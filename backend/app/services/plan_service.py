from copy import deepcopy
from datetime import date, timedelta
import re

from backend.app.data.demo_data import DEMO_USER_ID, TODAY_DATE
from backend.app.models.domain import MacroTargets, MealPlan, MealPlanDay, Plan, PlanAdjustmentInput, PlanGenerateInput, PlannedFood, PlannedMeal, UserProfile, WorkoutPlan, WorkoutPlanDay
from backend.app.services.demo_seed import timestamp
from backend.app.services.demo_store import _active_repository_store, get_current_plan as get_demo_current_plan, get_profile, list_plans, save_plan


def get_current_plan(user_id: str = DEMO_USER_ID) -> Plan | None:
    store = _active_repository_store()
    if store:
        return store.get_current_plan(user_id)
    return get_demo_current_plan(user_id)


def _plan_id(kind: str) -> str:
    return f"plan-{TODAY_DATE}-{kind}-{timestamp().replace(':', '').replace('-', '')[-10:]}"


GOAL_TARGETS = {
    "fat_loss": (2100, 165, 190, 65),
    "muscle_gain": (2600, 170, 300, 75),
    "body_recomposition": (2300, 160, 240, 70),
    "strength": (2500, 165, 285, 75),
    "conditioning": (2350, 155, 275, 65),
    "maintenance": (2400, 155, 260, 75),
}


def _apply_goal_rules(plan: Plan, goal: str) -> Plan:
    calories, protein, carbs, fat = GOAL_TARGETS[goal]
    days = deepcopy(plan.workout_plan.days)
    for day in days:
        for exercise in day.exercises:
            if goal == "muscle_gain":
                exercise.sets += 1
                exercise.reps = "8-12"
            elif goal == "strength":
                exercise.sets += 1
                exercise.reps = "4-6"
                exercise.rest_seconds = max(exercise.rest_seconds, 120)
            elif goal in ("fat_loss", "conditioning"):
                exercise.sets = max(2, exercise.sets - 1)
                exercise.reps = "10-15"
    return plan.model_copy(update={
        "goal": goal,
        "workout_plan": WorkoutPlan(days=days),
        "meal_plan": plan.meal_plan.model_copy(update={
            "daily_targets": MacroTargets(calories=calories, protein_g=protein, carbs_g=carbs, fat_g=fat)
        }),
    })


def _has_any(values: list[str], terms: set[str]) -> bool:
    return any(value.lower() in terms for value in values)


def _equipment_substitution(exercise):
    replacements = {
        "ex-db-press": {"exercise_id": "ex-push-up", "name": "俯卧撑", "target_weight": "bodyweight"},
        "ex-row": {"exercise_id": "ex-prone-y-t-w", "name": "俯卧 Y-T-W", "target_weight": "bodyweight"},
        "ex-db-shoulder-press": {"exercise_id": "ex-pike-push-up", "name": "派克俯卧撑", "target_weight": "bodyweight"},
        "ex-squat": {"exercise_id": "ex-bodyweight-squat", "name": "徒手深蹲", "target_weight": "bodyweight"},
    }
    replacement = replacements.get(exercise.exercise_id)
    return exercise.model_copy(update=replacement) if replacement else exercise


def _apply_profile_workout_constraints(plan: Plan, profile: UserProfile) -> Plan:
    has_gym = _has_any(profile.equipment, {"gym", "barbell", "cable_machine"})
    has_dumbbells = _has_any(profile.equipment, {"dumbbells", "dumbbell"})
    if has_gym or has_dumbbells:
        return plan
    days = []
    for day in plan.workout_plan.days:
        days.append(day.model_copy(update={"exercises": [_equipment_substitution(exercise) for exercise in day.exercises]}))
    return plan.model_copy(update={"workout_plan": WorkoutPlan(days=days)})


def _apply_training_schedule(plan: Plan, days_per_week: int, duration_minutes: int, constraints: list[str]) -> Plan:
    templates = deepcopy(plan.workout_plan.days)
    start = date.fromisoformat(TODAY_DATE)
    busy_weekdays = _has_any(constraints, {"busy_weekdays", "工作日繁忙"})
    scheduled: list[WorkoutPlanDay] = []
    for index in range(days_per_week):
        template = templates[index % len(templates)]
        scheduled_date = start + timedelta(days=round(index * 7 / days_per_week))
        day_duration = min(duration_minutes, 45) if busy_weekdays and scheduled_date.weekday() < 5 else duration_minutes
        exercises = template.exercises if day_duration >= 60 else template.exercises[: max(1, min(2, len(template.exercises)))]
        scheduled.append(template.model_copy(update={
            "date": scheduled_date.isoformat(),
            "duration_minutes": day_duration,
            "exercises": exercises,
        }))
    return plan.model_copy(update={"workout_plan": WorkoutPlan(days=scheduled)})


