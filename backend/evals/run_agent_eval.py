"""Run the deterministic 945 Agent baseline without writing user records."""

import argparse
import asyncio
from dataclasses import dataclass
import json
from pathlib import Path

from backend.app.agents.graph import run_agent_graph
from backend.app.data.demo_data import DEMO_USER_ID, TODAY_DATE
from backend.app.llm.deterministic import DeterministicProvider
from backend.app.llm.factory import LLMProviderRouter
from backend.app.services.demo_store import list_meal_logs, list_plans, list_workout_logs


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
    AgentEvalCase("workout_completed", "今天完成了深蹲训练，帮我记录", "log_workout", "workout_log"),
    AgentEvalCase("workout_short_record", "深蹲 3 组 10 次，帮我记录", "log_workout", "workout_log"),
    AgentEvalCase("workout_english_record", "I did squats today, log it", "log_workout", "workout_log", "en-US"),
    AgentEvalCase("meal_manual_record", "今天吃了三文鱼和米饭，记录一下", "log_meal", "meal_log"),
    AgentEvalCase("meal_short_record", "我刚吃了蛋白餐，帮我记录", "log_meal", "meal_log"),
    AgentEvalCase("meal_english_record", "I ate a chicken rice meal, please log it", "log_meal", "meal_log", "en-US"),
    AgentEvalCase("plan_adjustment_schedule", "今天要调整训练安排", "adjust_plan", "plan_adjustment"),
    AgentEvalCase("plan_adjustment_english", "Please adjust my workout plan", "adjust_plan", "plan_adjustment", "en-US"),
    AgentEvalCase("nutrition_question", "蛋白质每天吃多少？", "ask_question", None),
    AgentEvalCase("meal_question", "训练后应该吃什么？", "ask_question", None),
    AgentEvalCase("safety_pain", "我现在强烈疼痛，还应该训练吗？", "safety_warning", None),
    AgentEvalCase("safety_heart", "我感觉心脏不适，今天能继续练吗？", "safety_warning", None),
    AgentEvalCase("workout_had_record", "I had a squat session today, log it", "log_workout", "workout_log", "en-US"),
    AgentEvalCase("workout_chinese_variant", "深蹲练了 3 组，记录一下", "log_workout", "workout_log"),
    AgentEvalCase("meal_had_record", "I had a high protein meal, log it", "log_meal", "meal_log", "en-US"),
    AgentEvalCase("meal_chinese_variant", "我吃了午餐，帮我记录", "log_meal", "meal_log"),
    AgentEvalCase("plan_adjustment_today", "帮我调整今天的训练", "adjust_plan", "plan_adjustment"),
    AgentEvalCase("plan_adjustment_weekly", "Please adjust my weekly plan", "adjust_plan", "plan_adjustment", "en-US"),
    AgentEvalCase("workout_how_question", "How do I squat safely", "ask_question", None, "en-US"),
    AgentEvalCase("food_question_english", "What is a good post-workout food?", "ask_question", None, "en-US"),
    AgentEvalCase("generic_today_question", "今天训练什么？", "ask_question", None),
    AgentEvalCase("safety_severe_pain", "我现在剧烈疼痛，还应该训练吗？", "safety_warning", None),
    AgentEvalCase("safety_breathing", "训练后呼吸困难，需要继续吗？", "safety_warning", None),
    AgentEvalCase("safety_fainting", "我刚刚昏倒过，今天还能练吗？", "safety_warning", None),
)


def _structured_record_count() -> int:
    return sum(
        len(records or [])
        for records in (
            list_workout_logs(DEMO_USER_ID),
            list_meal_logs(DEMO_USER_ID),
            list_plans(DEMO_USER_ID),
        )
    )


async def run_evaluation() -> tuple[list[tuple[AgentEvalCase, bool, str]], int]:
    provider = DeterministicProvider()
    router = LLMProviderRouter(primary=provider, fallback=provider, app_env="development")
    results: list[tuple[AgentEvalCase, bool, str]] = []
    starting_record_count = _structured_record_count()

    for case in CASES:
        records_before = _structured_record_count()
        result = await run_agent_graph(
            user_id=DEMO_USER_ID,
            locale=case.locale,
            message=case.message,
            context={"date": TODAY_DATE},
            provider_router=router,
        )
        records_after = _structured_record_count()
        actual_draft_type = result.record_draft.type if result.record_draft else None
        wrote_structured_record = records_after != records_before
        passed = (
            result.intent == case.expected_intent
            and actual_draft_type == case.expected_draft_type
            and not wrote_structured_record
        )
        details = (
            f"intent={result.intent}, draft={actual_draft_type or '-'}, "
            f"structured_write={'yes' if wrote_structured_record else 'no'}"
        )
        results.append((case, passed, details))

    return results, _structured_record_count() - starting_record_count


def build_eval_report(
    results: list[tuple[AgentEvalCase, bool, str]], structured_writes: int
) -> dict[str, object]:
    passed_cases = sum(1 for _, is_passing, _ in results if is_passing)
    total_cases = len(results)
    return {
        "total_cases": total_cases,
        "passed_cases": passed_cases,
        "pass_rate": passed_cases / total_cases if total_cases else 0.0,
        "structured_writes": structured_writes,
        "passed": passed_cases == total_cases and structured_writes == 0,
        "cases": [
            {"case_id": case.case_id, "passed": is_passing, "details": details}
            for case, is_passing, details in results
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the deterministic 945 Agent evaluation suite.")
    parser.add_argument("--json-output", type=Path, help="Write the evaluation report to this JSON file.")
    args = parser.parse_args(argv)
    results, structured_writes = asyncio.run(run_evaluation())
    report = build_eval_report(results, structured_writes)

    print("945 Agent Eval")
    for case, is_passing, details in results:
        print(f"{'PASS' if is_passing else 'FAIL'} {case.case_id}: {details}")
    print(f"Structured writes: {structured_writes}")
    print(f"Passed: {report['passed_cases']}/{report['total_cases']}")
    if args.json_output is not None:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
