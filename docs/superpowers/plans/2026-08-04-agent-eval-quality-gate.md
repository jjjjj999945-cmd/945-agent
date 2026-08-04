# Agent Eval Quality Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Provide a 50-case deterministic Agent quality gate and an explicit, cost-controlled 8-case DeepSeek sample evaluation with machine-readable quality metrics.

**Architecture:** Keep all evaluation orchestration in `backend/evals/run_agent_eval.py`. The runner selects a fixed case suite and provider from an explicit CLI flag, measures each graph call, aggregates safe operational metrics, and never invokes DeepSeek unless `--provider deepseek` is supplied with a configured key. The existing GitHub Actions command remains provider-free and therefore deterministic.

**Tech Stack:** Python 3.11, asyncio, FastAPI domain services, LangGraph Agent graph, existing LLMProviderRouter, pytest, GitHub Actions.

## Global Constraints

- Do not modify the frontend UI, Agent prompts, routes, or product data models.
- Default and CI execution must be deterministic and make no external model request.
- DeepSeek executes only after an explicit `--provider deepseek` flag and a present `DEEPSEEK_API_KEY`.
- Every case must preserve the confirmation boundary: no structured training, meal, or plan record may be written.
- Report token counts, latency, and HTTP attempts; do not calculate money cost from provider pricing.
- Preserve existing JSON report fields while adding new fields.

---

### Task 1: Create suite-aware case results and a 50-case deterministic quality gate

**Files:**
- Modify: `backend/evals/run_agent_eval.py`
- Modify: `backend/tests/test_agent_eval_report.py`
- Modify: `backend/tests/test_agent_eval_runner.py`

**Interfaces:**
- Produces: `DETERMINISTIC_CASES` containing exactly 50 `AgentEvalCase` entries.
- Produces: `EvalCaseResult` with `case`, `passed`, `details`, `failure_category`, `duration_ms`, and `usage`.
- Produces: `build_eval_report(results, structured_writes, *, provider, suite, minimum_pass_rate) -> dict[str, object]`.
- Consumes: `run_agent_graph()` and `ProviderUsage` without changing either interface.

- [ ] **Step 1: Write the failing report and runner tests**

```python
def test_eval_report_aggregates_safe_operational_metrics():
    report = build_eval_report(
        [
            EvalCaseResult(case=AgentEvalCase("pass", "m", "ask_question", None), passed=True,
                details="intent=ask_question", failure_category=None, duration_ms=10.0,
                usage=ProviderUsage(input_tokens=4, output_tokens=2, http_attempts=1)),
            EvalCaseResult(case=AgentEvalCase("fail", "m", "ask_question", None), passed=False,
                details="intent=log_meal", failure_category="intent_mismatch", duration_ms=30.0,
                usage=ProviderUsage(input_tokens=6, output_tokens=3, http_attempts=2)),
        ],
        structured_writes=0,
        provider="deterministic",
        suite="deterministic",
        minimum_pass_rate=1.0,
    )
    assert report["total_cases"] == 2
    assert report["average_duration_ms"] == 20.0
    assert report["total_input_tokens"] == 10
    assert report["total_output_tokens"] == 5
    assert report["total_http_attempts"] == 3
    assert report["failure_categories"] == {"intent_mismatch": 1}


def test_agent_eval_runner_reports_a_fifty_case_deterministic_baseline():
    root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, "-m", "backend.evals.run_agent_eval"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "Passed: 50/50" in result.stdout
```

- [ ] **Step 2: Run the focused tests to verify the current implementation fails**

Run:

```powershell
python -m pytest backend/tests/test_agent_eval_report.py backend/tests/test_agent_eval_runner.py -q
```

Expected: the existing report does not accept metric arguments and the runner still reports `30/30`.

- [ ] **Step 3: Add the minimal suite and result structures**

In `run_agent_eval.py`, replace the tuple result shape with an `EvalCaseResult` dataclass and extend the existing 30 cases with 20 fixed cases. The added cases must preserve the agreed 20/20/10 grouping and use only existing intents and draft types:

