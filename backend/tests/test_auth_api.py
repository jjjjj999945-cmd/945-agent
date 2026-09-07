from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.config import get_settings
from backend.app.repositories.mongo import MongoRepository
from backend.app.models.domain import AgentRetryInput, AgentRun
from backend.app.services import demo_store
from backend.app.services.demo_seed import timestamp
from backend.app.services.repository_store import RepositoryBackedStore
from backend.tests.test_mongo_repository import FakeDatabase


client = TestClient(app)


def test_register_login_and_read_current_session():
    registered = client.post("/api/auth/register", json={"display_name": "Test User", "email": "test@example.com", "password": "secure-pass-945"})
    assert registered.status_code == 200
    session = registered.json()["data"]
    assert session["token_type"] == "bearer"
    assert session["user"]["display_name"] == "Test User"

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {session['access_token']}"})
    assert me.status_code == 200
    assert me.json()["data"]["user_id"] == session["user"]["user_id"]

    login_response = client.post("/api/auth/login", json={"email": "test@example.com", "password": "secure-pass-945"})
    assert login_response.status_code == 200
    assert login_response.json()["data"]["user"]["user_id"] == session["user"]["user_id"]


def test_auth_rejects_invalid_credentials_and_invalid_session():
    assert client.post("/api/auth/login", json={"email": "missing@example.com", "password": "secure-pass-945"}).status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer invalid"}).status_code == 401


