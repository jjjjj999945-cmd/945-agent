# Lv4 Acceptance Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 945 增加可重复的一键 Lv4 验收、5 条显式付费 DeepSeek 基线、机器报告和中文验收摘要，并用真实运行证据完成当前阶段收口。

**Architecture:** 保留 `backend.evals.run_agent_eval` 作为 Agent 用例执行和指标聚合的唯一实现，只增加 Lv4 固定样本选择与必要的报告字段。新增 `backend.evals.run_lv4_acceptance` 作为薄编排层，通过子进程复用现有 pytest、构建和 Playwright 命令，汇总状态但不复制测试逻辑；DeepSeek 只在所有离线检查通过并显式要求时执行。

**Tech Stack:** Python 3.11、pytest、FastAPI、LangGraph、DeepSeek Provider、Node.js、Vite、Playwright、MongoDB、Docker Compose。

## Global Constraints

- 不修改 `src/`、前端颜色、字体、图标、导航、玻璃效果或任何 UI 视觉样式。
- 不修改产品功能、Prompt、Agent 工具白名单、结构化数据模型和“草稿 -> 用户确认 -> API 写入”边界。
- 默认路径零模型费用；只有 `--include-deepseek` 显式启用且离线检查全部通过后才能调用 DeepSeek。
- DeepSeek Lv4 样本固定为 5 条，通过门槛为 4/5，`deepseek_safety_warning` 必须通过，结构化写入必须为 0。
- 主报告不得包含 API Key、Authorization、用户聊天正文、模型完整输出、profile、RAG 原文或思维链。
- `.env.production`、`.venv/` 和 `output/` 不得提交。
- 文档使用中文；命令、路径和环境变量保持字面形式。

## File Structure

- Modify: `backend/evals/run_agent_eval.py` - 保留 Eval 单一实现，增加 Lv4 样本选择、必过用例和逻辑生成次数聚合。
- Create: `backend/evals/run_lv4_acceptance.py` - 定义验收命令、执行子进程、汇总矩阵、分类失败、生成 JSON/Markdown。
- Modify: `backend/tests/test_agent_eval_deepseek.py` - 验证固定 5 条集合、4/5 门槛和安全用例硬阻断。
- Modify: `backend/tests/test_agent_eval_report.py` - 验证逻辑生成次数聚合。
- Create: `backend/tests/test_lv4_acceptance.py` - 验证命令顺序、跳过付费调用、报告与提醒。
- Modify: `package.json` - 增加 `qa:lv4` 和 `qa:lv4:deepseek`。
- Modify: `README.md` - 将项目阶段和下一步说明更新为当前 Lv4 收口状态。
- Modify: `backend/README.md` - 记录统一验收命令、报告位置、付费边界和阈值。

---

### Task 1: 固定 Lv4 DeepSeek 样本与 Eval 报告契约

**Files:**
- Modify: `backend/evals/run_agent_eval.py`
- Modify: `backend/tests/test_agent_eval_deepseek.py`
- Modify: `backend/tests/test_agent_eval_report.py`

**Interfaces:**
- Produces: `LV4_DEEPSEEK_CASES: tuple[AgentEvalCase, ...]`。
- Produces: CLI `--deepseek-suite {full,lv4}`，只影响 `--provider deepseek`；默认 `full` 保持原 8 条行为。
- Produces: `build_eval_report(..., required_case_ids: frozenset[str] = frozenset()) -> dict[str, object]`。
- Produces: 报告字段 `total_logical_generations`、`required_case_ids`、`failed_required_cases`。
- Consumes: 现有 `DEEPSEEK_SAMPLE_CASES`、`run_evaluation()` 和 `ProviderUsage`。

- [ ] **Step 1: 写 Lv4 样本和安全硬门槛失败测试**

在 `backend/tests/test_agent_eval_deepseek.py` 增加：

```python
def test_lv4_deepseek_suite_has_five_fixed_cases():
    assert [case.case_id for case in agent_eval.LV4_DEEPSEEK_CASES] == [
        "deepseek_workout_record",
        "deepseek_meal_record",
        "deepseek_plan_adjustment",
        "deepseek_training_question",
        "deepseek_safety_warning",
    ]


def test_lv4_deepseek_report_requires_the_safety_case():
    results = [
        agent_eval.EvalCaseResult(
            case=case,
            passed=case.case_id != "deepseek_safety_warning",
            details="intent=expected",
            failure_category=("intent_mismatch" if case.case_id == "deepseek_safety_warning" else None),
            duration_ms=1.0,
            usage=ProviderUsage(logical_generations=1, http_attempts=1),
        )
        for case in agent_eval.LV4_DEEPSEEK_CASES
    ]
    report = agent_eval.build_eval_report(
        results,
        structured_writes=0,
        provider="deepseek",
        suite="deepseek_lv4",
        minimum_pass_rate=0.8,
        required_case_ids=frozenset({"deepseek_safety_warning"}),
    )
    assert report["pass_rate"] == 0.8
    assert report["failed_required_cases"] == ["deepseek_safety_warning"]
    assert report["passed"] is False
```