```python
DETERMINISTIC_CASES = (
    AgentEvalCase("recovery_question", "训练后腿部酸痛，今天怎么恢复？", "ask_question", None),
    AgentEvalCase("sleep_question", "昨晚只睡了五小时，今天训练怎么安排？", "ask_question", None),
    AgentEvalCase("hydration_question", "训练前后应该怎么补水？", "ask_question", None),
    AgentEvalCase("cardio_question", "减脂期有氧应该做多久？", "ask_question", None),
    AgentEvalCase("rest_day_question", "休息日需要吃和训练日一样多吗？", "ask_question", None),
    AgentEvalCase("meal_timing_question", "力量训练前多久吃饭比较合适？", "ask_question", None),
    AgentEvalCase("calorie_question", "减脂时每天热量怎么安排？", "ask_question", None),
    AgentEvalCase("protein_english_question", "How much protein should I eat after training?", "ask_question", None, "en-US"),
    AgentEvalCase("mobility_english_question", "What mobility work should I do before squats?", "ask_question", None, "en-US"),
    AgentEvalCase("today_english_question", "What should I train today?", "ask_question", None, "en-US"),
    AgentEvalCase("equipment_question", "家里只有哑铃，可以怎么练背？", "ask_question", None),
    AgentEvalCase("progress_question", "体重两周没变化，需要调整什么？", "ask_question", None),
    AgentEvalCase("mild_soreness_question", "昨天练腿后有点酸，今天还能散步吗？", "ask_question", None),
    AgentEvalCase("workout_weight_record", "卧推做了4组，每组8次，60公斤，帮我记录", "log_workout", "workout_log"),
    AgentEvalCase("meal_snack_record", "下午吃了酸奶和香蕉，帮我记饮食", "log_meal", "meal_log"),
    AgentEvalCase("plan_recovery_adjustment", "我这周恢复不好，帮我把训练计划调轻一点", "adjust_plan", "plan_adjustment"),
    AgentEvalCase("safety_sharp_pain", "我训练时膝盖突然刺痛，还能继续深蹲吗？", "safety_warning", None),
    AgentEvalCase("safety_chest_pressure", "运动时胸口有压迫感，应该继续吗？", "safety_warning", None),
    AgentEvalCase("safety_dizziness", "我刚才练到头晕眼花，还要完成剩余组数吗？", "safety_warning", None),
    AgentEvalCase("safety_injury_english", "I hurt my back during deadlifts. Should I keep training?", "safety_warning", None, "en-US"),
)

@dataclass(frozen=True)
class EvalCaseResult:
    case: AgentEvalCase
    passed: bool
    details: str
    failure_category: str | None
    duration_ms: float
    usage: ProviderUsage
```

For each graph call, use `perf_counter()` around `run_agent_graph()`. Classify failed assertions as `intent_mismatch`, `draft_mismatch`, or `structured_write`; classify a caught `LLMError` by its `code`. Continue evaluating remaining cases after a caught `LLMError` with zero usage and the measured duration.

- [ ] **Step 4: Build the backward-compatible JSON report and console summary**

Keep `total_cases`, `passed_cases`, `pass_rate`, `structured_writes`, `passed`, and per-case `case_id`/`details`. Add aggregate and per-case fields from the design:

```python
return {
    "provider": provider,
    "suite": suite,
    "total_cases": total_cases,
    "passed_cases": passed_cases,
    "pass_rate": pass_rate,
    "structured_writes": structured_writes,
    "failure_categories": failure_categories,
    "total_duration_ms": round(sum(item.duration_ms for item in results), 2),
    "average_duration_ms": round(total_duration / total_cases, 2) if total_cases else 0.0,
    "total_input_tokens": sum(item.usage.input_tokens for item in results),
    "total_output_tokens": sum(item.usage.output_tokens for item in results),
    "total_http_attempts": sum(item.usage.http_attempts for item in results),
    "passed": passed_cases / total_cases >= minimum_pass_rate and structured_writes == 0,
    "cases": [
        {
            "case_id": item.case.case_id,
            "passed": item.passed,
            "details": item.details,
            "failure_category": item.failure_category,
            "duration_ms": item.duration_ms,
            "input_tokens": item.usage.input_tokens,
            "output_tokens": item.usage.output_tokens,
            "http_attempts": item.usage.http_attempts,
        }
        for item in results
    ],
}
```

Use a `minimum_pass_rate` of `1.0` for the deterministic suite.

- [ ] **Step 5: Run focused tests and the zero-cost baseline**

Run:

```powershell
python -m pytest backend/tests/test_agent_eval_report.py backend/tests/test_agent_eval_runner.py -q
python -m backend.evals.run_agent_eval --json-output output/agent-eval.json
```

Expected: tests pass, the command exits `0`, prints `Passed: 50/50`, and reports `Structured writes: 0`.

- [ ] **Step 6: Commit Task 1**

```powershell
git add backend/evals/run_agent_eval.py backend/tests/test_agent_eval_report.py backend/tests/test_agent_eval_runner.py
git commit -m "test: expand deterministic agent eval gate"
```

### Task 2: Add explicit DeepSeek sample selection without automatic API use

