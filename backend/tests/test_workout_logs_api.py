from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def test_create_workout_log_returns_saved_log():
    response = client.post(
        "/api/workout-logs",
        json={
            "user_id": "demo-user-945",
            "plan_id": "plan-2026-07-11-demo",
            "date": "2026-07-11",
            "status": "completed",
            "duration_minutes": 58,
            "rpe": 8,
            "exercises": [
                {
                    "exercise_id": "ex-db-press",
                    "name": "哑铃卧推",
                    "sets": [
                        {"reps": 10, "weight_kg": 28, "completed": True},
                        {"reps": 9, "weight_kg": 28, "completed": True}
                    ]
                }
            ],
            "notes": "最后两组比较吃力。"
        }
    )

    assert response.status_code == 200
    body = response.json()
    assert body["error"] is None
    assert body["data"]["workout_log_id"].startswith("workout-2026-07-11-")
    assert body["data"]["user_id"] == "demo-user-945"
    assert body["data"]["plan_id"] == "plan-2026-07-11-demo"
    assert body["data"]["status"] == "completed"
    assert body["data"]["duration_minutes"] == 58
    assert body["data"]["rpe"] == 8
    assert body["data"]["exercises"][0]["name"] == "哑铃卧推"
    assert body["data"]["exercises"][0]["sets"][0] == {
        "reps": 10,
        "weight_kg": 28.0,
        "completed": True
    }
    assert body["data"]["created_at"]
    assert body["data"]["updated_at"]


def test_list_workout_logs_returns_saved_logs_for_user():
    client.post(
        "/api/workout-logs",
        json={
            "user_id": "demo-user-945",
            "date": "2026-07-11",
            "status": "completed",
            "exercises": [{"name": "深蹲", "sets": [{"reps": 8, "weight_kg": 80}]}]
        }
    )

    response = client.get("/api/workout-logs", params={"user_id": "demo-user-945"})

    assert response.status_code == 200
    body = response.json()
    assert body["error"] is None
    assert any(log["exercises"][0]["name"] == "深蹲" for log in body["data"])


def test_create_workout_log_rejects_unknown_user():
    response = client.post(
        "/api/workout-logs",
        json={
            "user_id": "missing-user",
            "date": "2026-07-11",
            "status": "completed",
            "exercises": [{"name": "深蹲", "sets": [{"reps": 8}]}]
        }
    )

    assert response.status_code == 404
    assert response.json() == {
        "data": None,
        "error": {
            "code": "NOT_FOUND",
            "message": "Demo user not found.",
            "details": {"user_id": "missing-user"}
        }
    }
