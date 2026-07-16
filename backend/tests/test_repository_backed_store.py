from backend.app.data.demo_data import DEMO_USER_ID, TODAY_DATE
from backend.app.models.domain import (
    ConfirmPlannedMealInput,
    DailyCheckinInput,
    ManualMealLogInput,
    WorkoutLogInput,
)
from backend.app.repositories.mongo import MongoRepository
from backend.app.services.repository_store import RepositoryBackedStore
from backend.tests.test_mongo_repository import FakeDatabase


def create_store() -> RepositoryBackedStore:
    store = RepositoryBackedStore(MongoRepository(FakeDatabase()))
    store.seed_demo_data()
    return store


def test_repository_store_seeds_demo_data_once():
    store = create_store()
    store.seed_demo_data()

    assert store.get_current_user().user_id == DEMO_USER_ID
    assert store.get_profile(DEMO_USER_ID).goal == "body_recomposition"
    assert store.get_current_plan(DEMO_USER_ID).plan_id == "plan-2026-07-11-demo"
    assert store.get_advice(DEMO_USER_ID).daily.advice_id == "advice-2026-07-11-1"


def test_repository_store_persists_workout_and_meal_logs():
    store = create_store()

    workout = store.create_workout_log(
        WorkoutLogInput(
            user_id=DEMO_USER_ID,
            plan_id="plan-2026-07-11-demo",
            date=TODAY_DATE,
            status="completed",
            exercises=[{"name": "深蹲", "sets": [{"reps": 8, "weight_kg": 80}]}]
        )
    )
    planned_meal = store.confirm_planned_meal(
        ConfirmPlannedMealInput(
            user_id=DEMO_USER_ID,
            plan_id="plan-2026-07-11-demo",
            date=TODAY_DATE,
            meal_id="meal-breakfast-1"
        )
    )
    manual_meal = store.create_manual_meal_log(
        ManualMealLogInput(
            user_id=DEMO_USER_ID,
            date=TODAY_DATE,
            meal_name="加餐",
            foods=[{"name": "香蕉", "portion": "1 根", "calories": 100, "protein_g": 1, "carbs_g": 27, "fat_g": 0}]
        )
    )

    assert workout.workout_log_id.startswith("workout-2026-07-11-")
    assert planned_meal.meal_name == "早餐"
    assert manual_meal.calories == 100
    assert len(store.list_workout_logs(DEMO_USER_ID)) == 1
    assert len(store.list_meal_logs(DEMO_USER_ID)) == 2


def test_repository_store_builds_today_from_persisted_records():
    store = create_store()
    store.create_workout_log(
        WorkoutLogInput(
            user_id=DEMO_USER_ID,
            date=TODAY_DATE,
            status="completed",
            exercises=[{"name": "深蹲", "sets": [{"reps": 8}]}]
        )
    )
    store.create_manual_meal_log(
        ManualMealLogInput(
            user_id=DEMO_USER_ID,
            date=TODAY_DATE,
            meal_name="训练后餐",
            foods=[
                {
                    "name": "训练后餐",
                    "portion": "1 份",
                    "calories": 1800,
                    "protein_g": 130,
                    "carbs_g": 220,
                    "fat_g": 45
                }
            ]
        )
    )
    store.save_daily_checkin(
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

    today = store.build_today_response(DEMO_USER_ID, TODAY_DATE)

    assert today.status_summary.weekly_workouts_completed >= 4
    assert today.status_summary.calories_logged >= 1800
    assert today.daily_checkin.fatigue_level == 4
    assert today.status_summary.recovery_status == "fatigued"
