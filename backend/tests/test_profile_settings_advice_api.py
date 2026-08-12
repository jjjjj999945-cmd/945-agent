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


def test_profile_requires_safety_confirmation_before_it_is_complete():
    response = client.patch("/api/profile/demo-user-945", json={"safety_confirmed": False})

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["profile_completion"] == "incomplete"
    assert "safety_confirmed" in data["missing_fields"]


def test_profile_returns_complete_after_required_fields_and_safety_confirmation():
    response = client.patch("/api/profile/demo-user-945", json={"safety_confirmed": True})

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["profile_completion"] == "complete"
    assert data["safety_confirmed_at"] is not None


def test_profile_clears_safety_confirmation_timestamp_when_confirmation_is_revoked():
    confirmed = client.patch("/api/profile/demo-user-945", json={"safety_confirmed": True})
    assert confirmed.json()["data"]["safety_confirmed_at"] is not None

    revoked = client.patch("/api/profile/demo-user-945", json={"safety_confirmed": False})

    assert revoked.status_code == 200
    assert revoked.json()["data"]["safety_confirmed_at"] is None


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


def test_generate_feedback_creates_recovery_advice_and_plan_adjustment_for_high_fatigue():
    checkin = client.post(
        "/api/daily-checkins",
        json={"user_id": "demo-user-945", "date": "2026-07-11", "fatigue_level": 4, "sleep_hours": 6.5},
    )
    assert checkin.status_code == 200

    generated = client.post("/api/advice/generate", json={"user_id": "demo-user-945", "date": "2026-07-11"})
    assert generated.status_code == 200
    items = generated.json()["data"]
    assert items[0]["type"] == "daily_advice"
    assert items[0]["risk_level"] == "medium"
    assert items[2]["type"] == "plan_adjustment"
    assert "草稿" in items[2]["content"]

    advice = client.get("/api/advice").json()["data"]
    assert advice["daily"]["advice_id"] == "advice-daily-2026-07-11"
    assert advice["adjustments"][0]["advice_id"] == "advice-adjustment-2026-07-11"


def test_generate_feedback_flags_low_protein_when_recovery_signals_are_normal():
    generated = client.post("/api/advice/generate", json={"user_id": "demo-user-945", "date": "2026-07-11"})

    assert generated.status_code == 200
    daily = generated.json()["data"][0]
    assert daily["type"] == "daily_advice"
    assert "蛋白质" in daily["title"]
    assert daily["risk_level"] == "low"


def test_export_returns_user_owned_structured_data():
    response = client.get("/api/settings/export", params={"user_id": "demo-user-945"})

    assert response.status_code == 200
    exported = response.json()["data"]
    assert exported["schema_version"] == "1.0"
    assert exported["exported_at"]
    assert exported["user"]["user_id"] == "demo-user-945"
    assert exported["profile"]["user_id"] == "demo-user-945"
    assert isinstance(exported["plans"], list)
    assert "agent_messages" in exported


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
