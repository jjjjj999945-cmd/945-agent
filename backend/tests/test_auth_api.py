from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def test_registration_requires_mongo_storage():
    response = client.post(
        "/api/auth/register",
        json={"display_name": "User", "email": "user@example.com", "password": "secure-pass-945"},
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "STORAGE_CONFIG_ERROR"


def test_mongo_registration_creates_revocable_session(mongo_store):
    registered = client.post(
        "/api/auth/register",
        json={"display_name": "User", "email": "user@example.com", "password": "secure-pass-945"},
    )

    assert registered.status_code == 200
    session = registered.json()["data"]
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
