from backend.app.data.demo_data import DEMO_USER_ID, TODAY_DATE
from backend.app.models.domain import DailyCheckinInput, ManualMealLogInput, WorkoutLogInput
from backend.app.services.demo_store import create_manual_meal_log, create_workout_log, save_daily_checkin
from backend.app.services.memory_service import generate_weekly_memory_summary, list_user_memory_summaries


def test_generate_weekly_memory_summary_from_structured_records():
    create_workout_log(
        WorkoutLogInput(
            user_id=DEMO_USER_ID,
            date=TODAY_DATE,
            status="completed",
            exercises=[{"name": "深蹲", "sets": [{"reps": 8}]}],
            rpe=8
        )
    )
    create_manual_meal_log(
        ManualMealLogInput(
            user_id=DEMO_USER_ID,
            date=TODAY_DATE,
            meal_name="训练后餐",
            foods=[
                {
                    "name": "鸡胸肉饭",
                    "portion": "1 份",
                    "calories": 620,
                    "protein_g": 42,
                    "carbs_g": 78,
                    "fat_g": 16
                }
            ]
        )
    )
    save_daily_checkin(
        DailyCheckinInput(
            user_id=DEMO_USER_ID,
            date=TODAY_DATE,
            sleep_hours=6.5,
            fatigue_level=4,
            soreness_level=3,
            stress_level=3,
            mood="low"
        )
    )

    summary = generate_weekly_memory_summary(DEMO_USER_ID, week_start="2026-07-11", week_end="2026-07-17")

    assert summary.summary_id == "memory-demo-user-945-2026-07-11"
    assert "训练 1 次" in summary.content
    assert "蛋白质 42g" in summary.content
    assert "疲劳偏高" in summary.content
    assert summary.metadata["source"] == "structured_records"
    assert list_user_memory_summaries(DEMO_USER_ID)[0].summary_id == summary.summary_id
