from copy import deepcopy

from backend.app.core.config import get_settings as get_app_settings
from backend.app.data.demo_data import DEMO_ADVICE, DEMO_PLAN, DEMO_USER, DEMO_USER_ID, create_today_response
from backend.app.models.domain import (
    AdvicePageData,
    AdviceStatus,
    AgentAdvice,
    AgentMessage,
    BodyMetric,
    BodyMetricInput,
    ConfirmPlannedMealInput,
    DailyCheckin,
    DailyCheckinInput,
    FoodLog,
    ManualMealLogInput,
    MealLog,
    Plan,
    ProfileCreateInput,
    ProfilePatchInput,
    SettingsData,
    SettingsPatchInput,
    TodayResponseData,
    User,
    UserMemorySummary,
    UserProfile,
    WorkoutLog,
    WorkoutLogInput,
)
from backend.app.repositories.mongo import create_mongo_repository
from backend.app.services.demo_seed import INITIAL_PROFILE, INITIAL_WEEKLY_ADVICE, timestamp
from backend.app.services.repository_store import RepositoryBackedStore


current_user: User = deepcopy(DEMO_USER)
current_profile: UserProfile = deepcopy(INITIAL_PROFILE)
plans = [deepcopy(DEMO_PLAN)]
advice_items: list[AgentAdvice] = [deepcopy(DEMO_ADVICE), deepcopy(INITIAL_WEEKLY_ADVICE)]
workout_logs: list[WorkoutLog] = []
meal_logs: list[MealLog] = []
body_metrics: list[BodyMetric] = []
daily_checkins: list[DailyCheckin] = []
agent_messages: list[AgentMessage] = []
user_memory_summaries: list[UserMemorySummary] = []
_repository_store_override: RepositoryBackedStore | None = None
_repository_store: RepositoryBackedStore | None = None


def set_repository_store_for_tests(store: RepositoryBackedStore | None) -> None:
    global _repository_store_override

    _repository_store_override = store


def _active_repository_store() -> RepositoryBackedStore | None:
    global _repository_store

    if get_app_settings().storage_backend != "mongo":
        return None
    if _repository_store_override is not None:
        return _repository_store_override
    if _repository_store is None:
        _repository_store = RepositoryBackedStore(create_mongo_repository())
        _repository_store.seed_demo_data()
    return _repository_store


def reset_demo_store() -> None:
    global current_user, current_profile, advice_items, plans

    current_user = deepcopy(DEMO_USER)
    current_profile = deepcopy(INITIAL_PROFILE)
    advice_items = [deepcopy(DEMO_ADVICE), deepcopy(INITIAL_WEEKLY_ADVICE)]
    plans = [deepcopy(DEMO_PLAN)]
    workout_logs.clear()
    meal_logs.clear()
    body_metrics.clear()
    daily_checkins.clear()
    agent_messages.clear()
    user_memory_summaries.clear()


def is_demo_user(user_id: str) -> bool:
    store = _active_repository_store()
    if store:
        return store.is_demo_user(user_id)
    return user_id == DEMO_USER_ID


def get_current_user() -> User:
    store = _active_repository_store()
    if store:
        return store.get_current_user()
    return current_user


def get_profile(user_id: str) -> UserProfile | None:
    store = _active_repository_store()
    if store:
        return store.get_profile(user_id)
    if not is_demo_user(user_id):
        return None

    return current_profile


def save_profile(input_data: ProfileCreateInput) -> UserProfile | None:
    global current_profile, current_user

    store = _active_repository_store()
    if store:
        return store.save_profile(input_data)
    if not is_demo_user(input_data.user_id):
        return None

    now = timestamp()
    current_user = User(
        user_id=input_data.user_id,
        display_name=input_data.display_name,
        locale=input_data.locale,
        unit_system=input_data.unit_system,
        created_at=current_user.created_at,
        updated_at=now
    )
    current_profile = UserProfile(
        profile_id="profile-demo-user-945",
        user_id=input_data.user_id,
        age=input_data.age,
        gender=input_data.gender,
        height_cm=input_data.height_cm,
        weight_kg=input_data.weight_kg,
        goal=input_data.goal,
        experience_level=input_data.experience_level,
        training_days_per_week=input_data.training_days_per_week,
        training_duration_minutes=input_data.training_duration_minutes,
        equipment=input_data.equipment,
        dietary_preferences=input_data.dietary_preferences,
        allergies=input_data.allergies,
        constraints=input_data.constraints,
        updated_at=now
    )
    return current_profile


def update_profile(user_id: str, input_data: ProfilePatchInput) -> UserProfile | None:
    global current_profile

    store = _active_repository_store()
    if store:
        return store.update_profile(user_id, input_data)
    if not is_demo_user(user_id):
        return None

    updates = input_data.model_dump(exclude_unset=True)
    current_profile = current_profile.model_copy(update={**updates, "updated_at": timestamp()})
    return current_profile


def get_settings(user_id: str) -> SettingsData | None:
    store = _active_repository_store()
    if store:
        return store.get_settings(user_id)
    if not is_demo_user(user_id):
        return None

    return SettingsData(
        user=current_user,
        profile=current_profile,
        language=current_user.locale,
        unit_system=current_user.unit_system
    )


def update_settings(input_data: SettingsPatchInput) -> SettingsData | None:
    global current_user, current_profile

    store = _active_repository_store()
    if store:
        return store.update_settings(input_data)
    if not is_demo_user(input_data.user_id):
        return None

    now = timestamp()
    current_user = current_user.model_copy(
        update={
            "locale": input_data.language or current_user.locale,
            "unit_system": input_data.unit_system or current_user.unit_system,
            "updated_at": now
        }
    )

    if input_data.profile is not None:
        updates = input_data.profile.model_dump(exclude_unset=True)
        current_profile = current_profile.model_copy(update={**updates, "updated_at": now})

    return get_settings(input_data.user_id)


