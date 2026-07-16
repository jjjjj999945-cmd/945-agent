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
