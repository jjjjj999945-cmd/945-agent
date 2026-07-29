import asyncio

import pytest

from backend.app.llm.errors import LLMTimeoutError
from backend.app.models.domain import AgentChatInput
from backend.app.services import demo_store
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
