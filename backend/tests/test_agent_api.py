import asyncio

import pytest
from fastapi.testclient import TestClient

from backend.app.core.config import get_settings
from backend.app.llm.factory import get_llm_provider_router
from backend.app.llm.errors import LLMTimeoutError
from backend.app.main import app
from backend.app.models.domain import AgentChatInput, AgentRun
from backend.app.services import demo_store
from backend.app.services.agent_service import create_agent_reply
from backend.app.services.demo_seed import timestamp


client = TestClient(app)


class FailingRouter:
    async def generate(self, request):
        raise LLMTimeoutError("timeout", request_id=request.request_id)

    async def recover(self, request, exc):
        raise exc


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


def test_agent_chat_parses_explicit_workout_log_values():
    response = client.post(
        "/api/agent/chat",
        json={
            "user_id": "demo-user-945",
            "locale": "zh-CN",
            "message": "帮我记录：深蹲 3 组，每组 12 次，60kg。",
        },
    )

    assert response.status_code == 200
    assert response.json()["data"]["record_draft"]["payload"] == {
        "exercise_name": "深蹲",
        "sets": 3,
        "reps": 12,
        "weight_kg": 60,
        "effort_note": "帮我记录：深蹲 3 组，每组 12 次，60kg。",
    }


def test_agent_chat_answers_food_question_without_creating_a_record_draft():
    response = client.post(
        "/api/agent/chat",
        json={
            "user_id": "demo-user-945",
            "locale": "zh-CN",
            "message": "鸡胸肉的蛋白质含量是多少？",
        },
    )

    assert response.status_code == 200
    assert response.json()["data"]["record_draft"] is None


def test_agent_run_trace_exposes_safe_workflow_steps_only():
    response = client.post(
        "/api/agent/chat",
        json={
            "user_id": "demo-user-945",
            "locale": "en-US",
            "message": "How should I warm up before a squat session?",
        },
    )
    assert response.status_code == 200
    run_id = client.get("/api/agent/runs", params={"user_id": "demo-user-945"}).json()["data"][0]["agent_run_id"]

    trace_response = client.get(
        f"/api/agent/runs/{run_id}/trace",
        params={"user_id": "demo-user-945"},
    )

    assert trace_response.status_code == 200
    trace = trace_response.json()["data"]
    assert [step["name"] for step in trace] == [
        "safety_guard",
        "context_builder",
        "rag_retriever",
        "memory_context",
        "model_generation",
        "tool_execution",
        "draft_validator",
    ]
    assert all("message" not in step["metadata"] for step in trace)
    assert all("chain_of_thought" not in step["metadata"] for step in trace)


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


def test_agent_chat_enforces_per_user_hourly_run_limit(monkeypatch):
    monkeypatch.setenv("945_AGENT_MAX_RUNS_PER_HOUR", "1")
    _clear_llm_caches()
    payload = {
        "user_id": "demo-user-945",
        "locale": "en-US",
        "message": "How should I warm up before a squat session?",
    }

    assert client.post("/api/agent/chat", json=payload).status_code == 200
    response = client.post("/api/agent/chat", json=payload)

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "AGENT_USAGE_LIMIT"
    assert len(demo_store.list_agent_runs("demo-user-945")) == 1


def test_agent_chat_enforces_daily_token_limit(monkeypatch):
    monkeypatch.setenv("945_AGENT_MAX_TOKENS_PER_DAY", "1")
    _clear_llm_caches()
    now = timestamp()
    demo_store.save_agent_run(
        AgentRun(
            agent_run_id="run-token-limit",
            user_id="demo-user-945",
            status="completed",
            started_at=now,
            completed_at=now,
            duration_ms=1,
            input_tokens=1,
        )
    )

    response = client.post(
        "/api/agent/chat",
        json={
            "user_id": "demo-user-945",
            "locale": "en-US",
            "message": "How should I warm up before a squat session?",
        },
    )

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "AGENT_USAGE_LIMIT"