def _scale_portion(portion: str, multiplier: float) -> str:
    """Scale the leading quantity while keeping the existing serving unit."""
    match = re.match(r"^(\d+(?:\.\d+)?)(\s*)(.*)$", portion)
    if match is None:
        return portion
    quantity = float(match.group(1)) * multiplier
    display = str(int(round(quantity))) if quantity >= 10 else f"{quantity:.1f}".rstrip("0").rstrip(".")
    return f"{display}{match.group(2)}{match.group(3)}".strip()


def _scale_foods(meal, values: dict[str, int]) -> list[PlannedFood]:
    """Make the visible foods add up to the macro target assigned to a meal."""
    original_calories = max(1, meal.total_macros.calories)
    multiplier = values["calories"] / original_calories
    foods: list[PlannedFood] = []
    allocated = {key: 0 for key in values}
    for index, food in enumerate(meal.foods):
        if index == len(meal.foods) - 1:
            macros = {key: values[key] - allocated[key] for key in values}
        else:
            macros = {key: round(getattr(food, key) * multiplier) for key in values}
            allocated = {key: allocated[key] + macros[key] for key in values}
        foods.append(food.model_copy(update={
            "portion": _scale_portion(food.portion, multiplier),
            **macros,
        }))
    return foods


def _apply_meal_schedule(plan: Plan, days: int) -> Plan:
    target = plan.meal_plan.daily_targets
    ratios = (0.3, 0.4, 0.3)
    start = date.fromisoformat(TODAY_DATE)
    template = deepcopy(plan.meal_plan.days[0].meals)
    scheduled: list[MealPlanDay] = []
    for day_index in range(days):
        meals = []
        allocated = {"calories": 0, "protein_g": 0, "carbs_g": 0, "fat_g": 0}
        for index, meal in enumerate(template):
            values = {
                "calories": round(target.calories * ratios[index]),
                "protein_g": round(target.protein_g * ratios[index]),
                "carbs_g": round(target.carbs_g * ratios[index]),
                "fat_g": round(target.fat_g * ratios[index]),
            }
            if index == len(template) - 1:
                values = {key: getattr(target, key) - allocated[key] for key in allocated}
            allocated = {key: allocated[key] + values[key] for key in allocated}
            meals.append(meal.model_copy(update={
                "meal_id": f"meal-{day_index + 1}-{index + 1}",
                "foods": _scale_foods(meal, values),
                "total_macros": MacroTargets(**values),
            }))
        scheduled.append(MealPlanDay(date=(start + timedelta(days=day_index)).isoformat(), meals=meals))
    return plan.model_copy(update={"meal_plan": MealPlan(daily_targets=target, days=scheduled)})


def _replacement_food(food: PlannedFood, profile: UserProfile) -> PlannedFood:
    allergies = {value.lower() for value in profile.allergies}
    preferences = {value.lower() for value in profile.dietary_preferences}
    vegan = bool(preferences & {"vegan", "纯素"})
    vegetarian = vegan or bool(preferences & {"vegetarian", "素食"})
    dairy_free = bool(allergies & {"dairy", "milk", "lactose", "乳制品", "牛奶", "乳糖"})
    seafood_free = bool(allergies & {"fish", "seafood", "鱼", "海鲜"})
    gluten_free = bool(allergies & {"gluten", "麸质"})
    if food.name == "希腊酸奶" and (vegan or dairy_free):
        return food.model_copy(update={"name": "无糖豆乳酸奶", "portion": "250g", "calories": 150, "protein_g": 12, "carbs_g": 10, "fat_g": 7})
    if food.name == "燕麦片" and gluten_free:
        return food.model_copy(update={"name": "米饭", "portion": "150g", "calories": 175, "protein_g": 4, "carbs_g": 39, "fat_g": 0})
    if food.name == "鸡胸肉饭碗" and vegetarian:
        return food.model_copy(update={"name": "豆腐藜麦饭碗", "portion": "1 bowl", "calories": 560, "protein_g": 30, "carbs_g": 72, "fat_g": 18})
    if food.name == "三文鱼" and (vegetarian or seafood_free):
        name = "烤豆腐" if vegetarian else "鸡胸肉"
        return food.model_copy(update={"name": name, "portion": "220g" if vegetarian else "180g", "calories": 290, "protein_g": 28 if vegetarian else 54, "carbs_g": 8 if vegetarian else 0, "fat_g": 16 if vegetarian else 6})
    return food


def _apply_profile_meal_constraints(plan: Plan, profile: UserProfile) -> Plan:
    days = []
    for day in plan.meal_plan.days:
        meals = [meal.model_copy(update={"foods": [_replacement_food(food, profile) for food in meal.foods]}) for meal in day.meals]
        days.append(day.model_copy(update={"meals": meals}))
    return plan.model_copy(update={"meal_plan": plan.meal_plan.model_copy(update={"days": days})})


