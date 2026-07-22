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
