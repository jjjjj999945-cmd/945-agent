from datetime import UTC, datetime

from backend.app.data.demo_data import DEMO_PLAN, DEMO_USER_ID, create_today_response
from backend.app.models.domain import (
    BodyMetric,
    BodyMetricInput,
    ConfirmPlannedMealInput,
    DailyCheckin,
    DailyCheckinInput,
    FoodLog,
    ManualMealLogInput,
    MealLog,
    TodayResponseData,
    WorkoutLog,
    WorkoutLogInput,
)


workout_logs: list[WorkoutLog] = []
meal_logs: list[MealLog] = []
body_metrics: list[BodyMetric] = []
daily_checkins: list[DailyCheckin] = []


def reset_demo_store() -> None:
    workout_logs.clear()
    meal_logs.clear()
    body_metrics.clear()
    daily_checkins.clear()


def timestamp() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def is_demo_user(user_id: str) -> bool:
    return user_id == DEMO_USER_ID


def create_workout_log(input_data: WorkoutLogInput) -> WorkoutLog | None:
    if not is_demo_user(input_data.user_id):
        return None

    now = timestamp()
    saved = WorkoutLog(
        **input_data.model_dump(),
        workout_log_id=f"workout-{input_data.date}-{len(workout_logs) + 1}",
        created_at=now,
        updated_at=now
    )
    workout_logs.append(saved)
    return saved


def list_workout_logs(user_id: str) -> list[WorkoutLog] | None:
    if not is_demo_user(user_id):
        return None

    return [log for log in workout_logs if log.user_id == user_id]


def _sum_foods(foods: list[FoodLog]) -> dict[str, int]:
    return {
        "calories": sum(food.calories for food in foods),
        "protein_g": sum(food.protein_g for food in foods),
        "carbs_g": sum(food.carbs_g for food in foods),
        "fat_g": sum(food.fat_g for food in foods)
    }


def confirm_planned_meal(input_data: ConfirmPlannedMealInput) -> MealLog | None:
    if not is_demo_user(input_data.user_id):
        return None

    day = next((item for item in DEMO_PLAN.meal_plan.days if item.date == input_data.date), None)
    meal = next((item for item in day.meals if item.meal_id == input_data.meal_id), None) if day else None
    if meal is None:
        return None

    now = timestamp()
    foods = [FoodLog(**food.model_dump()) for food in meal.foods]
    saved = MealLog(
        meal_log_id=f"meal-log-{input_data.meal_id}-{len(meal_logs) + 1}",
        user_id=input_data.user_id,
        plan_id=input_data.plan_id,
        date=input_data.date,
        meal_id=input_data.meal_id,
        meal_name=meal.name,
        source="planned_meal_confirmation",
        foods=foods,
        calories=meal.total_macros.calories,
        protein_g=meal.total_macros.protein_g,
        carbs_g=meal.total_macros.carbs_g,
        fat_g=meal.total_macros.fat_g,
        created_at=now,
        updated_at=now
    )
    meal_logs.append(saved)
    return saved


def create_manual_meal_log(input_data: ManualMealLogInput) -> MealLog | None:
    if not is_demo_user(input_data.user_id):
        return None

    now = timestamp()
    totals = _sum_foods(input_data.foods)
    saved = MealLog(
        **input_data.model_dump(),
        meal_log_id=f"meal-log-manual-{input_data.date}-{len(meal_logs) + 1}",
        source="manual_entry",
        **totals,
        created_at=now,
        updated_at=now
    )
    meal_logs.append(saved)
    return saved


def list_meal_logs(user_id: str) -> list[MealLog] | None:
    if not is_demo_user(user_id):
        return None

    return [log for log in meal_logs if log.user_id == user_id]


def save_body_metric(input_data: BodyMetricInput) -> BodyMetric | None:
    if not is_demo_user(input_data.user_id):
        return None

    saved = BodyMetric(
        **input_data.model_dump(),
        metric_id=f"metric-{input_data.date}-{len(body_metrics) + 1}",
        created_at=timestamp()
    )
    body_metrics.append(saved)
    return saved


def list_body_metrics(user_id: str) -> list[BodyMetric] | None:
    if not is_demo_user(user_id):
        return None

    return sorted([metric for metric in body_metrics if metric.user_id == user_id], key=lambda metric: metric.date)


def save_daily_checkin(input_data: DailyCheckinInput) -> DailyCheckin | None:
    if not is_demo_user(input_data.user_id):
        return None

    existing = next(
        (
            checkin
            for checkin in daily_checkins
            if checkin.user_id == input_data.user_id and checkin.date == input_data.date
        ),
        None
    )
    now = timestamp()
    saved = DailyCheckin(
        **input_data.model_dump(),
        checkin_id=existing.checkin_id if existing else f"checkin-{input_data.date}-{len(daily_checkins) + 1}",
        created_at=existing.created_at if existing else now,
        updated_at=now
    )

    if existing:
        index = daily_checkins.index(existing)
        daily_checkins[index] = saved
    else:
        daily_checkins.append(saved)

    return saved


def get_daily_checkin(user_id: str, date: str) -> DailyCheckin | None:
    return next((checkin for checkin in daily_checkins if checkin.user_id == user_id and checkin.date == date), None)


def build_today_response(user_id: str, date: str) -> TodayResponseData | None:
    if not is_demo_user(user_id):
        return None

    today = create_today_response(date)
    today_meal_logs = [log for log in meal_logs if log.user_id == user_id and log.date == date]
    calories_logged = sum(log.calories for log in today_meal_logs)
    protein_logged = sum(log.protein_g for log in today_meal_logs)
    completed_workouts = len(
        [
            log
            for log in workout_logs
            if log.user_id == user_id and log.status in ("completed", "partially_completed")
        ]
    )
    checkin = get_daily_checkin(user_id, date)

    recovery_status = today.status_summary.recovery_status
    if checkin and (
        (checkin.fatigue_level is not None and checkin.fatigue_level >= 4)
        or (checkin.soreness_level is not None and checkin.soreness_level >= 4)
        or (checkin.sleep_hours is not None and checkin.sleep_hours < 7)
    ):
        recovery_status = "fatigued"

    today.status_summary.calories_logged = max(today.status_summary.calories_logged, calories_logged)
    today.status_summary.protein_logged_g = max(today.status_summary.protein_logged_g, protein_logged)
    today.status_summary.weekly_workouts_completed = max(
        today.status_summary.weekly_workouts_completed,
        3 + completed_workouts
    )
    today.status_summary.recovery_status = recovery_status
    today.daily_checkin = checkin
    return today