def generate_plan(input_data: PlanGenerateInput) -> Plan | None:
    current = get_current_plan(input_data.user_id)
    profile = get_profile(input_data.user_id)
    if current is None or profile is None:
        return None
    now = timestamp()
    goal = input_data.goal or profile.goal
    base_plan = _apply_profile_meal_constraints(_apply_profile_workout_constraints(
        _apply_goal_rules(deepcopy(current), goal), profile), profile)
    tailored = _apply_meal_schedule(_apply_training_schedule(base_plan,
        profile.training_days_per_week,
        profile.training_duration_minutes,
        profile.constraints,
    ), input_data.days)
    draft = tailored.model_copy(update={
        "plan_id": _plan_id("draft"),
        "status": "draft",
        "generated_by": "mock",
        "created_at": now,
        "updated_at": now,
    })
    store = _active_repository_store()
    return store.save_plan(draft) if store else save_plan(draft)


def accept_plan(user_id: str, plan_id: str) -> Plan | None:
    store = _active_repository_store()
    plans = store.list_plans(user_id) if store else list_plans(user_id)
    candidate = next((plan for plan in plans or [] if plan.plan_id == plan_id and plan.status == "draft"), None)
    if candidate is None:
        return None
    current = get_current_plan(user_id)
    if current:
        (store.save_plan if store else save_plan)(current.model_copy(update={"status": "archived", "updated_at": timestamp()}))
    return (store.save_plan if store else save_plan)(candidate.model_copy(update={"status": "active", "updated_at": timestamp()}))


def adjust_plan(plan_id: str, input_data: PlanAdjustmentInput) -> Plan | None:
    current = get_current_plan(input_data.user_id)
    if current is None or current.plan_id != plan_id:
        return None
    days = deepcopy(current.workout_plan.days)
    meals_by_day = deepcopy(current.meal_plan.days)
    target_date = input_data.target_date or TODAY_DATE
    workout_day = next((day for day in days if day.date == target_date), None)
    meal_day = next((day for day in meals_by_day if day.date == target_date), None)
    if input_data.adjustment_type == "reduce_intensity":
        for exercise in (workout_day.exercises if workout_day else []):
            exercise.sets = max(1, exercise.sets - 1)
            exercise.notes = input_data.reason
    elif input_data.adjustment_type == "increase_intensity":
        for exercise in (workout_day.exercises if workout_day else []):
            exercise.sets += 1
            exercise.notes = input_data.reason
    elif input_data.adjustment_type == "skip_workout" and workout_day:
        days[days.index(workout_day)] = workout_day.model_copy(update={
            "name": "恢复日",
            "focus": "recovery",
            "duration_minutes": 0,
            "exercises": [],
        })
    elif input_data.adjustment_type == "change_schedule" and workout_day:
        days[days.index(workout_day)] = workout_day.model_copy(update={
            "date": (date.fromisoformat(workout_day.date) + timedelta(days=1)).isoformat(),
        })
    elif input_data.adjustment_type == "swap_exercise" and workout_day:
        exercise = next((item for item in workout_day.exercises if item.exercise_id == input_data.target_exercise_id), workout_day.exercises[0] if workout_day.exercises else None)
        if exercise:
            replacement = exercise.model_copy(update={
                "exercise_id": f"custom-{exercise.exercise_id}",
                "name": input_data.replacement_name or "高脚杯深蹲",
                "notes": input_data.reason,
            })
            workout_day.exercises[workout_day.exercises.index(exercise)] = replacement
    elif input_data.adjustment_type == "swap_meal" and meal_day:
        meal = next((item for item in meal_day.meals if item.meal_id == input_data.target_meal_id), meal_day.meals[0] if meal_day.meals else None)
        if meal:
            alternate = meal.model_copy(update={"foods": [PlannedFood(name=input_data.replacement_name or "鸡肉藜麦饭碗", portion="1 bowl", calories=560, protein_g=42, carbs_g=64, fat_g=16)]})
            meal_day.meals[meal_day.meals.index(meal)] = alternate.model_copy(update={"foods": _scale_foods(alternate, meal.total_macros.model_dump())})
    now = timestamp()
    adjusted = current.model_copy(update={
        "plan_id": _plan_id("adjusted"),
        "status": "active",
        "workout_plan": WorkoutPlan(days=days),
        "meal_plan": current.meal_plan.model_copy(update={"days": meals_by_day}),
        "generated_by": "agent",
        "created_at": now,
        "updated_at": now,
    })
    store = _active_repository_store()
    writer = store.save_plan if store else save_plan
    writer(current.model_copy(update={"status": "archived", "updated_at": now}))
    return writer(adjusted)
