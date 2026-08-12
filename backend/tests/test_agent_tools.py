from backend.app.agents.tools import (
    accept_advice,
    build_meal_log_draft,
    build_plan_adjustment_draft,
    build_workout_log_draft,
    create_meal_log_draft,
    create_plan_adjustment_draft,
    create_workout_log_draft,
    get_current_plan_tool,
    get_profile_tool,
    get_today_context,
    list_recent_meal_logs,
    list_recent_workout_logs,
)
from backend.app.data.demo_data import DEMO_USER_ID, TODAY_DATE
from backend.app.models.domain import ManualMealLogInput, WorkoutLogInput
from backend.app.services.demo_store import create_manual_meal_log, create_workout_log


def test_agent_read_tools_return_structured_context():
    assert get_profile_tool(DEMO_USER_ID).user_id == DEMO_USER_ID
    assert get_current_plan_tool(DEMO_USER_ID).plan_id == "plan-2026-07-11-demo"
    assert get_today_context(DEMO_USER_ID, TODAY_DATE).date == TODAY_DATE


def test_agent_recent_log_tools_read_existing_records():
    create_workout_log(
        WorkoutLogInput(
            user_id=DEMO_USER_ID,
            date=TODAY_DATE,
            status="completed",
            exercises=[{"name": "深蹲", "sets": [{"reps": 8}]}]
        )
    )
    create_manual_meal_log(
        ManualMealLogInput(
            user_id=DEMO_USER_ID,
            date=TODAY_DATE,
            meal_name="加餐",
            foods=[{"name": "香蕉", "portion": "1 根", "calories": 100, "protein_g": 1, "carbs_g": 27, "fat_g": 0}]
        )
    )

    assert list_recent_workout_logs(DEMO_USER_ID)[0].exercises[0].name == "深蹲"
    assert list_recent_meal_logs(DEMO_USER_ID)[0].meal_name == "加餐"


def test_agent_draft_tools_do_not_write_records():
    workout_draft = create_workout_log_draft("今天深蹲做了 4 组，每组 8 次，80kg。")
    meal_draft = create_meal_log_draft("我中午吃了鸡胸肉饭。", locale="zh-CN")
    adjustment_draft = create_plan_adjustment_draft("今天太累，帮我调整计划。")

    assert workout_draft.type == "workout_log"
    assert workout_draft.requires_confirmation is True
    assert workout_draft.payload["exercise_name"] == "深蹲"
    assert meal_draft.type == "meal_log"
    assert meal_draft.payload["meal_name"] == "手动记录"
    assert adjustment_draft.type == "plan_adjustment"
    assert list_recent_workout_logs(DEMO_USER_ID) == []
    assert list_recent_meal_logs(DEMO_USER_ID) == []


def test_agent_identifies_skip_and_swap_plan_adjustment_drafts():
    skip = create_plan_adjustment_draft("Skip today's workout")
    swap = create_plan_adjustment_draft("Swap meal for today")

    assert skip.payload["adjustment_type"] == "skip_workout"
    assert swap.payload["adjustment_type"] == "swap_meal"
    assert skip.payload["target_date"] == TODAY_DATE


def test_structured_draft_builders_return_confirmation_required_drafts():
    workout_draft = build_workout_log_draft("深蹲", 4, 8, 80, "感觉很累")
    meal_draft = build_meal_log_draft("午餐", "鸡胸肉饭")
    adjustment_draft = build_plan_adjustment_draft("reduce_intensity", "今天太累")

    assert workout_draft.payload == {
        "exercise_name": "深蹲",
        "sets": 4,
        "reps": 8,
        "weight_kg": 80,
        "effort_note": "感觉很累",
    }
    assert meal_draft.payload == {"meal_name": "午餐", "note": "鸡胸肉饭"}
    assert adjustment_draft.payload == {
        "adjustment_type": "reduce_intensity",
        "reason": "今天太累",
    }
    assert all(
        draft.requires_confirmation is True
        for draft in (workout_draft, meal_draft, adjustment_draft)
    )


def test_accept_advice_tool_updates_advice_status():
    advice = accept_advice(DEMO_USER_ID, "advice-2026-07-11-1", "accepted")

    assert advice.accepted_status == "accepted"