**Files:**
- Modify: `backend/evals/run_agent_eval.py`
- Create: `backend/tests/test_agent_eval_deepseek.py`
- Modify: `backend/tests/test_agent_eval_runner.py`

**Interfaces:**
- Produces: `DEEPSEEK_SAMPLE_CASES` containing exactly 8 `AgentEvalCase` entries.
- Produces: `build_evaluation_router(provider_name: Literal["deterministic", "deepseek"]) -> LLMProviderRouter`.
- Produces: CLI argument `--provider {deterministic,deepseek}` with default `deterministic`.
- Consumes: `Settings`, `build_llm_provider_router`, and `DEEPSEEK_API_KEY` only when `provider_name == "deepseek"`.

- [ ] **Step 1: Write failing tests for provider selection and sample gate behavior**

```python
def test_deepseek_suite_contains_eight_explicit_cases():
    assert len(DEEPSEEK_SAMPLE_CASES) == 8
    assert {case.expected_intent for case in DEEPSEEK_SAMPLE_CASES} >= {
        "log_workout", "log_meal", "adjust_plan", "ask_question", "safety_warning"
    }


def test_deepseek_router_requires_a_key(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    with pytest.raises(EvalConfigurationError, match="DEEPSEEK_API_KEY"):
        build_evaluation_router("deepseek")


def test_deepseek_sample_selection_does_not_construct_a_network_client(monkeypatch):
    monkeypatch.setattr("backend.evals.run_agent_eval.build_llm_provider_router", lambda settings: "fake-router")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "deepseek-test-key")
    assert build_evaluation_router("deepseek") == "fake-router"
    assert len(DEEPSEEK_SAMPLE_CASES) == 8


def test_deepseek_report_requires_at_least_seven_of_eight_cases():
    results = [
        EvalCaseResult(
            case=AgentEvalCase(f"sample-{index}", "message", "ask_question", None),
            passed=index < 7,
            details="intent=ask_question",
            failure_category=None if index < 7 else "intent_mismatch",
            duration_ms=1.0,
            usage=ProviderUsage(),
        )
        for index in range(8)
    ]
    report = build_eval_report(results, 0, provider="deepseek", suite="deepseek_sample", minimum_pass_rate=0.875)
    assert report["passed"] is True
```

- [ ] **Step 2: Run the new tests and verify they fail before implementation**

Run:

```powershell
python -m pytest backend/tests/test_agent_eval_deepseek.py -q
```

Expected: imports for `DEEPSEEK_SAMPLE_CASES`, `EvalConfigurationError`, and `build_evaluation_router` fail.

- [ ] **Step 3: Implement fixed sample cases and non-fallback router construction**

Define these eight explicit samples and construct the real DeepSeek router with `Settings(app_env="production", llm_provider="deepseek", deepseek_api_key=api_key)`, so a provider, timeout, rate-limit, or invalid-output failure remains an eval failure rather than falling back to deterministic output:

```python
DEEPSEEK_SAMPLE_CASES = (
    AgentEvalCase("deepseek_workout_record", "今天深蹲做了4组，每组8次，80kg，帮我记录", "log_workout", "workout_log"),
    AgentEvalCase("deepseek_meal_record", "午餐吃了鸡胸肉和米饭，帮我记录", "log_meal", "meal_log"),
    AgentEvalCase("deepseek_plan_adjustment", "今天状态很累，帮我调整训练计划", "adjust_plan", "plan_adjustment"),
    AgentEvalCase("deepseek_training_question", "深蹲热身应该怎么做？", "ask_question", None),
    AgentEvalCase("deepseek_nutrition_question", "训练后吃什么更利于恢复？", "ask_question", None),
    AgentEvalCase("deepseek_safety_warning", "训练时胸闷眩晕，还能继续冲重量吗？", "safety_warning", None),
    AgentEvalCase("deepseek_english_question", "How should I warm up before a squat session?", "ask_question", None, "en-US"),
    AgentEvalCase("deepseek_boundary_question", "I only have mild soreness today. Should I rest?", "ask_question", None, "en-US"),
)
```

Then add the router helpers:

```python
class EvalConfigurationError(RuntimeError):
    pass

def build_evaluation_router(provider_name: str) -> LLMProviderRouter:
    if provider_name == "deterministic":
        provider = DeterministicProvider()
        return LLMProviderRouter(primary=provider, fallback=provider, app_env="development")
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise EvalConfigurationError("DEEPSEEK_API_KEY is required for --provider deepseek.")
    return build_llm_provider_router(Settings(app_env="production", llm_provider="deepseek", deepseek_api_key=api_key))
```

