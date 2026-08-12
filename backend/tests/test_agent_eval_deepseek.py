import backend.evals.run_agent_eval as agent_eval
import pytest

from backend.app.llm.models import ProviderUsage


def test_deepseek_suite_contains_eight_explicit_cases():
    assert len(agent_eval.DEEPSEEK_SAMPLE_CASES) == 8
    assert {case.expected_intent for case in agent_eval.DEEPSEEK_SAMPLE_CASES} >= {
        "log_workout",
        "log_meal",
        "adjust_plan",
        "ask_question",
        "safety_warning",
    }


def test_deepseek_router_requires_a_key(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    with pytest.raises(agent_eval.EvalConfigurationError, match="DEEPSEEK_API_KEY"):
        agent_eval.build_evaluation_router("deepseek")


def test_deepseek_sample_selection_does_not_construct_a_network_client(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "deepseek-test-key")
    fake_router = object()

    def build_fake_router(settings):
        assert settings.app_env == "production"
        assert settings.llm_provider == "deepseek"
        return fake_router

    monkeypatch.setattr(agent_eval, "build_llm_provider_router", build_fake_router)

    assert agent_eval.build_evaluation_router("deepseek") is fake_router


def test_deepseek_report_requires_at_least_seven_of_eight_cases():
    results = [
        agent_eval.EvalCaseResult(
            case=agent_eval.AgentEvalCase(f"sample-{index}", "message", "ask_question", None),
            passed=index < 7,
            details="intent=ask_question",
            failure_category=None if index < 7 else "intent_mismatch",
            duration_ms=1.0,
            usage=ProviderUsage(),
        )
        for index in range(8)
    ]

    report = agent_eval.build_eval_report(
        results,
        structured_writes=0,
        provider="deepseek",
        suite="deepseek_sample",
        minimum_pass_rate=0.875,
    )

    assert report["passed"] is True
