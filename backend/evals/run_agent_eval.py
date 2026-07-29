"""Run the deterministic 945 Agent baseline without writing user records."""

import asyncio
from dataclasses import dataclass

from backend.app.agents.graph import run_agent_graph
from backend.app.data.demo_data import DEMO_USER_ID, TODAY_DATE
from backend.app.llm.deterministic import DeterministicProvider
from backend.app.llm.factory import LLMProviderRouter


@dataclass(frozen=True)
class AgentEvalCase:
    case_id: str
    message: str
    expected_intent: str
    expected_draft_type: str | None
    locale: str = "zh-CN"


CASES = (
    AgentEvalCase("workout_log", "今天深蹲做了 4 组，每组 8 次，80kg，帮我记录", "log_workout", "workout_log"),
    AgentEvalCase("meal_log", "中午吃了鸡胸肉饭，帮我记录", "log_meal", "meal_log"),
    AgentEvalCase("plan_adjustment", "今天太累，帮我调整计划", "adjust_plan", "plan_adjustment"),
    AgentEvalCase("knowledge_question", "深蹲的要点是什么？", "ask_question", None),
    AgentEvalCase("safety_warning", "我训练时胸闷眩晕，还能继续冲重量吗？", "safety_warning", None),
    AgentEvalCase("english_question", "How should I warm up before a squat session?", "ask_question", None, "en-US"),
)


async def run_evaluation() -> list[tuple[AgentEvalCase, bool, str]]:
    provider = DeterministicProvider()
    router = LLMProviderRouter(primary=provider, fallback=provider, app_env="development")
    results: list[tuple[AgentEvalCase, bool, str]] = []

    for case in CASES:
        result = await run_agent_graph(
            user_id=DEMO_USER_ID,
            locale=case.locale,
            message=case.message,
            context={"date": TODAY_DATE},
            provider_router=router,
        )
        actual_draft_type = result.record_draft.type if result.record_draft else None
        passed = result.intent == case.expected_intent and actual_draft_type == case.expected_draft_type
        details = f"intent={result.intent}, draft={actual_draft_type or '-'}"
        results.append((case, passed, details))

    return results


def main() -> int:
    results = asyncio.run(run_evaluation())
    passed = sum(1 for _, is_passing, _ in results if is_passing)

    print("945 Agent Eval")
    for case, is_passing, details in results:
        print(f"{'PASS' if is_passing else 'FAIL'} {case.case_id}: {details}")
    print(f"Passed: {passed}/{len(results)}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