def test_authenticated_user_can_change_password():
    registered = client.post("/api/auth/register", json={"display_name": "Password User", "email": "password-change@example.com", "password": "secure-pass-945"}).json()["data"]
    headers = {"Authorization": f"Bearer {registered['access_token']}"}
    changed = client.post("/api/auth/change-password", json={"current_password": "secure-pass-945", "new_password": "new-secure-pass-945"}, headers=headers)
    assert changed.status_code == 200
    assert client.get("/api/auth/me", headers=headers).status_code == 401
    assert client.post("/api/auth/login", json={"email": "password-change@example.com", "password": "secure-pass-945"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": "password-change@example.com", "password": "new-secure-pass-945"}).status_code == 200


def test_logout_revokes_current_token():
    registered = client.post("/api/auth/register", json={"display_name": "Logout User", "email": "logout@example.com", "password": "secure-pass-945"}).json()["data"]
    headers = {"Authorization": f"Bearer {registered['access_token']}"}
    assert client.post("/api/auth/logout", headers=headers).status_code == 200
    assert client.get("/api/auth/me", headers=headers).status_code == 401


def test_login_sets_http_only_refresh_cookie_and_refresh_rotates_it():
    email = "refresh-cookie@example.com"
    assert client.post(
        "/api/auth/register",
        json={"display_name": "Refresh Cookie", "email": email, "password": "secure-pass-945"},
    ).status_code == 200

    login_response = client.post(
        "/api/auth/login",
        json={"email": email, "password": "secure-pass-945"},
    )

    assert login_response.status_code == 200
    assert "httponly" in login_response.headers["set-cookie"].lower()
    assert "samesite=lax" in login_response.headers["set-cookie"].lower()
    assert "path=/api/auth" in login_response.headers["set-cookie"].lower()
    first_refresh = login_response.cookies.get("945_refresh_token")
    refreshed = client.post("/api/auth/refresh")

    assert refreshed.status_code == 200
    assert refreshed.cookies.get("945_refresh_token") != first_refresh


def test_foreign_device_revoke_returns_not_found():
    alice = client.post(
        "/api/auth/register",
        json={"display_name": "Alice Devices", "email": "alice-devices@example.com", "password": "secure-pass-945"},
    ).json()["data"]
    bob = client.post(
        "/api/auth/register",
        json={"display_name": "Bob Devices", "email": "bob-devices@example.com", "password": "secure-pass-945"},
    ).json()["data"]

    response = client.delete(
        f"/api/auth/sessions/{bob['session_id']}",
        headers={"Authorization": f"Bearer {alice['access_token']}"},
    )

    assert response.status_code == 404


def test_login_rate_limit_and_production_auth_requirement(monkeypatch):
    email = "rate-limit@example.com"
    for _ in range(5):
        assert client.post("/api/auth/login", json={"email": email, "password": "wrong-password"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": email, "password": "wrong-password"}).status_code == 429

    monkeypatch.setenv("945_APP_ENV", "production")
    get_settings.cache_clear()
    try:
        assert client.get("/api/workout-logs?user_id=demo-user-945").status_code == 401
    finally:
        monkeypatch.delenv("945_APP_ENV", raising=False)
        get_settings.cache_clear()


def test_mongo_session_isolates_two_users(monkeypatch):
    monkeypatch.setenv("945_STORAGE_BACKEND", "mongo")
    get_settings.cache_clear()
    store = RepositoryBackedStore(MongoRepository(FakeDatabase()))
    store.seed_demo_data()
    demo_store.set_repository_store_for_tests(store)
    try:
        first = client.post("/api/auth/register", json={"display_name": "Alice", "email": "alice-isolation@example.com", "password": "secure-pass-945"}).json()["data"]
        second = client.post("/api/auth/register", json={"display_name": "Bob", "email": "bob-isolation@example.com", "password": "secure-pass-945"}).json()["data"]
        alice_headers = {"Authorization": f"Bearer {first['access_token']}"}
        bob_headers = {"Authorization": f"Bearer {second['access_token']}"}
        payload = {
            "user_id": first["user"]["user_id"], "date": "2026-07-11", "status": "completed",
            "exercises": [{"name": "深蹲", "sets": [{"reps": 8, "weight_kg": 80}]}],
        }
        assert client.post("/api/workout-logs", json=payload, headers=alice_headers).status_code == 200
        assert client.get(f"/api/workout-logs?user_id={first['user']['user_id']}", headers=bob_headers).status_code == 403
        assert client.get(f"/api/workout-logs?user_id={second['user']['user_id']}", headers=bob_headers).json()["data"] == []
        incomplete_plan = client.post("/api/plans/generate", json={"user_id": first["user"]["user_id"]}, headers=alice_headers)
        assert incomplete_plan.status_code == 409
        assert incomplete_plan.json()["error"]["code"] == "PROFILE_INCOMPLETE"
        confirmed = client.patch(
            f"/api/profile/{first['user']['user_id']}",
            json={"safety_confirmed": True},
            headers=alice_headers,
        )
        assert confirmed.status_code == 200

        plan = client.post("/api/plans/generate", json={"user_id": first["user"]["user_id"]}, headers=alice_headers)
        assert plan.status_code == 200
        assert plan.json()["data"]["user_id"] == first["user"]["user_id"]
        now = timestamp()
        alice_run = AgentRun(
            agent_run_id="alice-interrupted-run",
            user_id=first["user"]["user_id"],
            status="interrupted",
            started_at=now,
            updated_at=now,
            request_input=AgentRetryInput(message="继续任务", locale="zh-CN"),
        )
        demo_store.save_agent_run(alice_run)

        cross_user_resume = client.post(
            f"/api/agent/runs/{alice_run.agent_run_id}/resume",
            json={"user_id": second["user"]["user_id"]},
            headers=bob_headers,
        )

        assert cross_user_resume.status_code == 404
        saved_alice_run = demo_store.list_agent_runs(first["user"]["user_id"])[0]
        assert saved_alice_run.status == "interrupted"
        assert saved_alice_run.resume_count == 0
        assert client.post("/api/auth/login", json={"email": "alice-isolation@example.com", "password": "secure-pass-945"}).status_code == 200
    finally:
        demo_store.set_repository_store_for_tests(None)
        monkeypatch.delenv("945_STORAGE_BACKEND", raising=False)
        get_settings.cache_clear()
