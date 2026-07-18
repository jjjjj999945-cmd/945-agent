import asyncio

import pytest

from backend.app.agents.graph import run_agent_graph
from backend.app.data.demo_data import DEMO_USER_ID
from backend.app.llm.errors import LLMOutputInvalidError
from backend.app.llm.models import AgentModelResponse, ProviderContinuation, ToolCallProposal


class StubRouter:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    async def generate(self, request):
        self.requests.append(request)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    async def recover(self, request, exc):
        raise exc


def test_agent_graph_routes_high_risk_to_safety_response_before_provider():
    router = StubRouter(
        [
            AgentModelResponse(
                intent="ask_question",
                reply="should not be used",
                provider="stub",
            )
        ]
    )

    result = asyncio.run(
        run_agent_graph(
            user_id=DEMO_USER_ID,
            locale="zh-CN",
            message="我训练时胸闷眩晕，还能继续冲重量吗？",
            context={"date": "2026-07-11"},
            provider_router=router,
        )
    )

    assert result.intent == "safety_warning"
    assert result.record_draft is None
    assert "暂停训练" in result.reply
    assert router.requests == []


def test_agent_graph_generates_workout_draft_without_writing():
    router = StubRouter(
        [
            AgentModelResponse(
                intent="log_workout",
                reply="",
                provider="stub",
                tool_call=ToolCallProposal(
                    call_id="call-1",
                    name="create_workout_log_draft",
                    arguments={
                        "exercise_name": "深蹲",
                        "sets": 4,
                        "reps": 8,
                        "weight_kg": 80,
                        "effort_note": "今天深蹲 4 组 8 次 80kg",
                    },
                ),
                continuation=ProviderContinuation(
                    output_items=[
                        {
                            "type": "function_call",
                            "call_id": "call-1",
                            "name": "create_workout_log_draft",
                            "arguments": "{}",
                        }
                    ]
                ),
            ),
            AgentModelResponse(
                intent="log_workout",
                reply="训练草稿已整理，请确认后保存。",
                provider="stub",
            ),
        ]
    )

    result = asyncio.run(
        run_agent_graph(
            user_id=DEMO_USER_ID,
            locale="zh-CN",
            message="今天深蹲做了 4 组，每组 8 次，80kg。",
            context={"date": "2026-07-11"},
            provider_router=router,
        )
    )

    assert result.intent == "log_workout"
    assert result.record_draft.type == "workout_log"
    assert result.record_draft.payload["exercise_name"] == "深蹲"
    assert len(router.requests) == 2
    assert router.requests[1].tool_result.call_id == "call-1"


def test_agent_graph_retrieves_knowledge_for_question():
    router = StubRouter(
        [
            AgentModelResponse(
                intent="ask_question",
                reply="深蹲时注意脚跟稳定、核心收紧。",
                provider="stub",
            )
        ]
    )

    result = asyncio.run(
        run_agent_graph(
            user_id=DEMO_USER_ID,
            locale="zh-CN",
            message="深蹲动作要点是什么？",
            context={"date": "2026-07-11"},
            provider_router=router,
        )
    )

    assert result.intent == "ask_question"
    assert result.record_draft is None
    assert any(chunk.metadata["topic"] == "squat" for chunk in result.rag_chunks)
    assert router.requests[0].rag_chunks


def test_agent_graph_rejects_invalid_tool_output_in_production_router():
    router = StubRouter(
        [
            AgentModelResponse(
                intent="log_workout",
                reply="",
                provider="stub",
                tool_call=ToolCallProposal(
                    call_id="call-1",
                    name="create_workout_log_draft",
                    arguments={"exercise_name": "深蹲", "sets": "4"},
                ),
                continuation=ProviderContinuation(
                    output_items=[
                        {
                            "type": "function_call",
                            "call_id": "call-1",
                            "name": "create_workout_log_draft",
                            "arguments": "{}",
                        }
                    ]
                ),
            )
        ]
    )

    with pytest.raises(LLMOutputInvalidError):
        asyncio.run(
            run_agent_graph(
                user_id=DEMO_USER_ID,
                locale="zh-CN",
                message="今天练什么？",
                context={"date": "2026-07-11"},
                provider_router=router,
            )
        )
