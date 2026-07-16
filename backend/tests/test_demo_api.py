from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def test_get_demo_user_returns_local_demo_user():
    response = client.get("/api/demo-user")

    assert response.status_code == 200
    assert response.json() == {
        "data": {
            "user_id": "demo-user-945",
            "display_name": "Alex",
            "locale": "zh-CN",
            "unit_system": "metric",
            "created_at": "2026-07-11T00:00:00.000Z",
            "updated_at": "2026-07-11T00:00:00.000Z"
        },
        "error": None
    }


def test_get_today_returns_demo_aggregate_with_default_query():
    response = client.get("/api/today")

    assert response.status_code == 200
    body = response.json()
    assert body["error"] is None
    assert body["data"]["date"] == "2026-07-11"
    assert body["data"]["user"] == {
        "user_id": "demo-user-945",
        "display_name": "Alex",
        "goal": "body_recomposition"
    }
    assert body["data"]["status_summary"] == {
        "weekly_workouts_completed": 3,
        "weekly_workouts_planned": 4,
        "calories_target": 2300,
        "calories_logged": 1480,
        "protein_target_g": 160,
        "protein_logged_g": 102,
        "weight_7_day_delta_kg": -0.4,
        "recovery_status": "normal"
    }
    assert body["data"]["today_workout"]["name"] == "上肢力量"
    assert body["data"]["today_workout"]["exercises"][0]["name"] == "哑铃卧推"
    assert [meal["meal_id"] for meal in body["data"]["today_meals"]] == [
        "meal-breakfast-1",
        "meal-lunch-1",
        "meal-dinner-1"
    ]
    assert body["data"]["daily_checkin"] is None
    assert body["data"]["latest_advice"]["advice_id"] == "advice-2026-07-11-1"


def test_get_today_accepts_explicit_demo_user_and_date():
    response = client.get("/api/today", params={"user_id": "demo-user-945", "date": "2026-07-11"})

    assert response.status_code == 200
    assert response.json()["data"]["date"] == "2026-07-11"


def test_get_today_rejects_unknown_user():
    response = client.get("/api/today", params={"user_id": "missing-user", "date": "2026-07-11"})

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
