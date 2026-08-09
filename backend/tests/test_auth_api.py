from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def register_session(email: str) -> dict:
    response = client.post(
        "/api/auth/register",
        json={"display_name": email.split("@")[0], "email": email, "password": "secure-pass-945"},
    )
    assert response.status_code == 200
    return response.json()["data"]


def test_registration_requires_mongo_storage():
    response = client.post(
        "/api/auth/register",
        json={"display_name": "User", "email": "user@example.com", "password": "secure-pass-945"},
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "STORAGE_CONFIG_ERROR"


def test_mongo_registration_creates_revocable_session(mongo_store):
    session = register_session("user@example.com")
    headers = {"Authorization": f"Bearer {session['access_token']}"}
    assert client.get("/api/auth/me", headers=headers).status_code == 200
    assert client.post("/api/auth/logout", headers=headers).status_code == 200
    assert client.get("/api/auth/me", headers=headers).status_code == 401


def test_mongo_user_can_login_and_change_password(mongo_store):
    client.post(
        "/api/auth/register",
        json={"display_name": "Password User", "email": "password@example.com", "password": "secure-pass-945"},
    )
    login = client.post(
        "/api/auth/login",
        json={"email": "password@example.com", "password": "secure-pass-945"},
    )

    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['data']['access_token']}"}
    changed = client.post(
        "/api/auth/change-password",
        headers=headers,
        json={"current_password": "secure-pass-945", "new_password": "new-secure-pass-945"},
    )

    assert changed.status_code == 200
    assert client.get("/api/auth/me", headers=headers).status_code == 401
    assert client.post("/api/auth/login", json={"email": "password@example.com", "password": "secure-pass-945"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": "password@example.com", "password": "new-secure-pass-945"}).status_code == 200


def test_authenticated_user_cannot_read_or_write_another_users_data(mongo_store):
    alice = register_session("alice@example.com")
    bob = register_session("bob@example.com")
    alice_id = alice["user"]["user_id"]
    bob_headers = {"Authorization": f"Bearer {bob['access_token']}"}
    profile = {
        "user_id": alice_id,
        "display_name": "Alice",
        "age": 30,
        "height_cm": 176,
        "weight_kg": 74.8,
        "goal": "maintenance",
        "experience_level": "intermediate",
        "training_days_per_week": 3,
        "training_duration_minutes": 45,
        "equipment": ["gym"],
        "dietary_preferences": ["high_protein"],
        "allergies": [],
        "constraints": [],
        "locale": "zh-CN",
        "unit_system": "metric",
    }

    assert client.get(f"/api/workout-logs?user_id={alice_id}", headers=bob_headers).status_code == 403
    assert client.post("/api/profile", headers=bob_headers, json=profile).status_code == 403


def test_registered_user_can_manage_own_profile(mongo_store):
    session = register_session("own-profile@example.com")
    user_id = session["user"]["user_id"]
    headers = {"Authorization": f"Bearer {session['access_token']}"}
    profile = {
        "user_id": user_id,
        "display_name": "Own Profile",
        "age": 30,
        "height_cm": 176,
        "weight_kg": 74.8,
        "goal": "maintenance",
        "experience_level": "intermediate",
        "training_days_per_week": 3,
        "training_duration_minutes": 45,
        "equipment": ["gym"],
        "dietary_preferences": ["high_protein"],
        "allergies": [],
        "constraints": [],
        "locale": "zh-CN",
        "unit_system": "metric",
    }

    response = client.post("/api/profile", headers=headers, json=profile)

    assert response.status_code == 200
    assert response.json()["data"]["user_id"] == user_id
