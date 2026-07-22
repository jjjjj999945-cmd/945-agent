from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def test_get_current_plan_returns_active_demo_plan():
    response = client.get("/api/plans/current")

    assert response.status_code == 200
    body = response.json()
    assert body["error"] is None
    assert body["data"]["plan_id"] == "plan-2026-07-11-demo"
    assert body["data"]["user_id"] == "demo-user-945"
    assert body["data"]["goal"] == "body_recomposition"
    assert body["data"]["status"] == "active"
    assert body["data"]["start_date"] == "2026-07-11"
    assert body["data"]["end_date"] == "2026-07-17"
    assert body["data"]["generated_by"] == "mock"
    assert body["data"]["workout_plan"]["days"][0]["name"] == "上肢力量"
    assert body["data"]["workout_plan"]["days"][0]["exercises"][0]["exercise_id"] == "ex-db-press"
    assert body["data"]["meal_plan"]["daily_targets"] == {
        "calories": 2300,
        "protein_g": 160,
        "carbs_g": 240,
        "fat_g": 70
    }
    assert body["data"]["meal_plan"]["days"][0]["meals"][0]["meal_id"] == "meal-breakfast-1"


def test_get_current_plan_accepts_explicit_demo_user():
    response = client.get("/api/plans/current", params={"user_id": "demo-user-945"})

    assert response.status_code == 200
    assert response.json()["data"]["plan_id"] == "plan-2026-07-11-demo"


def test_get_current_plan_rejects_unknown_user():
    response = client.get("/api/plans/current", params={"user_id": "missing-user"})

    assert response.status_code == 404
    assert response.json() == {
        "data": None,
        "error": {
            "code": "NOT_FOUND",
            "message": "Demo user not found.",
            "details": {
                "user_id": "missing-user"
            }
        }
    }


def test_generate_and_accept_plan_replaces_active_plan():
    generated = client.post("/api/plans/generate", json={"user_id": "demo-user-945", "goal": "muscle_gain"})

    assert generated.status_code == 200
    draft = generated.json()["data"]
    assert draft["status"] == "draft"
    assert draft["goal"] == "muscle_gain"

    active_before = client.get("/api/plans/current").json()["data"]
    assert active_before["plan_id"] != draft["plan_id"]

    accepted = client.post(f"/api/plans/{draft['plan_id']}/accept", json={"user_id": "demo-user-945"})
    assert accepted.status_code == 200
    assert accepted.json()["data"]["status"] == "active"
    assert client.get("/api/plans/current").json()["data"]["plan_id"] == draft["plan_id"]


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


def test_confirmed_plan_adjustment_creates_new_active_plan():
    original = client.get("/api/plans/current").json()["data"]
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
    plan = client.get("/api/plans/current").json()["data"]
    response = client.post(
        f"/api/plans/{plan['plan_id']}/adjust",
        json={"user_id": "demo-user-945", "adjustment_type": "reduce_intensity", "reason": "疲劳较高", "confirmed": False},
    )

    assert response.status_code == 422
    assert client.get("/api/plans/current").json()["data"]["plan_id"] == plan["plan_id"]