def test_agent_chat_enforces_daily_logical_generation_limit(monkeypatch):
    monkeypatch.setenv("945_AGENT_MAX_LOGICAL_GENERATIONS_PER_DAY", "1")
    _clear_llm_caches()
    now = timestamp()
    demo_store.save_agent_run(
        AgentRun(
            agent_run_id="run-generation-limit",
            user_id="demo-user-945",
            status="completed",
            started_at=now,
            completed_at=now,
            duration_ms=1,
            logical_generations=1,
        )
    )

    response = client.post(
        "/api/agent/chat",
        json={
            "user_id": "demo-user-945",
            "locale": "en-US",
            "message": "How should I warm up before a squat session?",
        },
    )

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "AGENT_USAGE_LIMIT"


def test_agent_chat_keeps_generation_limit_when_token_limit_is_disabled(monkeypatch):
    monkeypatch.setenv("945_AGENT_MAX_TOKENS_PER_DAY", "0")
    monkeypatch.setenv("945_AGENT_MAX_LOGICAL_GENERATIONS_PER_DAY", "1")
    _clear_llm_caches()
    now = timestamp()
    demo_store.save_agent_run(
        AgentRun(
            agent_run_id="run-generation-limit-token-disabled",
            user_id="demo-user-945",
            status="completed",
            started_at=now,
            completed_at=now,
            duration_ms=1,
            logical_generations=1,
        )
    )

    response = client.post(
        "/api/agent/chat",
        json={
            "user_id": "demo-user-945",
            "locale": "en-US",
            "message": "How should I warm up before a squat session?",
        },
    )

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "AGENT_USAGE_LIMIT"


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


def test_get_agent_runs_exposes_safe_observability_fields_only():
    client.post(
        "/api/agent/chat",
        json={
            "user_id": "demo-user-945",
            "locale": "en-US",
            "message": "How should I warm up before a squat session?",
        },
    )

    response = client.get("/api/agent/runs", params={"user_id": "demo-user-945"})

    assert response.status_code == 200
    run = response.json()["data"][0]
    assert run["status"] == "completed"
    assert run["provider"] == "deterministic"
    assert run["intent"] == "ask_question"
    assert "retry_input" not in run


def test_get_agent_metrics_aggregates_success_failure_and_latency():
    client.post(
        "/api/agent/chat",
        json={
            "user_id": "demo-user-945",
            "locale": "en-US",
            "message": "How should I warm up before a squat session?",
        },
    )
    with pytest.raises(LLMTimeoutError):
        asyncio.run(
            create_agent_reply(
                AgentChatInput(
                    user_id="demo-user-945",
                    locale="en-US",
                    message="How should I warm up before a squat session?",
                ),
                provider_router=FailingRouter(),
            )
        )

    response = client.get("/api/agent/metrics", params={"user_id": "demo-user-945"})

    assert response.status_code == 200
    assert response.json()["data"] == {
        "total_runs": 2,
        "completed_runs": 1,
        "failed_runs": 1,
        "running_runs": 0,
        "interrupted_runs": 0,
        "success_rate": 0.5,
        "average_duration_ms": pytest.approx(response.json()["data"]["average_duration_ms"]),
        "total_input_tokens": 0,
        "total_output_tokens": 0,
        "total_logical_generations": 1,
        "total_http_attempts": 0,
        "failures_by_code": {"LLM_TIMEOUT": 1},
    }


def test_retry_agent_run_replays_only_a_failed_turn_and_returns_a_draft():
    input_data = AgentChatInput(
        user_id="demo-user-945",
        locale="en-US",
        message="I did squats today, log it",
    )
    with pytest.raises(LLMTimeoutError):
        asyncio.run(create_agent_reply(input_data, provider_router=FailingRouter()))

    failed_run = demo_store.list_agent_runs("demo-user-945")[0]
    response = client.post(
        f"/api/agent/runs/{failed_run.agent_run_id}/retry",
        json={"user_id": "demo-user-945"},
    )

    assert response.status_code == 200
    assert response.json()["data"]["record_draft"]["type"] == "workout_log"
    assert demo_store.list_workout_logs("demo-user-945") == []


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
