from backend.app.models.domain import UserMemorySummary
from backend.app.services.demo_seed import timestamp
from backend.app.services.demo_store import (
    list_daily_checkins,
    list_meal_logs,
    list_user_memory_summaries as list_saved_memory_summaries,
    list_workout_logs,
    save_user_memory_summary,
)


def _filter_dates(items, week_start: str, week_end: str):
    return [item for item in items if week_start <= item.date <= week_end]


def generate_weekly_memory_summary(user_id: str, week_start: str, week_end: str) -> UserMemorySummary:
    workouts = _filter_dates(list_workout_logs(user_id) or [], week_start, week_end)
    meals = _filter_dates(list_meal_logs(user_id) or [], week_start, week_end)
    checkins = _filter_dates(list_daily_checkins(user_id) or [], week_start, week_end)
    protein = sum(meal.protein_g for meal in meals)
    calories = sum(meal.calories for meal in meals)
    high_fatigue = any((checkin.fatigue_level or 0) >= 4 for checkin in checkins)
    recovery_copy = "疲劳偏高" if high_fatigue else "恢复信号正常"
    content = (
        f"用户本周训练 {len(workouts)} 次，记录饮食 {len(meals)} 次，"
        f"累计蛋白质 {protein}g，累计热量 {calories}kcal，{recovery_copy}。"
    )
    summary = UserMemorySummary(
        summary_id=f"memory-{user_id}-{week_start}",
        user_id=user_id,
        week_start=week_start,
        week_end=week_end,
        content=content,
        metadata={
            "source": "structured_records",
            "summary_type": "weekly",
            "locale": "zh-CN"
        },
        created_at=timestamp()
    )
    return save_user_memory_summary(summary)


def list_user_memory_summaries(user_id: str) -> list[UserMemorySummary]:
    return list_saved_memory_summaries(user_id) or []
