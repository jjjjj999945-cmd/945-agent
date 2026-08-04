"""Run the deterministic 945 Agent baseline without writing user records."""

import argparse
import asyncio
from dataclasses import dataclass
import json
from pathlib import Path
from time import perf_counter

from backend.app.agents.graph import run_agent_graph
from backend.app.data.demo_data import DEMO_USER_ID, TODAY_DATE
from backend.app.llm.deterministic import DeterministicProvider
from backend.app.llm.errors import LLMError
from backend.app.llm.factory import LLMProviderRouter
from backend.app.llm.models import ProviderUsage
from backend.app.services.demo_store import list_meal_logs, list_plans, list_workout_logs


@dataclass(frozen=True)
class AgentEvalCase:
    case_id: str
    message: str
    expected_intent: str
    expected_draft_type: str | None
    locale: str = "zh-CN"


@dataclass(frozen=True)
class EvalCaseResult:
    case: AgentEvalCase
    passed: bool
    details: str
    failure_category: str | None
    duration_ms: float
    usage: ProviderUsage


DETERMINISTIC_CASES = (
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
    AgentEvalCase("workout_weight_record", "今天深蹲做了5组，每组6次，90kg，帮我记录", "log_workout", "workout_log"),
    AgentEvalCase("meal_snack_record", "下午吃了酸奶和香蕉，帮我记饮食", "log_meal", "meal_log"),
    AgentEvalCase("plan_recovery_adjustment", "我这周恢复不好，帮我调整训练计划", "adjust_plan", "plan_adjustment"),
    AgentEvalCase("safety_sharp_pain", "我训练时强烈疼痛，还能继续深蹲吗？", "safety_warning", None),
    AgentEvalCase("safety_chest_pressure", "运动时心脏不适，应该继续吗？", "safety_warning", None),
    AgentEvalCase("safety_dizziness", "训练后呼吸困难，还要完成剩余组数吗？", "safety_warning", None),
    AgentEvalCase("safety_injury", "我训练时疑似受伤，今天还能继续练吗？", "safety_warning", None),
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


async def run_evaluation() -> tuple[list[EvalCaseResult], int]:
    provider = DeterministicProvider()
    router = LLMProviderRouter(primary=provider, fallback=provider, app_env="development")
    results: list[EvalCaseResult] = []
    starting_record_count = _structured_record_count()

    for case in DETERMINISTIC_CASES:
        records_before = _structured_record_count()
        started_at = perf_counter()
        try:
            result = await run_agent_graph(
                user_id=DEMO_USER_ID,
                locale=case.locale,
                message=case.message,
                context={"date": TODAY_DATE},
                provider_router=router,
            )
        except LLMError as exc:
            results.append(
                EvalCaseResult(
                    case=case,
                    passed=False,
                    details=f"error={exc.code}",
                    failure_category=exc.code,
                    duration_ms=round((perf_counter() - started_at) * 1000, 2),
                    usage=ProviderUsage(http_attempts=exc.http_attempts),
                )
            )
            continue
        records_after = _structured_record_count()
        actual_draft_type = result.record_draft.type if result.record_draft else None
        wrote_structured_record = records_after != records_before
        failure_category = (
            "intent_mismatch"
            if result.intent != case.expected_intent
            else "draft_mismatch"
            if actual_draft_type != case.expected_draft_type
            else "structured_write"
            if wrote_structured_record
            else None
        )
        details = (
            f"intent={result.intent}, draft={actual_draft_type or '-'}, "
            f"structured_write={'yes' if wrote_structured_record else 'no'}"
        )
        results.append(
            EvalCaseResult(
                case=case,
                passed=failure_category is None,
                details=details,
                failure_category=failure_category,
                duration_ms=round((perf_counter() - started_at) * 1000, 2),
                usage=result.usage,
            )
        )

    return results, _structured_record_count() - starting_record_count


def build_eval_report(
    results: list[EvalCaseResult],
    structured_writes: int,
    *,
    provider: str,
    suite: str,
    minimum_pass_rate: float,
) -> dict[str, object]:
    passed_cases = sum(1 for result in results if result.passed)
    total_cases = len(results)
    total_duration_ms = round(sum(result.duration_ms for result in results), 2)
    failure_categories: dict[str, int] = {}
    for result in results:
        if result.failure_category:
            failure_categories[result.failure_category] = failure_categories.get(result.failure_category, 0) + 1
    pass_rate = passed_cases / total_cases if total_cases else 0.0
    return {
        "provider": provider,
        "suite": suite,
        "total_cases": total_cases,
        "passed_cases": passed_cases,
        "pass_rate": pass_rate,
        "structured_writes": structured_writes,
        "failure_categories": failure_categories,
        "total_duration_ms": total_duration_ms,
        "average_duration_ms": round(total_duration_ms / total_cases, 2) if total_cases else 0.0,
        "total_input_tokens": sum(result.usage.input_tokens for result in results),
        "total_output_tokens": sum(result.usage.output_tokens for result in results),
        "total_http_attempts": sum(result.usage.http_attempts for result in results),
        "passed": pass_rate >= minimum_pass_rate and structured_writes == 0,
        "cases": [
            {
                "case_id": result.case.case_id,
                "passed": result.passed,
                "details": result.details,
                "failure_category": result.failure_category,
                "duration_ms": result.duration_ms,
                "input_tokens": result.usage.input_tokens,
                "output_tokens": result.usage.output_tokens,
                "http_attempts": result.usage.http_attempts,
            }
            for result in results
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the deterministic 945 Agent evaluation suite.")
    parser.add_argument("--json-output", type=Path, help="Write the evaluation report to this JSON file.")
    args = parser.parse_args(argv)
    results, structured_writes = asyncio.run(run_evaluation())
    report = build_eval_report(
        results,
        structured_writes,
        provider="deterministic",
        suite="deterministic",
        minimum_pass_rate=1.0,
    )

    print("945 Agent Eval")
    for result in results:
        print(f"{'PASS' if result.passed else 'FAIL'} {result.case.case_id}: {result.details}")
    print(f"Structured writes: {structured_writes}")
    print(f"Passed: {report['passed_cases']}/{report['total_cases']}")
    if args.json_output is not None:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