- [ ] **Step 2: 写逻辑生成次数聚合失败测试**

在 `backend/tests/test_agent_eval_report.py` 的指标测试中为两个结果分别设置 `logical_generations=1` 和 `logical_generations=2`，并断言：

```python
assert report["total_logical_generations"] == 3
```

- [ ] **Step 3: 运行测试并确认因接口缺失失败**

Run:

```powershell
python -m pytest backend/tests/test_agent_eval_deepseek.py backend/tests/test_agent_eval_report.py -q
```

Expected: FAIL，原因是 `LV4_DEEPSEEK_CASES`、`required_case_ids` 或 `total_logical_generations` 尚不存在。

- [ ] **Step 4: 最小实现固定样本、报告门槛和 CLI 选择**

在 `backend/evals/run_agent_eval.py`：

```python
LV4_DEEPSEEK_CASE_IDS = (
    "deepseek_workout_record",
    "deepseek_meal_record",
    "deepseek_plan_adjustment",
    "deepseek_training_question",
    "deepseek_safety_warning",
)
LV4_DEEPSEEK_CASES = tuple(
    case for case in DEEPSEEK_SAMPLE_CASES if case.case_id in LV4_DEEPSEEK_CASE_IDS
)
```

扩展 `build_eval_report()`：

```python
required_case_ids: frozenset[str] = frozenset()
failed_required_cases = sorted(
    result.case.case_id
    for result in results
    if result.case.case_id in required_case_ids and not result.passed
)
report_passed = (
    pass_rate >= minimum_pass_rate
    and structured_writes == 0
    and not failed_required_cases
)
```

并聚合：

```python
"total_logical_generations": sum(result.usage.logical_generations for result in results)
```

CLI 增加 `--deepseek-suite`，`lv4` 选择 `LV4_DEEPSEEK_CASES`、`minimum_pass_rate=0.8` 和安全必过集合；`full` 保持 8 条、`minimum_pass_rate=0.875`。

- [ ] **Step 5: 运行聚焦测试并确认通过**

Run:

```powershell
python -m pytest backend/tests/test_agent_eval_deepseek.py backend/tests/test_agent_eval_report.py backend/tests/test_agent_eval_runner.py -q
```

Expected: PASS，且现有 8 条默认 DeepSeek 接口保持兼容。

- [ ] **Step 6: 提交 Task 1**

```powershell
git add backend/evals/run_agent_eval.py backend/tests/test_agent_eval_deepseek.py backend/tests/test_agent_eval_report.py
git commit -m "feat: add lv4 deepseek eval gate"
```

---

### Task 2: 实现统一 Lv4 验收编排与报告

**Files:**
- Create: `backend/evals/run_lv4_acceptance.py`
- Create: `backend/tests/test_lv4_acceptance.py`

**Interfaces:**
- Produces: `CheckSpec(check_id, name, command, failure_category, artifact_path=None)`。
- Produces: `CheckResult(check_id, name, status, duration_ms, return_code, failure_category, log_path)`。
- Produces: `build_check_specs(root: Path, output_dir: Path, include_deepseek: bool) -> tuple[list[CheckSpec], CheckSpec | None]`。
- Produces: `run_acceptance(..., executor=execute_check) -> tuple[dict[str, object], int]`。
- Produces: `build_warnings(deepseek_report: dict[str, object] | None) -> list[dict[str, object]]`。
- Produces: `render_markdown(report: dict[str, object]) -> str`。
- Consumes: Task 1 的 `--deepseek-suite lv4` JSON 子报告。

- [ ] **Step 1: 写命令矩阵和顺序失败测试**

在 `backend/tests/test_lv4_acceptance.py`：

```python
def test_offline_check_order_reuses_existing_quality_commands(tmp_path):
    offline, deepseek = acceptance.build_check_specs(ROOT, tmp_path, include_deepseek=True)
    assert [item.check_id for item in offline] == [
        "backend_tests",
        "deterministic_eval",
        "frontend_build",
        "http_qa",
        "mongo_qa",
    ]
    assert deepseek is not None
    assert "--deepseek-suite" in deepseek.command
    assert "lv4" in deepseek.command
```

- [ ] **Step 2: 写离线失败时禁止 DeepSeek 的失败测试**

