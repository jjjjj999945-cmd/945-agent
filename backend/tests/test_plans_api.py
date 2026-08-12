from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def test_get_current_plan_returns_active_demo_plan():
    response = client.get("/api/plans/current")

    assert response.status_code == 200
    body = response.json()
    assert body["error"] is None
    assert body["data"]["coverage_status"] == "active_today"
    plan = body["data"]["plan"]
    assert plan["plan_id"] == "plan-2026-07-11-demo"
    assert plan["user_id"] == "demo-user-945"
    assert plan["goal"] == "body_recomposition"
    assert plan["status"] == "active"
    assert plan["start_date"] == "2026-07-11"
    assert plan["end_date"] == "2026-07-17"
    assert plan["generated_by"] == "mock"
    assert plan["workout_plan"]["days"][0]["name"] == "上肢力量"
    assert plan["workout_plan"]["days"][0]["exercises"][0]["exercise_id"] == "ex-db-press"
    assert plan["meal_plan"]["daily_targets"] == {
        "calories": 2300,
        "protein_g": 160,
        "carbs_g": 240,
        "fat_g": 70
    }
    assert plan["meal_plan"]["days"][0]["meals"][0]["meal_id"] == "meal-breakfast-1"


def test_get_current_plan_accepts_explicit_demo_user():
    response = client.get("/api/plans/current", params={"user_id": "demo-user-945"})

    assert response.status_code == 200
    assert response.json()["data"]["plan"]["plan_id"] == "plan-2026-07-11-demo"


def test_get_current_plan_rejects_unknown_user():
    response = client.get("/api/plans/current", params={"user_id": "missing-user"})

    assert response.status_code == 404
    assert response.json() == {
        "data": None,
        "error": {
            "code": "NOT_FOUND",
            "message": "No active plan found. Generate and accept a plan first.",
            "details": {
                "user_id": "missing-user"
            }
        }
    }


def test_current_plan_endpoint_returns_expired_state_without_executable_plan(monkeypatch):
    monkeypatch.setenv("945_REFERENCE_DATE", "2026-07-26")

    response = client.get("/api/plans/current?user_id=demo-user-945")

    assert response.json()["data"]["coverage_status"] == "expired"
    assert response.json()["data"]["plan"] is None


def test_generate_and_accept_plan_replaces_active_plan():
    generated = client.post("/api/plans/generate", json={"user_id": "demo-user-945", "goal": "muscle_gain"})

    assert generated.status_code == 200
    draft = generated.json()["data"]
    assert draft["status"] == "draft"
    assert draft["goal"] == "muscle_gain"

    active_before = client.get("/api/plans/current").json()["data"]["plan"]
    assert active_before["plan_id"] != draft["plan_id"]

    accepted = client.post(f"/api/plans/{draft['plan_id']}/accept", json={"user_id": "demo-user-945"})
    assert accepted.status_code == 200
    assert accepted.json()["data"]["status"] == "active"
    assert client.get("/api/plans/current").json()["data"]["plan"]["plan_id"] == draft["plan_id"]


def test_generated_plan_applies_goal_specific_training_and_macro_rules():
    response = client.post("/api/plans/generate", json={"user_id": "demo-user-945", "goal": "muscle_gain"})

    assert response.status_code == 200
    plan = response.json()["data"]
    assert plan["meal_plan"]["daily_targets"] == {"calories": 2600, "protein_g": 170, "carbs_g": 300, "fat_g": 75}
    assert plan["workout_plan"]["days"][0]["exercises"][0]["sets"] == 5
    assert plan["workout_plan"]["days"][0]["exercises"][0]["reps"] == "8-12"


def test_generated_plan_uses_profile_goal_when_request_omits_goal():
    profile = client.patch("/api/profile/demo-user-945", json={"goal": "strength"})
    assert profile.status_code == 200

    response = client.post("/api/plans/generate", json={"user_id": "demo-user-945"})

    assert response.status_code == 200
    plan = response.json()["data"]
    assert plan["goal"] == "strength"
    assert plan["workout_plan"]["days"][0]["exercises"][0]["reps"] == "4-6"


def test_generated_plan_uses_profile_training_frequency_and_duration():
    profile = client.patch(
        "/api/profile/demo-user-945",
        json={"training_days_per_week": 3, "training_duration_minutes": 45},
    )
    assert profile.status_code == 200

    response = client.post("/api/plans/generate", json={"user_id": "demo-user-945"})

    assert response.status_code == 200
    workouts = response.json()["data"]["workout_plan"]["days"]
    assert len(workouts) == 3
    assert all(day["duration_minutes"] == 45 for day in workouts)
    assert all(len(day["exercises"]) <= 2 for day in workouts)


def test_generated_plan_spreads_daily_macros_across_seven_meals_days():
    response = client.post("/api/plans/generate", json={"user_id": "demo-user-945", "goal": "fat_loss"})

    assert response.status_code == 200
    meal_plan = response.json()["data"]["meal_plan"]
    assert len(meal_plan["days"]) == 7
    for day in meal_plan["days"]:
        totals = {key: sum(meal["total_macros"][key] for meal in day["meals"]) for key in meal_plan["daily_targets"]}
        assert totals == meal_plan["daily_targets"]


