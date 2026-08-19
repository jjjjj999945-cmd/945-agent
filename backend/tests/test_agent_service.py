import asyncio

import pytest

from backend.app.llm.errors import LLMTimeoutError
from backend.app.models.domain import AgentChatInput, AgentMessage, AgentRetryInput, AgentRun
from backend.app.services import demo_store
from backend.app.services import agent_service
from backend.app.services.agent_observability import summarize_agent_runs
from backend.app.services.agent_service import create_agent_reply
from backend.app.services.demo_seed import timestamp
from backend.app.services.demo_store import list_agent_messages


class FailingRouter:
    async def generate(self, request):
        raise LLMTimeoutError("timeout", request_id=request.request_id)

    async def recover(self, request, exc):
        raise exc


def test_demo_store_upserts_agent_runs_and_messages_by_id():
    now = timestamp()
    run = AgentRun(
        agent_run_id="run-upsert",
        user_id="demo-user-945",
        status="running",
        started_at=now,
        updated_at=now,
        request_input=AgentRetryInput(message="继续任务", locale="zh-CN"),
    )
    demo_store.save_agent_run(run)
    demo_store.save_agent_run(run.model_copy(update={"status": "interrupted"}))
    message = AgentMessage(
        message_id="msg-agent-run-upsert",
        user_id="demo-user-945",
        role="agent",
        content="旧内容",
        locale="zh-CN",
        created_at=now,
    )
    demo_store.save_agent_message(message)
    demo_store.save_agent_message(message.model_copy(update={"content": "新内容"}))

    assert len(demo_store.list_agent_runs("demo-user-945")) == 1
    assert demo_store.list_agent_runs("demo-user-945")[0].status == "interrupted"
    assert len(demo_store.list_agent_messages("demo-user-945")) == 1
    assert demo_store.list_agent_messages("demo-user-945")[0].content == "新内容"


def test_agent_metrics_exclude_nonterminal_runs_from_rate_and_latency():
    now = timestamp()
    runs = [
        AgentRun(
            agent_run_id="completed",
            user_id="demo-user-945",
            status="completed",
            started_at=now,
            updated_at=now,
            completed_at=now,
            duration_ms=100,
        ),
        AgentRun(
            agent_run_id="failed",
            user_id="demo-user-945",
            status="failed",
            started_at=now,
            updated_at=now,
            completed_at=now,
            duration_ms=300,
            error_code="LLM_TIMEOUT",
        ),
        AgentRun(
            agent_run_id="running",
            user_id="demo-user-945",
            status="running",
            started_at=now,
            updated_at=now,
            duration_ms=900,
        ),
        AgentRun(
            agent_run_id="interrupted",
            user_id="demo-user-945",
            status="interrupted",
            started_at=now,
            updated_at=now,
            duration_ms=700,
        ),
    ]

    metrics = summarize_agent_runs(runs)

    assert (metrics.total_runs, metrics.completed_runs, metrics.failed_runs) == (4, 1, 1)
    assert (metrics.running_runs, metrics.interrupted_runs) == (1, 1)
    assert metrics.success_rate == 0.5
    assert metrics.average_duration_ms == 200


def test_agent_service_does_not_save_partial_turn_on_provider_error():
    input_data = AgentChatInput(
        user_id="demo-user-945",
        locale="zh-CN",
        message="今天练什么？",
    )

    with pytest.raises(LLMTimeoutError):
        asyncio.run(create_agent_reply(input_data, provider_router=FailingRouter()))

    assert list_agent_messages("demo-user-945") == []
    runs = demo_store.list_agent_runs("demo-user-945")
    assert len(runs) == 1
    assert runs[0].status == "failed"
    assert runs[0].error_code == "LLM_TIMEOUT"
    assert runs[0].retry_input.message == input_data.message


def test_agent_service_saves_a_completed_run_without_model_reasoning():
    input_data = AgentChatInput(
        user_id="demo-user-945",
        locale="zh-CN",
        message="How should I warm up before a squat session?",
    )

    reply = asyncio.run(create_agent_reply(input_data))

    runs = demo_store.list_agent_runs("demo-user-945")
    assert reply is not None
    assert len(runs) == 1
    assert runs[0].status == "completed"
    assert runs[0].intent == "ask_question"
    assert runs[0].provider == "deterministic"
    assert runs[0].draft_type is None
    assert runs[0].error_code is None
    assert runs[0].input_tokens == 0
    assert runs[0].output_tokens == 0
    assert runs[0].logical_generations == 1
    assert runs[0].http_attempts == 0


def test_retrying_a_failed_run_creates_a_new_completed_run_without_writing_records():
    input_data = AgentChatInput(
        user_id="demo-user-945",
        locale="zh-CN",
        message="今天深蹲做了 4 组，每组 8 次，80kg，帮我记录",
    )

    with pytest.raises(LLMTimeoutError):
        asyncio.run(create_agent_reply(input_data, provider_router=FailingRouter()))

    failed_run = demo_store.list_agent_runs("demo-user-945")[0]
    reply = asyncio.run(agent_service.retry_agent_run("demo-user-945", failed_run.agent_run_id))

    runs = demo_store.list_agent_runs("demo-user-945")
    assert reply.record_draft.type == "workout_log"
    assert [message.role for message in list_agent_messages("demo-user-945")] == ["user", "agent"]
    assert [run.status for run in runs] == ["failed", "completed"]
    assert runs[1].retry_of_agent_run_id == failed_run.agent_run_id
    assert demo_store.list_workout_logs("demo-user-945") == []
