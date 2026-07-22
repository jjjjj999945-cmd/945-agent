from copy import deepcopy

from backend.app.data.demo_data import DEMO_ADVICE, DEMO_PLAN, DEMO_USER, DEMO_USER_ID, NOW, create_today_response
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
from backend.app.repositories.mongo import MongoRepository
from backend.app.services.demo_seed import INITIAL_PROFILE, INITIAL_WEEKLY_ADVICE, timestamp


COLLECTION_IDS = {
    "users": "user_id",
    "user_profiles": "profile_id",
    "plans": "plan_id",
    "workout_logs": "workout_log_id",
    "meal_logs": "meal_log_id",
    "body_metrics": "metric_id",
    "daily_checkins": "checkin_id",
    "agent_advice": "advice_id",
    "agent_messages": "message_id",
    "user_memory_summaries": "summary_id",
}


class RepositoryBackedStore:
    def __init__(self, repository: MongoRepository):
        self.repository = repository

    def seed_demo_data(self) -> None:
        self.repository.upsert_model("users", deepcopy(DEMO_USER), id_field=COLLECTION_IDS["users"])
        self.repository.upsert_model("user_profiles", deepcopy(INITIAL_PROFILE), id_field=COLLECTION_IDS["user_profiles"])
        self.repository.upsert_model("plans", deepcopy(DEMO_PLAN), id_field=COLLECTION_IDS["plans"])
        self.repository.upsert_model("agent_advice", deepcopy(DEMO_ADVICE), id_field=COLLECTION_IDS["agent_advice"])
        self.repository.upsert_model(
            "agent_advice",
            deepcopy(INITIAL_WEEKLY_ADVICE),
            id_field=COLLECTION_IDS["agent_advice"]
        )

    def is_demo_user(self, user_id: str) -> bool:
        return self.get_current_user().user_id == user_id

    def get_current_user(self) -> User:
        user = self.repository.get_model("users", User, {"user_id": DEMO_USER_ID})
        if user is None:
            self.seed_demo_data()
            user = self.repository.get_model("users", User, {"user_id": DEMO_USER_ID})
        return user

    def get_profile(self, user_id: str) -> UserProfile | None:
        if user_id != DEMO_USER_ID:
            return None
        return self.repository.get_model("user_profiles", UserProfile, {"user_id": user_id})

    def save_profile(self, input_data: ProfileCreateInput) -> UserProfile | None:
        if input_data.user_id != DEMO_USER_ID:
            return None
        now = timestamp()
        existing_user = self.get_current_user()
        user = User(
            user_id=input_data.user_id,
            display_name=input_data.display_name,
            locale=input_data.locale,
            unit_system=input_data.unit_system,
            created_at=existing_user.created_at,
            updated_at=now
        )
        profile = UserProfile(
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
        self.repository.upsert_model("users", user, id_field=COLLECTION_IDS["users"])
        self.repository.upsert_model("user_profiles", profile, id_field=COLLECTION_IDS["user_profiles"])
        return profile

    def update_profile(self, user_id: str, input_data: ProfilePatchInput) -> UserProfile | None:
        profile = self.get_profile(user_id)
        if profile is None:
            return None
        updated = profile.model_copy(update={**input_data.model_dump(exclude_unset=True), "updated_at": timestamp()})
        self.repository.upsert_model("user_profiles", updated, id_field=COLLECTION_IDS["user_profiles"])
        return updated

    def get_settings(self, user_id: str) -> SettingsData | None:
        profile = self.get_profile(user_id)
        if profile is None:
            return None
        user = self.get_current_user()
        return SettingsData(user=user, profile=profile, language=user.locale, unit_system=user.unit_system)

    def update_settings(self, input_data: SettingsPatchInput) -> SettingsData | None:
        if input_data.user_id != DEMO_USER_ID:
            return None
        user = self.get_current_user()
        updated_user = user.model_copy(
            update={
                "locale": input_data.language or user.locale,
                "unit_system": input_data.unit_system or user.unit_system,
                "updated_at": timestamp()
            }
        )
        self.repository.upsert_model("users", updated_user, id_field=COLLECTION_IDS["users"])
        if input_data.profile is not None:
            self.update_profile(input_data.user_id, input_data.profile)
        return self.get_settings(input_data.user_id)

    def get_current_plan(self, user_id: str) -> Plan | None:
        if user_id != DEMO_USER_ID:
            return None
        return self.repository.get_model("plans", Plan, {"user_id": user_id, "status": "active"})

    def save_plan(self, plan: Plan) -> Plan | None:
        if plan.user_id != DEMO_USER_ID:
            return None
        self.repository.upsert_model("plans", plan, id_field=COLLECTION_IDS["plans"])
        return plan

    def list_plans(self, user_id: str) -> list[Plan] | None:
        if user_id != DEMO_USER_ID:
            return None
        return self.repository.list_models("plans", Plan, {"user_id": user_id})

    def get_advice(self, user_id: str) -> AdvicePageData | None:
        if user_id != DEMO_USER_ID:
            return None
        advice = self.repository.list_models("agent_advice", AgentAdvice, {"user_id": user_id})
        return AdvicePageData(
            daily=next((item for item in advice if item.type == "daily_advice"), None),
            weekly=next((item for item in advice if item.type == "weekly_summary"), None),
            adjustments=[item for item in advice if item.type == "plan_adjustment"]
        )

    def update_advice_status(
        self,
        user_id: str,
        advice_id: str,
        accepted_status: AdviceStatus
    ) -> AgentAdvice | None:
        if user_id != DEMO_USER_ID:
            return None
        advice = self.repository.get_model("agent_advice", AgentAdvice, {"advice_id": advice_id, "user_id": user_id})
        if advice is None:
            return None
        updated = advice.model_copy(update={"accepted_status": accepted_status})
        self.repository.upsert_model("agent_advice", updated, id_field=COLLECTION_IDS["agent_advice"])
        return updated

    def create_workout_log(self, input_data: WorkoutLogInput) -> WorkoutLog | None:
        if input_data.user_id != DEMO_USER_ID:
            return None
        now = timestamp()
        count = len(self.list_workout_logs(input_data.user_id))
        saved = WorkoutLog(
            **input_data.model_dump(),
            workout_log_id=f"workout-{input_data.date}-{count + 1}",
            created_at=now,
            updated_at=now
        )
        self.repository.upsert_model("workout_logs", saved, id_field=COLLECTION_IDS["workout_logs"])
        return saved

    def list_workout_logs(self, user_id: str) -> list[WorkoutLog] | None:
        if user_id != DEMO_USER_ID:
            return None
        return self.repository.list_models("workout_logs", WorkoutLog, {"user_id": user_id})

    def confirm_planned_meal(self, input_data: ConfirmPlannedMealInput) -> MealLog | None:
        if input_data.user_id != DEMO_USER_ID:
            return None
        plan = self.get_current_plan(input_data.user_id)
        day = next((item for item in plan.meal_plan.days if item.date == input_data.date), None) if plan else None
        meal = next((item for item in day.meals if item.meal_id == input_data.meal_id), None) if day else None
        if meal is None:
            return None
        now = timestamp()
        foods = [FoodLog(**food.model_dump()) for food in meal.foods]
        saved = MealLog(
            meal_log_id=f"meal-log-{input_data.meal_id}-{len(self.list_meal_logs(input_data.user_id)) + 1}",
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
        self.repository.upsert_model("meal_logs", saved, id_field=COLLECTION_IDS["meal_logs"])
        return saved

    def create_manual_meal_log(self, input_data: ManualMealLogInput) -> MealLog | None:
        if input_data.user_id != DEMO_USER_ID:
            return None
        now = timestamp()
        saved = MealLog(
            **input_data.model_dump(),
            meal_log_id=f"meal-log-manual-{input_data.date}-{len(self.list_meal_logs(input_data.user_id)) + 1}",
            source="manual_entry",
            calories=sum(food.calories for food in input_data.foods),
            protein_g=sum(food.protein_g for food in input_data.foods),
            carbs_g=sum(food.carbs_g for food in input_data.foods),
            fat_g=sum(food.fat_g for food in input_data.foods),
            created_at=now,
            updated_at=now
        )
        self.repository.upsert_model("meal_logs", saved, id_field=COLLECTION_IDS["meal_logs"])
        return saved

    def list_meal_logs(self, user_id: str) -> list[MealLog] | None:
        if user_id != DEMO_USER_ID:
            return None
        return self.repository.list_models("meal_logs", MealLog, {"user_id": user_id})

    def save_body_metric(self, input_data: BodyMetricInput) -> BodyMetric | None:
        if input_data.user_id != DEMO_USER_ID:
            return None
        saved = BodyMetric(
            **input_data.model_dump(),
            metric_id=f"metric-{input_data.date}-{len(self.list_body_metrics(input_data.user_id)) + 1}",
            created_at=timestamp()
        )
        self.repository.upsert_model("body_metrics", saved, id_field=COLLECTION_IDS["body_metrics"])
        return saved

    def list_body_metrics(self, user_id: str) -> list[BodyMetric] | None:
        if user_id != DEMO_USER_ID:
            return None
        return sorted(
            self.repository.list_models("body_metrics", BodyMetric, {"user_id": user_id}),
            key=lambda metric: metric.date
        )

    def save_daily_checkin(self, input_data: DailyCheckinInput) -> DailyCheckin | None:
        if input_data.user_id != DEMO_USER_ID:
            return None
        existing = self.get_daily_checkin(input_data.user_id, input_data.date)
        now = timestamp()
        saved = DailyCheckin(
            **input_data.model_dump(),
            checkin_id=existing.checkin_id if existing else f"checkin-{input_data.date}-1",
            created_at=existing.created_at if existing else now,
            updated_at=now
        )
        self.repository.upsert_model("daily_checkins", saved, id_field=COLLECTION_IDS["daily_checkins"])
        return saved

    def get_daily_checkin(self, user_id: str, date: str) -> DailyCheckin | None:
        return self.repository.get_model("daily_checkins", DailyCheckin, {"user_id": user_id, "date": date})

    def list_daily_checkins(self, user_id: str) -> list[DailyCheckin] | None:
        if user_id != DEMO_USER_ID:
            return None
        return self.repository.list_models("daily_checkins", DailyCheckin, {"user_id": user_id})

    def save_agent_message(self, message: AgentMessage) -> AgentMessage:
        self.repository.upsert_model("agent_messages", message, id_field=COLLECTION_IDS["agent_messages"])
        return message

    def list_agent_messages(self, user_id: str) -> list[AgentMessage] | None:
        if user_id != DEMO_USER_ID:
            return None
        return self.repository.list_models("agent_messages", AgentMessage, {"user_id": user_id})

    def save_user_memory_summary(self, summary: UserMemorySummary) -> UserMemorySummary:
        self.repository.upsert_model(
            "user_memory_summaries",
            summary,
            id_field=COLLECTION_IDS["user_memory_summaries"]
        )
        return summary

    def list_user_memory_summaries(self, user_id: str) -> list[UserMemorySummary] | None:
        if user_id != DEMO_USER_ID:
            return None
        return self.repository.list_models("user_memory_summaries", UserMemorySummary, {"user_id": user_id})

    def build_today_response(self, user_id: str, date: str) -> TodayResponseData | None:
        if user_id != DEMO_USER_ID:
            return None
        today = create_today_response(date)
        plan = self.get_current_plan(user_id)
        if plan is not None:
            today.user.goal = plan.goal
            today.today_workout = next((day for day in plan.workout_plan.days if day.date == date), None)
            today.today_meals = next((day.meals for day in plan.meal_plan.days if day.date == date), [])
            today.status_summary.calories_target = plan.meal_plan.daily_targets.calories
            today.status_summary.protein_target_g = plan.meal_plan.daily_targets.protein_g
        meal_logs = [log for log in self.list_meal_logs(user_id) if log.date == date]
        workout_logs = self.list_workout_logs(user_id)
        checkin = self.get_daily_checkin(user_id, date)
        calories_logged = sum(log.calories for log in meal_logs)
        protein_logged = sum(log.protein_g for log in meal_logs)
        completed_workouts = len([
            log for log in workout_logs if log.status in ("completed", "partially_completed")
        ])
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
