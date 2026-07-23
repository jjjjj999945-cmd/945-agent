from fastapi.testclient import TestClient

from backend.app.core.config import get_settings
from backend.app.llm.factory import get_llm_provider_router
from backend.app.main import app


client = TestClient(app)


def _clear_llm_caches():
    get_settings.cache_clear()
    get_llm_provider_router.cache_clear()


def test_agent_chat_returns_workout_record_draft_without_saving_log():
    response = client.post(
        "/api/agent/chat",
        json={
            "user_id": "demo-user-945",
            "locale": "zh-CN",
            "message": "今天深蹲做了 4 组，每组 8 次，80kg，感觉很累。",
            "context": {
                "current_page": "today",
                "date": "2026-07-11"
            }
        }
    )

    assert response.status_code == 200
    body = response.json()
    assert body["error"] is None
    assert body["data"]["role"] == "agent"
    assert body["data"]["record_draft"] == {
        "type": "workout_log",
        "requires_confirmation": True,
        "payload": {
            "exercise_name": "深蹲",
            "sets": 4,
            "reps": 8,
            "weight_kg": 80,
            "effort_note": "今天深蹲做了 4 组，每组 8 次，80kg，感觉很累。"
        }
    }

    logs_response = client.get("/api/workout-logs", params={"user_id": "demo-user-945"})
    assert logs_response.status_code == 200
    assert logs_response.json()["data"] == []


def test_agent_chat_returns_meal_record_draft():
    response = client.post(
        "/api/agent/chat",
        json={
            "user_id": "demo-user-945",
            "locale": "zh-CN",
            "message": "我中午吃了鸡胸肉饭，可以帮我记录吗？"
        }
    )

    assert response.status_code == 200
    draft = response.json()["data"]["record_draft"]
    assert draft["type"] == "meal_log"
    assert draft["requires_confirmation"] is True
    assert draft["payload"]["meal_name"] == "手动记录"
    assert draft["payload"]["note"] == "我中午吃了鸡胸肉饭，可以帮我记录吗？"


def test_agent_chat_high_risk_input_returns_safety_reply_without_draft():
    response = client.post(
        "/api/agent/chat",
        json={
            "user_id": "demo-user-945",
            "locale": "zh-CN",
            "message": "我训练时胸闷眩晕，还能继续冲重量吗？"
        }
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["record_draft"] is None
    assert "暂停训练" in data["content"]
    assert "专业人士" in data["content"]


def test_get_agent_messages_returns_user_and_agent_messages():
    client.post(
        "/api/agent/chat",
        json={
            "user_id": "demo-user-945",
            "locale": "en-US",
            "message": "I did squats today."
        }
    )

    response = client.get("/api/agent/messages", params={"user_id": "demo-user-945"})

    assert response.status_code == 200
    messages = response.json()["data"]
    assert [message["role"] for message in messages] == ["user", "agent"]
    assert messages[0]["content"] == "I did squats today."


def test_agent_chat_rejects_unknown_user():
    response = client.post(
        "/api/agent/chat",
        json={
            "user_id": "missing-user",
            "locale": "zh-CN",
            "message": "今天深蹲 4 组。"
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


def test_agent_chat_development_openai_mode_falls_back_without_key(monkeypatch):
    monkeypatch.setenv("945_APP_ENV", "development")
    monkeypatch.setenv("945_LLM_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("945_OPENAI_MODEL", raising=False)
    _clear_llm_caches()

    response = client.post(
        "/api/agent/chat",
        json={
            "user_id": "demo-user-945",
            "locale": "zh-CN",
            "message": "今天深蹲做了 4 组，每组 8 次，80kg。",
        },
    )

    assert response.status_code == 200
    assert response.json()["data"]["record_draft"]["requires_confirmation"] is True


def test_agent_chat_production_openai_mode_returns_config_error_without_saving(monkeypatch):
    monkeypatch.setenv("945_APP_ENV", "production")
    monkeypatch.setenv("945_LLM_PROVIDER", "openai")
    monkeypatch.setenv("945_AUTH_REQUIRED", "false")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("945_OPENAI_MODEL", raising=False)
    _clear_llm_caches()

    response = client.post(
        "/api/agent/chat",
        json={
            "user_id": "demo-user-945",
            "locale": "zh-CN",
            "message": "今天练什么？",
        },
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "LLM_CONFIG_ERROR"
    messages = client.get("/api/agent/messages", params={"user_id": "demo-user-945"})
    assert messages.json()["data"] == []
    today = client.get(
        "/api/today",
        params={"user_id": "demo-user-945", "date": "2026-07-11"},
    )
    assert today.status_code == 200
