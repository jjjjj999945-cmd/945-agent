from backend.app.llm.models import ProviderUsage
from backend.evals.run_agent_eval import AgentEvalCase, EvalCaseResult, build_eval_report


def test_eval_report_exposes_machine_readable_quality_gate():
    passing_case = EvalCaseResult(
        case=AgentEvalCase("safe", "message", "ask_question", None),
        passed=True,
        details="intent=ask_question",
        failure_category=None,
        duration_ms=1.0,
        usage=ProviderUsage(),
    )
    failing_case = EvalCaseResult(
        case=AgentEvalCase("wrong-intent", "message", "ask_question", None),
        passed=False,
        details="intent=log_meal",
        failure_category="intent_mismatch",
        duration_ms=1.0,
        usage=ProviderUsage(),
    )

    report = build_eval_report(
        [passing_case, failing_case],
        structured_writes=0,
        provider="deterministic",
        suite="deterministic",
        minimum_pass_rate=1.0,
    )

    assert report["total_cases"] == 2
    assert report["passed_cases"] == 1
    assert report["pass_rate"] == 0.5
    assert report["structured_writes"] == 0
    assert report["passed"] is False
    assert report["cases"][1]["case_id"] == "wrong-intent"
    assert report["cases"][1]["passed"] is False


def test_eval_report_aggregates_safe_operational_metrics():
    report = build_eval_report(
        [
            EvalCaseResult(
                case=AgentEvalCase("pass", "message", "ask_question", None),
                passed=True,
                details="intent=ask_question",
                failure_category=None,
                duration_ms=10.0,
                usage=ProviderUsage(
                    input_tokens=4,
                    output_tokens=2,
                    logical_generations=1,
                    http_attempts=1,
                ),
            ),
            EvalCaseResult(
                case=AgentEvalCase("fail", "message", "ask_question", None),
                passed=False,
                details="intent=log_meal",
                failure_category="intent_mismatch",
                duration_ms=30.0,
                usage=ProviderUsage(
                    input_tokens=6,
                    output_tokens=3,
                    logical_generations=2,
                    http_attempts=2,
                ),
            ),
        ],
        structured_writes=0,
        provider="deterministic",
        suite="deterministic",
        minimum_pass_rate=1.0,
    )

    assert report["average_duration_ms"] == 20.0
    assert report["total_input_tokens"] == 10
    assert report["total_output_tokens"] == 5
    assert report["total_logical_generations"] == 3
    assert report["total_http_attempts"] == 3
    assert report["failure_categories"] == {"intent_mismatch": 1}
