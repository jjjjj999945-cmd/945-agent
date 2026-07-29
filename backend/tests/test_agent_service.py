import asyncio

import pytest

from backend.app.llm.errors import LLMTimeoutError
from backend.app.models.domain import AgentChatInput
from backend.app.services import demo_store
from backend.app.services import agent_service
from backend.app.services.agent_service import create_agent_reply
from backend.app.services.demo_store import list_agent_messages


class FailingRouter:
    async def generate(self, request):
        raise LLMTimeoutError("timeout", request_id=request.request_id)

    async def recover(self, request, exc):
        raise exc


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
