from copy import deepcopy
from typing import Any

from backend.app.core.config import get_settings
from backend.app.data.demo_data import DEMO_ADVICE, DEMO_PLAN, DEMO_USER, DEMO_USER_ID, NOW, create_today_response
from backend.app.models.domain import (
    AdvicePageData,
    AuthCredential,
    AdviceStatus,
    AgentAdvice,
    AgentMessage,
    AgentRun,
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
from backend.app.repositories.mongo import MongoRepository, model_to_mongo_document
from backend.app.services.agent_run_lease import AgentLeaseToken
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
    "agent_runs": "agent_run_id",
    "user_memory_summaries": "summary_id",
    "auth_credentials": "email",
}


def _lease_filter(token: AgentLeaseToken) -> dict[str, Any]:
    return {
        "_id": token.agent_run_id,
        "user_id": token.user_id,
        "status": "running",
        "lease_owner": token.owner,
        "lease_version": token.version,
        "$expr": {"$gt": ["$lease_expires_at", "$$NOW"]},
    }


def _lease_expiration_expression() -> dict[str, Any]:
    return {
        "$dateAdd": {
            "startDate": "$$NOW",
            "unit": "second",
            "amount": get_settings().agent_lease_ttl_seconds,
        }
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
        return self.get_user(user_id) is not None

    def get_user(self, user_id: str) -> User | None:
        return self.repository.get_model("users", User, {"user_id": user_id})

    def get_current_user(self) -> User:
        user = self.get_user(DEMO_USER_ID)
        if user is None:
            self.seed_demo_data()
            user = self.repository.get_model("users", User, {"user_id": DEMO_USER_ID})
        return user

    def save_registered_user(self, user: User, credential: AuthCredential) -> None:
        self.repository.upsert_model("users", user, id_field=COLLECTION_IDS["users"])
        self.repository.upsert_model("auth_credentials", credential, id_field=COLLECTION_IDS["auth_credentials"])
        profile = deepcopy(INITIAL_PROFILE).model_copy(update={
            "profile_id": f"profile-{user.user_id}",
            "user_id": user.user_id,
            "safety_confirmed": False,
            "safety_confirmed_at": None,
            "updated_at": user.updated_at,
        })
        self.repository.upsert_model("user_profiles", profile, id_field=COLLECTION_IDS["user_profiles"])

    def get_credential(self, email: str) -> AuthCredential | None:
        return self.repository.get_model("auth_credentials", AuthCredential, {"email": email})

    def save_credential(self, credential: AuthCredential) -> None:
        self.repository.upsert_model("auth_credentials", credential, id_field=COLLECTION_IDS["auth_credentials"])

    def get_profile(self, user_id: str) -> UserProfile | None:
        return self.repository.get_model("user_profiles", UserProfile, {"user_id": user_id})

    def save_profile(self, input_data: ProfileCreateInput) -> UserProfile | None:
        now = timestamp()
        existing_user = self.get_user(input_data.user_id)
        if existing_user is None:
            return None
        user = User(
            user_id=input_data.user_id,
            display_name=input_data.display_name,
            locale=input_data.locale,
            unit_system=input_data.unit_system,
            created_at=existing_user.created_at,
            updated_at=now
        )
        profile = UserProfile(
            profile_id=f"profile-{input_data.user_id}",
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
            safety_confirmed=input_data.safety_confirmed,
            safety_confirmed_at=now if input_data.safety_confirmed else None,
            updated_at=now
        )
        self.repository.upsert_model("users", user, id_field=COLLECTION_IDS["users"])
        self.repository.upsert_model("user_profiles", profile, id_field=COLLECTION_IDS["user_profiles"])
        return profile

    def update_profile(self, user_id: str, input_data: ProfilePatchInput) -> UserProfile | None:
        profile = self.get_profile(user_id)
        if profile is None:
            return None
        now = timestamp()
        updates = input_data.model_dump(exclude_unset=True)
        if "safety_confirmed" in updates:
            updates["safety_confirmed_at"] = now if updates["safety_confirmed"] else None
        updated = profile.model_copy(update={**updates, "updated_at": now})
        self.repository.upsert_model("user_profiles", updated, id_field=COLLECTION_IDS["user_profiles"])
        return updated

    def get_settings(self, user_id: str) -> SettingsData | None:
        profile = self.get_profile(user_id)
        if profile is None:
            return None
        user = self.get_user(user_id)
        if user is None:
            return None
        return SettingsData(user=user, profile=profile, language=user.locale, unit_system=user.unit_system)

    def update_settings(self, input_data: SettingsPatchInput) -> SettingsData | None:
        user = self.get_user(input_data.user_id)
        if user is None:
            return None
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
        return self.repository.get_model("plans", Plan, {"user_id": user_id, "status": "active"})

    def save_plan(self, plan: Plan) -> Plan | None:
        if self.get_user(plan.user_id) is None:
            return None
        self.repository.upsert_model("plans", plan, id_field=COLLECTION_IDS["plans"])
        return plan

    def list_plans(self, user_id: str) -> list[Plan] | None:
        if self.get_user(user_id) is None:
            return None
        return self.repository.list_models("plans", Plan, {"user_id": user_id})

    def get_advice(self, user_id: str) -> AdvicePageData | None:
        if self.get_user(user_id) is None:
            return None
        advice = sorted(
            self.repository.list_models("agent_advice", AgentAdvice, {"user_id": user_id}),
            key=lambda item: item.created_at,
            reverse=True,
        )
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
        if self.get_user(user_id) is None:
            return None
        advice = self.repository.get_model("agent_advice", AgentAdvice, {"advice_id": advice_id, "user_id": user_id})
        if advice is None:
            return None
        updated = advice.model_copy(update={"accepted_status": accepted_status})
        self.repository.upsert_model("agent_advice", updated, id_field=COLLECTION_IDS["agent_advice"])
        return updated

    def save_advice(self, advice: AgentAdvice) -> AgentAdvice | None:
        if self.get_user(advice.user_id) is None:
            return None
        self.repository.upsert_model("agent_advice", advice, id_field=COLLECTION_IDS["agent_advice"])
        return advice

    def create_workout_log(self, input_data: WorkoutLogInput) -> WorkoutLog | None:
        if self.get_user(input_data.user_id) is None:
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
        if self.get_user(user_id) is None:
            return None
        return self.repository.list_models("workout_logs", WorkoutLog, {"user_id": user_id})

    def confirm_planned_meal(self, input_data: ConfirmPlannedMealInput) -> MealLog | None:
        if self.get_user(input_data.user_id) is None:
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
        if self.get_user(input_data.user_id) is None:
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
        if self.get_user(user_id) is None:
            return None
        return self.repository.list_models("meal_logs", MealLog, {"user_id": user_id})

    def save_body_metric(self, input_data: BodyMetricInput) -> BodyMetric | None:
        if self.get_user(input_data.user_id) is None:
            return None
        saved = BodyMetric(
            **input_data.model_dump(),
            metric_id=f"metric-{input_data.date}-{len(self.list_body_metrics(input_data.user_id)) + 1}",
            created_at=timestamp()
        )
        self.repository.upsert_model("body_metrics", saved, id_field=COLLECTION_IDS["body_metrics"])
        return saved

    def list_body_metrics(self, user_id: str) -> list[BodyMetric] | None:
        if self.get_user(user_id) is None:
            return None
        return sorted(
            self.repository.list_models("body_metrics", BodyMetric, {"user_id": user_id}),
            key=lambda metric: metric.date
        )

    def save_daily_checkin(self, input_data: DailyCheckinInput) -> DailyCheckin | None:
        if self.get_user(input_data.user_id) is None:
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
        if self.get_user(user_id) is None:
            return None
        return self.repository.list_models("daily_checkins", DailyCheckin, {"user_id": user_id})

    def save_agent_message(self, message: AgentMessage) -> AgentMessage:
        self.repository.upsert_model("agent_messages", message, id_field=COLLECTION_IDS["agent_messages"])
        return message

    def list_agent_messages(self, user_id: str) -> list[AgentMessage] | None:
        if self.get_user(user_id) is None:
            return None
        return self.repository.list_models("agent_messages", AgentMessage, {"user_id": user_id})

    def save_agent_run(self, run: AgentRun) -> AgentRun:
        self.repository.upsert_model("agent_runs", run, id_field=COLLECTION_IDS["agent_runs"])
        return run

    def create_agent_run_with_lease(
        self,
        run: AgentRun,
        owner: str,
    ) -> AgentRun | None:
        leased = run.model_copy(
            update={
                "status": "running",
                "lease_owner": owner,
                "lease_version": 1,
                "lease_expires_at": None,
                "last_heartbeat_at": None,
            }
        )
        document = model_to_mongo_document(
            leased,
            id_field=COLLECTION_IDS["agent_runs"],
        )
        return self.repository.find_one_and_update_model(
            "agent_runs",
            AgentRun,
            {
                "_id": run.agent_run_id,
                "agent_run_id": {"$exists": False},
            },
            [
                {
                    "$replaceWith": {
                        "$mergeObjects": [
                            {"$literal": document},
                            {
                                "last_heartbeat_at": "$$NOW",
                                "lease_expires_at": _lease_expiration_expression(),
                            },
                        ]
                    }
                }
            ],
            upsert=True,
        )

    def acquire_agent_run_lease(
        self,
        user_id: str,
        agent_run_id: str,
        owner: str,
    ) -> AgentRun | None:
        return self.repository.find_one_and_update_model(
            "agent_runs",
            AgentRun,
            {
                "_id": agent_run_id,
                "user_id": user_id,
                "status": "interrupted",
            },
            [
                {
                    "$set": {
                        "status": "running",
                        "lease_owner": owner,
                        "lease_version": {
                            "$add": [{"$ifNull": ["$lease_version", 0]}, 1]
                        },
                        "last_heartbeat_at": "$$NOW",
                        "lease_expires_at": _lease_expiration_expression(),
                        "resume_count": {
                            "$add": [{"$ifNull": ["$resume_count", 0]}, 1]
                        },
                        "completed_at": None,
                        "error_code": None,
                    }
                }
            ],
        )

    def renew_agent_run_lease(
        self,
        token: AgentLeaseToken,
    ) -> AgentRun | None:
        return self.repository.find_one_and_update_model(
            "agent_runs",
            AgentRun,
            _lease_filter(token),
            [
                {
                    "$set": {
                        "last_heartbeat_at": "$$NOW",
                        "lease_expires_at": _lease_expiration_expression(),
                    }
                }
            ],
        )

    def agent_run_lease_is_valid(self, token: AgentLeaseToken) -> bool:
        return (
            self.repository.get_model(
                "agent_runs",
                AgentRun,
                _lease_filter(token),
            )
            is not None
        )

    def interrupt_expired_agent_runs(self, user_id: str) -> int:
        interrupted = 0
        while True:
            run = self.repository.find_one_and_update_model(
                "agent_runs",
                AgentRun,
                {
                    "user_id": user_id,
                    "status": "running",
                    "$or": [
                        {"lease_expires_at": {"$exists": False}},
                        {"lease_expires_at": None},
                        {"$expr": {"$lte": ["$lease_expires_at", "$$NOW"]}},
                    ],
                },
                {
                    "$set": {
                        "status": "interrupted",
                        "lease_owner": None,
                        "lease_expires_at": None,
                    }
                },
            )
            if run is None:
                return interrupted
            interrupted += 1

    def set_agent_run_resume_checkpoint(
        self,
        token: AgentLeaseToken,
        checkpoint_id: str,
    ) -> AgentRun | None:
        return self.repository.find_one_and_update_model(
            "agent_runs",
            AgentRun,
            _lease_filter(token),
            {"$set": {"resume_checkpoint_id": checkpoint_id}},
        )

    def transition_agent_run_with_lease(
        self,
        token: AgentLeaseToken,
        updated_run: AgentRun,
    ) -> AgentRun | None:
        if updated_run.status not in {"completed", "failed", "interrupted"}:
            return None
        if (
            updated_run.user_id != token.user_id
            or updated_run.agent_run_id != token.agent_run_id
        ):
            return None

        update_fields = updated_run.model_dump(exclude_computed_fields=True)
        update_fields.pop("last_heartbeat_at", None)
        update_fields.pop("resume_checkpoint_id", None)
        update_fields.update(
            {
                "lease_owner": None,
                "lease_version": token.version,
                "lease_expires_at": None,
            }
        )
        return self.repository.find_one_and_update_model(
            "agent_runs",
            AgentRun,
            _lease_filter(token),
            {"$set": update_fields},
        )

    def mark_agent_run_messages_persisted(
        self,
        user_id: str,
        agent_run_id: str,
        lease_version: int,
    ) -> bool:
        return self.repository.update_one(
            "agent_runs",
            {
                "_id": agent_run_id,
                "user_id": user_id,
                "status": "completed",
                "lease_version": lease_version,
            },
            {"$set": {"messages_persisted": True}},
        )

    def list_agent_runs(self, user_id: str) -> list[AgentRun] | None:
        if self.get_user(user_id) is None:
            return None
        return self.repository.list_models("agent_runs", AgentRun, {"user_id": user_id})

    def save_user_memory_summary(self, summary: UserMemorySummary) -> UserMemorySummary:
        self.repository.upsert_model(
            "user_memory_summaries",
            summary,
            id_field=COLLECTION_IDS["user_memory_summaries"]
        )
        return summary

    def list_user_memory_summaries(self, user_id: str) -> list[UserMemorySummary] | None:
        if self.get_user(user_id) is None:
            return None
        return self.repository.list_models("user_memory_summaries", UserMemorySummary, {"user_id": user_id})

    def build_today_response(self, user_id: str, date: str) -> TodayResponseData | None:
        user = self.get_user(user_id)
        if user is None:
            return None
        today = create_today_response(date)
        today.user.user_id = user.user_id
        today.user.display_name = user.display_name
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
