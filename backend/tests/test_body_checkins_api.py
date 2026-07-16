from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def test_save_body_metric_and_list_metrics_for_user():
    response = client.post(
        "/api/body-metrics",
        json={
            "user_id": "demo-user-945",
            "date": "2026-07-12",
            "weight_kg": 75.4,
            "body_fat_percentage": 18.4,
            "waist_cm": 82.5,
            "notes": "早晨空腹"
        }
    )

    assert response.status_code == 200
    body = response.json()
    assert body["error"] is None
    assert body["data"]["metric_id"].startswith("metric-2026-07-12-")
    assert body["data"]["weight_kg"] == 75.4
    assert body["data"]["body_fat_percentage"] == 18.4
    assert body["data"]["waist_cm"] == 82.5
    assert body["data"]["created_at"]

    list_response = client.get("/api/body-metrics", params={"user_id": "demo-user-945"})
    assert list_response.status_code == 200
    assert any(metric["date"] == "2026-07-12" for metric in list_response.json()["data"])


def test_save_daily_checkin_upserts_by_user_and_date():
    first_response = client.post(
        "/api/daily-checkins",
        json={
            "user_id": "demo-user-945",
            "date": "2026-07-11",
            "sleep_hours": 7.5,
            "sleep_quality": 4,
            "fatigue_level": 3,
            "soreness_level": 2,
            "stress_level": 3,
            "mood": "normal",
            "notes": "今天状态还可以。"
        }
    )
    second_response = client.post(
        "/api/daily-checkins",
        json={
            "user_id": "demo-user-945",
            "date": "2026-07-11",
            "sleep_hours": 6.5,
            "sleep_quality": 3,
            "fatigue_level": 4,
            "soreness_level": 3,
            "stress_level": 4,
            "mood": "low",
            "notes": "下午有些疲劳。"
        }
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    first = first_response.json()["data"]
    second = second_response.json()["data"]
    assert second["checkin_id"] == first["checkin_id"]
    assert second["sleep_hours"] == 6.5
    assert second["fatigue_level"] == 4
    assert second["updated_at"] != first["updated_at"]


def test_today_aggregate_reflects_saved_logs_and_checkin():
    client.post(
        "/api/workout-logs",
        json={
            "user_id": "demo-user-945",
            "date": "2026-07-11",
            "status": "completed",
            "exercises": [{"name": "深蹲", "sets": [{"reps": 8, "weight_kg": 80}]}]
        }
    )
    client.post(
        "/api/meal-logs",
        json={
            "user_id": "demo-user-945",
            "date": "2026-07-11",
            "meal_name": "大餐",
            "foods": [
                {
                    "name": "训练后餐",
                    "portion": "1 份",
                    "calories": 1800,
                    "protein_g": 130,
                    "carbs_g": 220,
                    "fat_g": 45
                }
            ]
        }
    )
    client.post(
        "/api/daily-checkins",
        json={
            "user_id": "demo-user-945",
            "date": "2026-07-11",
            "sleep_hours": 6.5,
            "fatigue_level": 4,
            "soreness_level": 3,
            "stress_level": 4,
            "mood": "low"
        }
    )

    response = client.get("/api/today", params={"user_id": "demo-user-945", "date": "2026-07-11"})

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status_summary"]["weekly_workouts_completed"] >= 4
    assert data["status_summary"]["calories_logged"] >= 1800
    assert data["status_summary"]["protein_logged_g"] >= 130
    assert data["daily_checkin"]["fatigue_level"] == 4
    assert data["status_summary"]["recovery_status"] == "fatigued"


def test_body_metric_rejects_unknown_user():
    response = client.post(
        "/api/body-metrics",
        json={
            "user_id": "missing-user",
            "date": "2026-07-11",
            "weight_kg": 75.6
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