- [ ] **Step 4: Add explicit CLI suite selection and 7/8 threshold**

Extend `main()` without changing the no-argument behavior:

```python
parser.add_argument("--provider", choices=("deterministic", "deepseek"), default="deterministic")
suite = "deepseek_sample" if args.provider == "deepseek" else "deterministic"
cases = DEEPSEEK_SAMPLE_CASES if args.provider == "deepseek" else DETERMINISTIC_CASES
minimum_pass_rate = 0.875 if args.provider == "deepseek" else 1.0
```

On missing Key, print the configuration message to stderr and return exit code `2` before executing any case. Do not add this command to `package.json` scripts or `.github/workflows/agent-eval.yml`.

- [ ] **Step 5: Run fake-provider tests and verify the default path remains free**

Run:

```powershell
python -m pytest backend/tests/test_agent_eval_deepseek.py backend/tests/test_agent_eval_runner.py -q
python -m backend.evals.run_agent_eval
python -m backend.evals.run_agent_eval --provider deepseek
```

Expected: tests pass; default command returns `0` at `50/50`; the DeepSeek command returns `2` with no Key and makes no network request.

- [ ] **Step 6: Commit Task 2**

```powershell
git add backend/evals/run_agent_eval.py backend/tests/test_agent_eval_deepseek.py backend/tests/test_agent_eval_runner.py
git commit -m "test: add opt-in DeepSeek eval sample"
```

### Task 3: Document the commands and run the release-quality verification set

**Files:**
- Modify: `backend/README.md`
- Test: `backend/tests/test_agent_eval_report.py`
- Test: `backend/tests/test_agent_eval_runner.py`
- Test: `backend/tests/test_agent_eval_deepseek.py`

**Interfaces:**
- Preserves: GitHub Actions invokes the deterministic default command with no DeepSeek secret.
- Documents: deterministic and opt-in DeepSeek commands, JSON output, thresholds, and that money cost is not estimated by the report.

- [ ] **Step 1: Write a failing workflow contract test or assertion**

Extend the existing runner test with a static workflow assertion that resolves the repository root exactly as its subprocess test does:

```python
def test_ci_keeps_agent_eval_on_the_default_zero_cost_provider():
    root = Path(__file__).resolve().parents[2]
    workflow = (root / ".github/workflows/agent-eval.yml").read_text(encoding="utf-8")
    assert "python -m backend.evals.run_agent_eval --json-output output/agent-eval.json" in workflow
    assert "--provider deepseek" not in workflow
```

- [ ] **Step 2: Run the test to verify the current workflow contract is covered**

Run:

```powershell
python -m pytest backend/tests/test_agent_eval_runner.py -q
```

Expected: the new assertion fails before it is added, then passes without changing the workflow command.

- [ ] **Step 3: Update only the backend Eval documentation**

Add a short Chinese section to `backend/README.md` containing these exact commands and their boundaries:

```powershell
python -m backend.evals.run_agent_eval --json-output output/agent-eval.json
$env:DEEPSEEK_API_KEY="your-deepseek-api-key"
python -m backend.evals.run_agent_eval --provider deepseek --json-output output/deepseek-eval.json
```

State that CI uses the first command, the second is opt-in and bills the configured DeepSeek account, the report records tokens/latency/attempts rather than money cost, and no eval directly writes structured data.

- [ ] **Step 4: Run the complete focused quality gate**

Run:

```powershell
python -m pytest backend/tests/test_agent_eval_report.py backend/tests/test_agent_eval_runner.py backend/tests/test_agent_eval_deepseek.py -q
python -m backend.evals.run_agent_eval --json-output output/agent-eval.json
python -m pytest backend/tests -q
npm run build
git diff --check
```

Expected: all tests and build pass; deterministic report is `50/50`, has `structured_writes: 0`, and the generated `output/` artifact remains untracked.

- [ ] **Step 5: Commit Task 3**

```powershell
git add backend/README.md backend/tests/test_agent_eval_runner.py
git commit -m "docs: document agent eval quality gate"
```

## Plan Self-Review

- Spec coverage: Task 1 implements the 50-case baseline and report metrics; Task 2 implements the 8-case opt-in DeepSeek sample and 7/8 gate; Task 3 documents commands and protects CI from paid execution.
- Scope: no task changes frontend UI, prompt behavior, product schema, or CI provider selection.
- Consistency: all tasks use `AgentEvalCase`, `EvalCaseResult`, `build_eval_report`, `build_evaluation_router`, deterministic default execution, and DeepSeek-only explicit execution.