使用 fake executor 返回一个 `backend_tests` 失败结果，其余离线项通过：

```python
report, exit_code = acceptance.run_acceptance(
    root=ROOT,
    json_output=tmp_path / "report.json",
    markdown_output=tmp_path / "report.md",
    include_deepseek=True,
    executor=fake_executor,
)
assert exit_code == 1
assert called_ids == ["backend_tests", "deterministic_eval", "frontend_build", "http_qa", "mongo_qa"]
assert report["deepseek_executed"] is False
assert report["checks"][-1]["status"] == "skipped"
```

- [ ] **Step 3: 写报告、矩阵、失败分类和提醒失败测试**

测试用临时 DeepSeek 子报告包含 5 条、4/5、安全通过、`average_duration_ms=12000`、`total_input_tokens=8000`、`total_output_tokens=3000`、`total_logical_generations=5`、`total_http_attempts=6`。断言：

```python
assert report["overall_status"] == "passed"
assert report["deepseek_baseline"]["total_cases"] == 5
assert {item["code"] for item in report["warnings"]} == {
    "deepseek_latency_high",
    "deepseek_tokens_high",
    "deepseek_extra_http_attempts",
}
assert "API Key" not in markdown
assert "完成度矩阵" in markdown
```

- [ ] **Step 4: 运行测试并确认模块缺失失败**

Run:

```powershell
python -m pytest backend/tests/test_lv4_acceptance.py -q
```

Expected: FAIL，原因是 `backend.evals.run_lv4_acceptance` 尚不存在。

- [ ] **Step 5: 最小实现命令执行和报告生成**

实现固定常量：

```python
DEEPSEEK_LATENCY_WARNING_MS = 10_000
DEEPSEEK_AVERAGE_TOKENS_WARNING = 2_000
```

实现 `execute_check()`，使用 `subprocess.run(..., shell=False)`，将合并后的 stdout/stderr 写入 `output/lv4-logs/<check_id>.log`，主报告仅引用相对日志路径。

实现 `run_acceptance()`：始终执行五个离线项；全部通过且 `include_deepseek=True` 时才运行真实样本；解析子 JSON 后验证 case 数、`passed`、安全必过和零结构化写入；构建完成度矩阵、失败摘要和提醒；最后写 JSON/Markdown，并返回退出码。

CLI 参数：

```python
parser.add_argument("--include-deepseek", action="store_true")
parser.add_argument("--json-output", type=Path, default=Path("output/lv4-acceptance.json"))
parser.add_argument("--markdown-output", type=Path, default=Path("output/lv4-acceptance.md"))
```

- [ ] **Step 6: 运行聚焦测试并确认通过**

Run:

```powershell
python -m pytest backend/tests/test_lv4_acceptance.py -q
```

Expected: PASS。

- [ ] **Step 7: 提交 Task 2**

```powershell
git add backend/evals/run_lv4_acceptance.py backend/tests/test_lv4_acceptance.py
git commit -m "feat: add lv4 acceptance runner"
```

---

### Task 3: 接入项目命令并校正文档

**Files:**
- Modify: `package.json`
- Modify: `README.md`
- Modify: `backend/README.md`
- Modify: `backend/tests/test_lv4_acceptance.py`

**Interfaces:**
- Produces: `npm run qa:lv4`。
- Produces: `npm run qa:lv4:deepseek`。
- Documents: 默认零费用、真实 5 条样本、报告路径、硬阻断与提醒边界。

- [ ] **Step 1: 写 package script 失败测试**

在 `backend/tests/test_lv4_acceptance.py` 增加：

```python
def test_package_exposes_offline_and_explicit_paid_lv4_commands():
    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    assert package["scripts"]["qa:lv4"] == "python -m backend.evals.run_lv4_acceptance"
    assert package["scripts"]["qa:lv4:deepseek"] == (
        "python -m backend.evals.run_lv4_acceptance --include-deepseek "
        "--json-output output/lv4-acceptance-deepseek.json "
        "--markdown-output output/lv4-acceptance-deepseek.md"
    )
```

- [ ] **Step 2: 运行测试并确认脚本缺失失败**

Run:

```powershell
python -m pytest backend/tests/test_lv4_acceptance.py::test_package_exposes_offline_and_explicit_paid_lv4_commands -q
```

Expected: FAIL，原因是 `qa:lv4` 尚不存在。

- [ ] **Step 3: 增加两个 npm scripts**

只修改 `package.json` 的 `scripts`：

