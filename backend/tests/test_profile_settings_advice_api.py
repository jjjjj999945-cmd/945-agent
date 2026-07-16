from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def test_get_and_patch_profile_for_demo_user():
    get_response = client.get("/api/profile/demo-user-945")

    assert get_response.status_code == 200
    profile = get_response.json()["data"]
    assert profile["profile_id"] == "profile-demo-user-945"
    assert profile["goal"] == "body_recomposition"

    patch_response = client.patch(
        "/api/profile/demo-user-945",
        json={
            "weight_kg": 75.2,
            "goal": "fat_loss",
            "training_days_per_week": 5,
            "constraints": ["busy_weekdays", "travel"]
        }
    )

    assert patch_response.status_code == 200
    updated = patch_response.json()["data"]
    assert updated["profile_id"] == "profile-demo-user-945"
    assert updated["weight_kg"] == 75.2
    assert updated["goal"] == "fat_loss"
    assert updated["training_days_per_week"] == 5
    assert updated["constraints"] == ["busy_weekdays", "travel"]
    assert updated["updated_at"]


def test_post_profile_overwrites_demo_profile():
    response = client.post(
        "/api/profile",
        json={
            "user_id": "demo-user-945",
            "display_name": "Alex",
            "age": 30,
            "gender": "optional",
            "height_cm": 176,
            "weight_kg": 74.8,
            "goal": "maintenance",
            "experience_level": "intermediate",
            "training_days_per_week": 3,
            "training_duration_minutes": 45,
            "equipment": ["gym"],
            "dietary_preferences": ["high_protein"],
            "allergies": [],
            "constraints": ["busy_weekdays"],
            "locale": "zh-CN",
            "unit_system": "metric"
        }
    )

    assert response.status_code == 200
    body = response.json()
    assert body["error"] is None
    assert body["data"]["user_id"] == "demo-user-945"
    assert body["data"]["goal"] == "maintenance"
    assert body["data"]["height_cm"] == 176


def test_settings_get_and_patch_updates_user_locale_and_units():
    get_response = client.get("/api/settings", params={"user_id": "demo-user-945"})

    assert get_response.status_code == 200
    settings = get_response.json()["data"]
    assert settings["language"] == "zh-CN"
    assert settings["unit_system"] == "metric"
    assert settings["user"]["display_name"] == "Alex"

    patch_response = client.patch(
        "/api/settings",
        json={
            "user_id": "demo-user-945",
            "language": "en-US",
            "unit_system": "imperial"
        }
    )

    assert patch_response.status_code == 200
    updated = patch_response.json()["data"]
    assert updated["language"] == "en-US"
    assert updated["unit_system"] == "imperial"
    assert updated["user"]["locale"] == "en-US"
    assert updated["user"]["unit_system"] == "imperial"


def test_get_advice_and_update_advice_status():
    get_response = client.get("/api/advice", params={"user_id": "demo-user-945"})

    assert get_response.status_code == 200
    advice = get_response.json()["data"]
    assert advice["daily"]["advice_id"] == "advice-2026-07-11-1"
    assert advice["weekly"]["advice_id"] == "advice-weekly-001"
    assert advice["adjustments"] == []

    patch_response = client.patch(
        "/api/advice/advice-2026-07-11-1/status",
        json={
            "user_id": "demo-user-945",
            "accepted_status": "accepted"
        }
    )

    assert patch_response.status_code == 200
    updated = patch_response.json()["data"]
    assert updated["advice_id"] == "advice-2026-07-11-1"
    assert updated["accepted_status"] == "accepted"


def test_update_advice_status_rejects_missing_advice():
    response = client.patch(
        "/api/advice/missing-advice/status",
        json={
            "user_id": "demo-user-945",
            "accepted_status": "dismissed"
        }
    )

    assert response.status_code == 404
    assert response.json() == {
        "data": None,
        "error": {
            "code": "NOT_FOUND",
            "message": "Advice not found.",
            "details": {
                "user_id": "demo-user-945",
                "advice_id": "missing-advice"
            }
        }
    }


def test_profile_rejects_unknown_user():
    response = client.get("/api/profile/missing-user")

    assert response.status_code == 404
    assert response.json() == {
        "data": None,
        "error": {
            "code": "NOT_FOUND",
            "message": "Demo user not found.",
            "details": {"user_id": "missing-user"}
        }
    }