def test_generated_plan_scales_food_portions_and_food_macros_for_goal_targets():
    fat_loss = client.post("/api/plans/generate", json={"user_id": "demo-user-945", "goal": "fat_loss"}).json()["data"]
    muscle_gain = client.post("/api/plans/generate", json={"user_id": "demo-user-945", "goal": "muscle_gain"}).json()["data"]

    fat_breakfast = fat_loss["meal_plan"]["days"][0]["meals"][0]
    gain_breakfast = muscle_gain["meal_plan"]["days"][0]["meals"][0]
    assert fat_breakfast["foods"][0]["portion"] == "407g"
    assert gain_breakfast["foods"][0]["portion"] == "504g"
    for meal in gain_breakfast, fat_breakfast:
        totals = {key: sum(food[key] for food in meal["foods"]) for key in meal["total_macros"]}
        assert totals == meal["total_macros"]


def test_generated_plan_respects_equipment_dietary_and_schedule_constraints():
    profile = client.patch(
        "/api/profile/demo-user-945",
        json={
            "equipment": ["resistance_bands"],
            "dietary_preferences": ["vegetarian"],
            "allergies": ["dairy", "gluten", "seafood"],
            "constraints": ["busy_weekdays"],
            "training_days_per_week": 4,
            "training_duration_minutes": 60,
        },
    )
    assert profile.status_code == 200

    plan = client.post("/api/plans/generate", json={"user_id": "demo-user-945"}).json()["data"]
    workouts = plan["workout_plan"]["days"]
    assert workouts[0]["exercises"][0]["name"] == "俯卧撑"
    assert all(day["duration_minutes"] <= 45 for day in workouts if day["date"] in {"2026-07-13", "2026-07-15", "2026-07-16"})
    breakfast = plan["meal_plan"]["days"][0]["meals"][0]["foods"]
    dinner = plan["meal_plan"]["days"][0]["meals"][2]["foods"]
    assert {food["name"] for food in breakfast} >= {"无糖豆乳酸奶", "米饭"}
    assert dinner[0]["name"] == "烤豆腐"


def test_confirmed_plan_adjustments_can_skip_workout_swap_exercise_and_swap_meal():
    original = client.get("/api/plans/current").json()["data"]["plan"]
    date = original["workout_plan"]["days"][0]["date"]
    exercise_id = original["workout_plan"]["days"][0]["exercises"][0]["exercise_id"]
    meal_id = original["meal_plan"]["days"][0]["meals"][0]["meal_id"]

    swapped_exercise = client.post(
        f"/api/plans/{original['plan_id']}/adjust",
        json={"user_id": "demo-user-945", "adjustment_type": "swap_exercise", "reason": "肩部不适", "target_date": date, "target_exercise_id": exercise_id, "replacement_name": "地板卧推", "confirmed": True},
    ).json()["data"]
    assert swapped_exercise["workout_plan"]["days"][0]["exercises"][0]["name"] == "地板卧推"

    skipped = client.post(
        f"/api/plans/{swapped_exercise['plan_id']}/adjust",
        json={"user_id": "demo-user-945", "adjustment_type": "skip_workout", "reason": "需要恢复", "target_date": date, "confirmed": True},
    ).json()["data"]
    assert skipped["workout_plan"]["days"][0]["exercises"] == []

    swapped_meal = client.post(
        f"/api/plans/{skipped['plan_id']}/adjust",
        json={"user_id": "demo-user-945", "adjustment_type": "swap_meal", "reason": "食材不足", "target_date": date, "target_meal_id": meal_id, "replacement_name": "火鸡藜麦饭碗", "confirmed": True},
    ).json()["data"]
    meal = swapped_meal["meal_plan"]["days"][0]["meals"][0]
    assert meal["foods"][0]["name"] == "火鸡藜麦饭碗"
    assert meal["foods"][0]["calories"] == meal["total_macros"]["calories"]


def test_confirmed_plan_adjustment_creates_new_active_plan():
    original = client.get("/api/plans/current").json()["data"]["plan"]
    adjusted = client.post(
        f"/api/plans/{original['plan_id']}/adjust",
        json={
            "user_id": "demo-user-945",
            "adjustment_type": "reduce_intensity",
            "reason": "疲劳较高",
            "confirmed": True,
        },
    )

    assert adjusted.status_code == 200
    plan = adjusted.json()["data"]
    assert plan["plan_id"] != original["plan_id"]
    assert plan["status"] == "active"
    assert plan["generated_by"] == "agent"
    assert plan["workout_plan"]["days"][0]["exercises"][0]["sets"] == original["workout_plan"]["days"][0]["exercises"][0]["sets"] - 1


def test_plan_adjustment_requires_explicit_confirmation():
    plan = client.get("/api/plans/current").json()["data"]["plan"]
    response = client.post(
        f"/api/plans/{plan['plan_id']}/adjust",
        json={"user_id": "demo-user-945", "adjustment_type": "reduce_intensity", "reason": "疲劳较高", "confirmed": False},
    )

    assert response.status_code == 422
    assert client.get("/api/plans/current").json()["data"]["plan"]["plan_id"] == plan["plan_id"]
