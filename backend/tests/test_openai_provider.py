import asyncio
from types import SimpleNamespace

import httpx
import pytest
from openai import APITimeoutError, RateLimitError

from backend.app.llm.errors import LLMOutputInvalidError, LLMRateLimitedError, LLMTimeoutError
from backend.app.llm.models import (
    AgentModelRequest,
    AgentToolDefinition,
    ToolExecutionResult,
)
from backend.app.llm.openai_provider import OpenAIProvider


class FakeItem(SimpleNamespace):
    def model_dump(self, mode: str = "python"):
        return dict(self.__dict__)


class FakeResponse(SimpleNamespace):
    pass


class FakeResponses:
    def __init__(self, results):
        self.results = list(results)
        self.requests = []

    async def create(self, **kwargs):
        self.requests.append(kwargs)
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


class FakeClient:
    def __init__(self, results):
        self.responses = FakeResponses(results)


def _response(output_text: str, output: list[FakeItem], response_id: str = "resp-1") -> FakeResponse:
    return FakeResponse(
        id=response_id,
        output_text=output_text,
        output=output,
        usage=SimpleNamespace(input_tokens=20, output_tokens=10),
    )


def _request() -> AgentModelRequest:
    return AgentModelRequest(
        request_id="req-openai",
        user_id="demo-user-945",
        locale="zh-CN",
        message="今天深蹲 4 组 8 次 80kg，帮我记录。",
        tools=[
            AgentToolDefinition(
                name="create_workout_log_draft",
                description="Create a workout draft.",
                parameters={
                    "type": "object",
                    "properties": {},
                    "required": [],
                    "additionalProperties": False,
                },
            )
        ],
    )


def test_openai_provider_returns_plain_text_without_sdk_objects():
    client = FakeClient([_response("基于今天的计划，建议先完成热身。", [])])
    provider = OpenAIProvider(client=client, model="configured-model", retry_delay_seconds=0)

    result = asyncio.run(provider.generate(_request().model_copy(update={"tools": []})))

    assert result.reply == "基于今天的计划，建议先完成热身。"
    assert result.provider == "openai"
    assert result.provider_request_id == "resp-1"
    assert result.usage.input_tokens == 20
    assert result.usage.http_attempts == 1
    assert client.responses.requests[0]["store"] is False
    assert client.responses.requests[0]["parallel_tool_calls"] is False


def test_openai_provider_parses_one_function_call_and_continuation():
    reasoning = FakeItem(type="reasoning", id="reason-1", summary=[])
    call = FakeItem(
        type="function_call",
        call_id="call-1",
        name="create_workout_log_draft",
        arguments='{"exercise_name":"深蹲","sets":4,"reps":8,"weight_kg":80,"effort_note":"感觉很累"}',
    )
    client = FakeClient([_response("", [reasoning, call])])
    provider = OpenAIProvider(client=client, model="configured-model", retry_delay_seconds=0)

    result = asyncio.run(provider.generate(_request()))

    assert result.intent == "log_workout"
    assert result.tool_call.call_id == "call-1"
    assert result.tool_call.arguments["sets"] == 4
    assert [item["type"] for item in result.continuation.output_items] == [
        "reasoning",
        "function_call",
    ]


def test_openai_provider_sends_call_id_and_disables_tools_on_final_generation():
    reasoning = FakeItem(type="reasoning", id="reason-1", summary=[])
    call = FakeItem(
        type="function_call",
        call_id="call-1",
        name="create_workout_log_draft",
        arguments='{"exercise_name":"深蹲","sets":4,"reps":8,"weight_kg":80,"effort_note":"感觉很累"}',
    )
    client = FakeClient([
        _response("", [reasoning, call], response_id="resp-first"),
        _response("训练草稿已整理，请确认后保存。", [], response_id="resp-final"),
    ])
    provider = OpenAIProvider(client=client, model="configured-model", retry_delay_seconds=0)
    first = asyncio.run(provider.generate(_request()))
    second_request = _request().model_copy(
        update={
            "continuation": first.continuation,
            "tool_result": ToolExecutionResult(
                call_id="call-1",
                name="create_workout_log_draft",
                output={"type": "workout_log", "requires_confirmation": True},
            ),
        }
    )

    final = asyncio.run(provider.generate(second_request))

    assert final.reply == "训练草稿已整理，请确认后保存。"
    final_payload = client.responses.requests[1]
    assert final_payload["tools"]
    assert final_payload["tool_choice"] == "none"
    assert [item["type"] for item in final_payload["input"][-3:]] == [
        "reasoning",
        "function_call",
        "function_call_output",
    ]
    assert final_payload["input"][-1] == {
        "type": "function_call_output",
        "call_id": "call-1",
        "output": '{"type": "workout_log", "requires_confirmation": true}',
    }


def test_openai_provider_rejects_multiple_tool_calls():
    calls = [
        FakeItem(type="function_call", call_id="call-1", name="get_profile", arguments="{}"),
        FakeItem(type="function_call", call_id="call-2", name="get_current_plan", arguments="{}"),
    ]
    provider = OpenAIProvider(
        client=FakeClient([_response("", calls)]),
        model="configured-model",
        retry_delay_seconds=0,
    )

    with pytest.raises(LLMOutputInvalidError, match="at most one tool"):
        asyncio.run(provider.generate(_request()))


def test_openai_provider_rejects_a_tool_call_after_tool_output():
    second_call = FakeItem(
        type="function_call",
        call_id="call-2",
        name="get_profile",
        arguments="{}",
    )
    provider = OpenAIProvider(
        client=FakeClient([_response("", [second_call])]),
        model="configured-model",
        retry_delay_seconds=0,
    )
    request = _request().model_copy(
        update={
            "tool_result": ToolExecutionResult(
                call_id="call-1",
                name="create_workout_log_draft",
                output={"type": "workout_log"},
            )
        }
    )

    with pytest.raises(LLMOutputInvalidError, match="second tool round"):
        asyncio.run(provider.generate(request))


def test_openai_provider_retries_timeout_once_then_maps_error():
    request = httpx.Request("POST", "https://api.openai.com/v1/responses")
    timeout = APITimeoutError(request=request)
    client = FakeClient([timeout, timeout])
    provider = OpenAIProvider(client=client, model="configured-model", retry_delay_seconds=0)

    with pytest.raises(LLMTimeoutError) as captured:
        asyncio.run(provider.generate(_request()))

    assert captured.value.http_attempts == 2
    assert len(client.responses.requests) == 2


def test_openai_provider_maps_rate_limit_after_one_retry():
    request = httpx.Request("POST", "https://api.openai.com/v1/responses")
    response = httpx.Response(429, request=request)
    limited = RateLimitError("rate limited", response=response, body=None)
    provider = OpenAIProvider(
        client=FakeClient([limited, limited]),
        model="configured-model",
        retry_delay_seconds=0,
    )

    with pytest.raises(LLMRateLimitedError):
        asyncio.run(provider.generate(_request()))