```json
"qa:lv4": "python -m backend.evals.run_lv4_acceptance",
"qa:lv4:deepseek": "python -m backend.evals.run_lv4_acceptance --include-deepseek --json-output output/lv4-acceptance-deepseek.json --markdown-output output/lv4-acceptance-deepseek.md"
```

- [ ] **Step 4: 更新 README 当前状态和验收说明**

在根 README 增加“当前阶段”与“Lv4 验收”章节，删除已明显过时的“后端尚未接入”表述。后端 README 增加两个命令、默认零费用、5 条付费样本、4/5 + 安全必过 + 零结构化写入门槛、报告路径和告警阈值；不重写其他产品说明。

- [ ] **Step 5: 验证脚本和文档测试**

Run:

```powershell
python -m pytest backend/tests/test_lv4_acceptance.py -q
```

Expected: PASS。

- [ ] **Step 6: 提交 Task 3**

```powershell
git add package.json README.md backend/README.md backend/tests/test_lv4_acceptance.py
git commit -m "docs: add lv4 acceptance workflow"
```

---

### Task 4: 完整验收、真实基线与阶段收口

**Files:**
- Generated only: `output/lv4-acceptance.json`
- Generated only: `output/lv4-acceptance.md`
- Generated only: `output/lv4-acceptance-deepseek.json`
- Generated only: `output/lv4-acceptance-deepseek.md`
- Modify only if a regression is found: files directly responsible for that failing check, with a new failing regression test first.

**Interfaces:**
- Consumes: `npm run qa:lv4`、`npm run qa:lv4:deepseek`、Compose `/health`。
- Produces: 当前提交的完整离线证据、5 条 DeepSeek token/延迟基线和 Docker 健康证据。

- [ ] **Step 1: 运行新增测试和完整后端测试**

```powershell
python -m pytest backend/tests/test_agent_eval_deepseek.py backend/tests/test_agent_eval_report.py backend/tests/test_lv4_acceptance.py -q
python -m pytest backend/tests -q
```

Expected: 全部 PASS；若失败，先为实际回归保留或新增失败测试，再做最小修复。

- [ ] **Step 2: 运行零费用统一验收**

```powershell
npm run qa:lv4
```

Expected: exit 0；报告 `overall_status=passed`；DeepSeek 矩阵项为 `not_run`；确定性 Eval 为 50/50，结构化写入为 0。

- [ ] **Step 3: 安全加载本机 Key 并运行 5 条真实样本**

只从被 Git 忽略的 `.env.production` 将 `DEEPSEEK_API_KEY`、`945_DEEPSEEK_MODEL` 和 `945_DEEPSEEK_MAX_TOKENS` 注入当前子进程；不得打印变量值：

```powershell
$allowed = @("DEEPSEEK_API_KEY", "945_DEEPSEEK_MODEL", "945_DEEPSEEK_MAX_TOKENS")
Get-Content .env.production | ForEach-Object {
  if ($_ -match '^\s*([^#][^=]*)=(.*)$') {
    $name = $matches[1].Trim()
    if ($allowed -contains $name) {
      [Environment]::SetEnvironmentVariable($name, $matches[2].Trim(), "Process")
    }
  }
}
npm run qa:lv4:deepseek
```

Expected: exit 0；至少 4/5、安全用例通过、结构化写入为 0，并写出 token、延迟和 HTTP 尝试次数。模型质量失败时只修复已有明确产品契约的代码或 Prompt 回归，不从输出扩展新产品设计。

- [ ] **Step 4: 检查 Docker 运行健康**

```powershell
docker compose ps
(Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8080/health).StatusCode
```

Expected: Compose 服务 healthy/running，HTTP 状态为 `200`。不执行 `docker compose down -v`。

- [ ] **Step 5: 最终仓库卫生和差异检查**

```powershell
git diff --check
git status --short
git diff --name-only HEAD~3..HEAD
git check-ignore .env.production .venv output
```

Expected: 只有计划内源码、测试和文档进入提交；`.env.production`、`.venv/` 和 `output/` 被忽略或保持未跟踪，不进入提交；无 `src/` UI 文件变化。

- [ ] **Step 6: 最终提交必要的验收修复**

如果完整验收暴露了需要修复的计划内问题，提交已通过回归测试的最小修复：

```powershell
git add <only-the-directly-related-files>
git commit -m "fix: close lv4 acceptance regressions"
```

没有源码修复时不创建空提交。

- [ ] **Step 7: 对照规格逐项复核**

核对 `docs/superpowers/specs/2026-08-12-lv4-acceptance-closure-design.md` 的“完成标准”，确认统一入口、两类报告、离线全绿、真实 5 条基线、Docker 200、README 更新、无 UI 改动和无密钥提交均有本轮证据。任何一项缺失都不得声称阶段完成。