def get_advice(user_id: str) -> AdvicePageData | None:
    store = _active_repository_store()
    if store:
        return store.get_advice(user_id)
    if not is_demo_user(user_id):
        return None

    return AdvicePageData(
        daily=next((item for item in advice_items if item.type == "daily_advice"), None),
        weekly=next((item for item in advice_items if item.type == "weekly_summary"), None),
        adjustments=[item for item in advice_items if item.type == "plan_adjustment"]
    )


def update_advice_status(user_id: str, advice_id: str, accepted_status: AdviceStatus) -> AgentAdvice | None:
    store = _active_repository_store()
    if store:
        return store.update_advice_status(user_id, advice_id, accepted_status)
    if not is_demo_user(user_id):
        return None

    existing = next((item for item in advice_items if item.advice_id == advice_id), None)
    if existing is None:
        return None

    updated = existing.model_copy(update={"accepted_status": accepted_status})
    advice_items[advice_items.index(existing)] = updated
    return updated


def save_agent_message(message: AgentMessage) -> AgentMessage:
    store = _active_repository_store()
    if store:
        return store.save_agent_message(message)
    agent_messages.append(message)
    return message


def list_agent_messages(user_id: str) -> list[AgentMessage] | None:
    store = _active_repository_store()
    if store:
        return store.list_agent_messages(user_id)
    if not is_demo_user(user_id):
        return None

    return [message for message in agent_messages if message.user_id == user_id]


def get_current_plan(user_id: str) -> Plan | None:
    if not is_demo_user(user_id):
        return None
    return next((plan for plan in reversed(plans) if plan.status == "active"), None)


def list_plans(user_id: str) -> list[Plan] | None:
    if not is_demo_user(user_id):
        return None
    return [plan for plan in plans if plan.user_id == user_id]


def save_plan(plan: Plan) -> Plan | None:
    if not is_demo_user(plan.user_id):
        return None
    existing = next((item for item in plans if item.plan_id == plan.plan_id), None)
    if existing is None:
        plans.append(plan)
    else:
        plans[plans.index(existing)] = plan
    return plan


def save_user_memory_summary(summary: UserMemorySummary) -> UserMemorySummary:
    store = _active_repository_store()
    if store:
        return store.save_user_memory_summary(summary)

    existing = next((item for item in user_memory_summaries if item.summary_id == summary.summary_id), None)
    if existing:
        user_memory_summaries[user_memory_summaries.index(existing)] = summary
    else:
        user_memory_summaries.append(summary)
    return summary


def list_user_memory_summaries(user_id: str) -> list[UserMemorySummary] | None:
    store = _active_repository_store()
    if store:
        return store.list_user_memory_summaries(user_id)
    if not is_demo_user(user_id):
        return None
    return [summary for summary in user_memory_summaries if summary.user_id == user_id]


def create_workout_log(input_data: WorkoutLogInput) -> WorkoutLog | None:
    store = _active_repository_store()
    if store:
        return store.create_workout_log(input_data)
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
    store = _active_repository_store()
    if store:
        return store.list_workout_logs(user_id)
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
    store = _active_repository_store()
    if store:
        return store.confirm_planned_meal(input_data)
    if not is_demo_user(input_data.user_id):
        return None

    plan = get_current_plan(input_data.user_id)
    day = next((item for item in plan.meal_plan.days if item.date == input_data.date), None) if plan else None
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
    store = _active_repository_store()
    if store:
        return store.create_manual_meal_log(input_data)
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
    store = _active_repository_store()
    if store:
        return store.list_meal_logs(user_id)
    if not is_demo_user(user_id):
        return None

    return [log for log in meal_logs if log.user_id == user_id]


def save_body_metric(input_data: BodyMetricInput) -> BodyMetric | None:
    store = _active_repository_store()
    if store:
        return store.save_body_metric(input_data)
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
    store = _active_repository_store()
    if store:
        return store.list_body_metrics(user_id)
    if not is_demo_user(user_id):
        return None

    return sorted([metric for metric in body_metrics if metric.user_id == user_id], key=lambda metric: metric.date)


def save_daily_checkin(input_data: DailyCheckinInput) -> DailyCheckin | None:
    store = _active_repository_store()
    if store:
        return store.save_daily_checkin(input_data)
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
    store = _active_repository_store()
    if store:
        return store.get_daily_checkin(user_id, date)
    return next((checkin for checkin in daily_checkins if checkin.user_id == user_id and checkin.date == date), None)


def list_daily_checkins(user_id: str) -> list[DailyCheckin] | None:
    store = _active_repository_store()
    if store:
        return store.list_daily_checkins(user_id)
    if not is_demo_user(user_id):
        return None
    return [checkin for checkin in daily_checkins if checkin.user_id == user_id]


def build_today_response(user_id: str, date: str) -> TodayResponseData | None:
    store = _active_repository_store()
    if store:
        return store.build_today_response(user_id, date)
    if not is_demo_user(user_id):
        return None

    today = create_today_response(date)
    plan = get_current_plan(user_id)
    if plan is not None:
        today.today_workout = next((day for day in plan.workout_plan.days if day.date == date), None)
        today.today_meals = next((day.meals for day in plan.meal_plan.days if day.date == date), [])
        today.status_summary.calories_target = plan.meal_plan.daily_targets.calories
        today.status_summary.protein_target_g = plan.meal_plan.daily_targets.protein_g
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
