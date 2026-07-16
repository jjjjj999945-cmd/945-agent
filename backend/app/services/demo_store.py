from datetime import UTC, datetime

from backend.app.data.demo_data import DEMO_PLAN, DEMO_USER_ID
from backend.app.models.domain import (
    ConfirmPlannedMealInput,
    FoodLog,
    ManualMealLogInput,
    MealLog,
    WorkoutLog,
    WorkoutLogInput,
)


workout_logs: list[WorkoutLog] = []
meal_logs: list[MealLog] = []


def timestamp() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


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
