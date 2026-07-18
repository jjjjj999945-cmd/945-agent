import asyncio
from types import SimpleNamespace

import httpx
import pytest
from openai import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    InternalServerError,
    RateLimitError,
)

from backend.app.llm.errors import (
    LLMOutputInvalidError,
    LLMProviderError,
    LLMRateLimitedError,
    LLMTimeoutError,
)
from backend.app.llm.models import (
    AgentModelRequest,
    AgentToolDefinition,
    ProviderContinuation,
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


def _response(
    output_text: str,
    output: list[FakeItem],
    response_id: str = "resp-1",
    *,
    input_tokens: int = 20,
    output_tokens: int = 10,
) -> FakeResponse:
    return FakeResponse(
        id=response_id,
        output_text=output_text,
        output=output,
        usage=SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens),
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


def _continuation(
    call_id: str = "call-1",
    name: str = "create_workout_log_draft",
) -> ProviderContinuation:
    return ProviderContinuation(
        output_items=[
            {
                "type": "function_call",
                "call_id": call_id,
                "name": name,
                "arguments": "{}",
            }
        ]
    )


def _sdk_error(kind: str):
    request = httpx.Request(
        "POST",
        "https://api.openai.com/v1/responses",
        headers={"Authorization": "Bearer test-secret"},
    )
    if kind == "timeout":
        return APITimeoutError(request=request)
    if kind == "connection":
        return APIConnectionError(request=request)

    status_by_kind = {
        "rate_limit": 429,
        "server": 500,
        "authentication": 401,
    }
    response = httpx.Response(
        status_by_kind[kind],
        request=request,
        headers={"x-request-id": f"provider-{kind}"},
    )
    error_by_kind = {
        "rate_limit": RateLimitError,
        "server": InternalServerError,
        "authentication": AuthenticationError,
    }
    return error_by_kind[kind](f"{kind} error", response=response, body=None)


def test_openai_provider_returns_plain_text_without_sdk_objects():
    client = FakeClient([_response("基于今天的计划，建议先完成热身。", [])])
    provider = OpenAIProvider(client=client, model="configured-model", retry_delay_seconds=0)

    result = asyncio.run(provider.generate(_request().model_copy(update={"tools": []})))

    assert result.reply == "基于今天的计划，建议先完成热身。"
    assert result.provider == "openai"
    assert result.provider_request_id == "resp-1"
    assert result.usage.input_tokens == 20
    assert result.usage.output_tokens == 10
    assert result.usage.logical_generations == 1
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


def test_openai_provider_rejects_a_function_call_for_an_unprovided_tool():
    call = FakeItem(
        type="function_call",
        call_id="call-unknown",
        name="get_profile",
        arguments="{}",
    )
    provider = OpenAIProvider(
        client=FakeClient([_response("", [call])]),
        model="configured-model",
        retry_delay_seconds=0,
    )

    with pytest.raises(LLMOutputInvalidError) as captured:
        asyncio.run(provider.generate(_request()))

    assert captured.value.request_id == "req-openai"
    assert captured.value.provider_request_id == "resp-1"
    assert captured.value.http_attempts == 1


@pytest.mark.parametrize(
    "call",
    [
        FakeItem(
            type="function_call",
            name="create_workout_log_draft",
            arguments="{}",
        ),
        FakeItem(
            type="function_call",
            call_id="",
            name="create_workout_log_draft",
            arguments="{}",
        ),
        FakeItem(
            type="function_call",
            call_id="call-1",
            arguments="{}",
        ),
        FakeItem(
            type="function_call",
            call_id="call-1",
            name="",
            arguments="{}",
        ),
        FakeItem(
            type="function_call",
            call_id="call-1",
            name="create_workout_log_draft",
        ),
        FakeItem(
            type="function_call",
            call_id="call-1",
            name="create_workout_log_draft",
            arguments="",
        ),
        FakeItem(
            type="function_call",
            call_id="call-1",
            name="create_workout_log_draft",
            arguments="not-json",
        ),
        FakeItem(
            type="function_call",
            call_id="call-1",
            name="create_workout_log_draft",
            arguments="[]",
        ),
    ],
    ids=[
        "missing-call-id",
        "empty-call-id",
        "missing-name",
        "empty-name",
        "missing-arguments",
        "empty-arguments",
        "invalid-json",
        "non-object-arguments",
    ],
)
def test_openai_provider_maps_malformed_function_calls_to_output_invalid(call):
    provider = OpenAIProvider(
        client=FakeClient([_response("", [call])]),
        model="configured-model",
        retry_delay_seconds=0,
    )

    with pytest.raises(LLMOutputInvalidError) as captured:
        asyncio.run(provider.generate(_request()))

    assert captured.value.request_id == "req-openai"
    assert captured.value.provider_request_id == "resp-1"
    assert captured.value.http_attempts == 1


def test_openai_provider_sends_call_id_and_disables_tools_on_final_generation():
    reasoning = FakeItem(
        type="reasoning",
        id="reason-1",
        summary=[{"type": "summary_text", "text": "The user asked to log a workout."}],
        content=[{"type": "reasoning_text", "text": "Use the workout draft tool."}],
        encrypted_content="opaque-reasoning-state",
        status="completed",
    )
    call = FakeItem(
        type="function_call",
        call_id="call-1",
        name="create_workout_log_draft",
        arguments='{"exercise_name":"深蹲","sets":4,"reps":8,"weight_kg":80,"effort_note":"感觉很累"}',
    )
    client = FakeClient([
        _response("", [reasoning, call], response_id="resp-first"),
        _response(
            "训练草稿已整理，请确认后保存。",
            [],
            response_id="resp-final",
            input_tokens=7,
            output_tokens=3,
        ),
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
    assert first.usage.input_tokens == 20
    assert first.usage.output_tokens == 10
    assert first.usage.logical_generations == 1
    assert first.usage.http_attempts == 1
    assert final.usage.input_tokens == 7
    assert final.usage.output_tokens == 3
    assert final.usage.logical_generations == 1
    assert final.usage.http_attempts == 1
    assert first.continuation.output_items[0] == reasoning.model_dump(mode="json")
    first_payload = client.responses.requests[0]
    final_payload = client.responses.requests[1]
    assert first_payload["store"] is False
    assert final_payload["store"] is False
    assert final_payload["tools"] == first_payload["tools"]
    assert final_payload["tool_choice"] == "none"
    assert [item["type"] for item in final_payload["input"][-3:]] == [
        "reasoning",
        "function_call",
        "function_call_output",
    ]
    assert final_payload["input"][-3] == reasoning.model_dump(mode="json")
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
        name="create_workout_log_draft",
        arguments="{}",
    )
    provider = OpenAIProvider(
        client=FakeClient([_response("", [second_call])]),
        model="configured-model",
        retry_delay_seconds=0,
    )
    request = _request().model_copy(
        update={
            "continuation": _continuation(),
            "tool_result": ToolExecutionResult(
                call_id="call-1",
                name="create_workout_log_draft",
                output={"type": "workout_log"},
            )
        }
    )

    with pytest.raises(LLMOutputInvalidError, match="second tool round"):
        asyncio.run(provider.generate(request))


@pytest.mark.parametrize(
    ("continuation", "call_id", "name"),
    [
        (None, "call-1", "create_workout_log_draft"),
        (ProviderContinuation(output_items=[]), "call-1", "create_workout_log_draft"),
        (
            ProviderContinuation(
                output_items=[{"type": "reasoning", "id": "reason-1", "summary": []}]
            ),
            "call-1",
            "create_workout_log_draft",
        ),
        (
            ProviderContinuation(
                output_items=[
                    _continuation().output_items[0],
                    {
                        "type": "function_call",
                        "call_id": "call-2",
                        "name": "create_workout_log_draft",
                        "arguments": "{}",
                    },
                ]
            ),
            "call-1",
            "create_workout_log_draft",
        ),
        (_continuation(call_id="call-other"), "call-1", "create_workout_log_draft"),
        (_continuation(name="get_profile"), "call-1", "create_workout_log_draft"),
    ],
    ids=[
        "missing-continuation",
        "missing-function-call",
        "reasoning-without-function-call",
        "multiple-function-calls",
        "call-id-mismatch",
        "name-mismatch",
    ],
)
def test_openai_provider_rejects_invalid_second_round_state(continuation, call_id, name):
    client = FakeClient([_response("must not be requested", [])])
    provider = OpenAIProvider(client=client, model="configured-model", retry_delay_seconds=0)
    request = _request().model_copy(
        update={
            "continuation": continuation,
            "tool_result": ToolExecutionResult(
                call_id=call_id,
                name=name,
                output={"type": "workout_log"},
            ),
        }
    )

    with pytest.raises(LLMOutputInvalidError) as captured:
        asyncio.run(provider.generate(request))

    assert captured.value.request_id == "req-openai"
    assert captured.value.http_attempts == 0
    assert client.responses.requests == []


@pytest.mark.parametrize(
    ("kind", "expected_error", "provider_request_id"),
    [
        ("timeout", LLMTimeoutError, None),
        ("rate_limit", LLMRateLimitedError, "provider-rate_limit"),
        ("connection", LLMProviderError, None),
        ("server", LLMProviderError, "provider-server"),
    ],
)
def test_openai_provider_retries_retryable_sdk_errors_once(
    kind,
    expected_error,
    provider_request_id,
):
    client = FakeClient([_sdk_error(kind), _sdk_error(kind)])
    provider = OpenAIProvider(
        client=client,
        model="configured-model",
        retry_delay_seconds=0,
    )

    with pytest.raises(expected_error) as captured:
        asyncio.run(provider.generate(_request()))

    assert len(client.responses.requests) == 2
    assert captured.value.request_id == "req-openai"
    assert captured.value.provider_request_id == provider_request_id
    assert captured.value.http_attempts == 2


def test_openai_provider_does_not_retry_4xx_or_leak_sdk_exception_context():
    client = FakeClient([_sdk_error("authentication")])
    provider = OpenAIProvider(client=client, model="configured-model", retry_delay_seconds=0)

    with pytest.raises(LLMProviderError) as captured:
        asyncio.run(provider.generate(_request()))

    error = captured.value
    assert len(client.responses.requests) == 1
    assert error.request_id == "req-openai"
    assert error.provider_request_id == "provider-authentication"
    assert error.http_attempts == 1
    assert error.__cause__ is None
    assert error.__context__ is None
    assert "Authorization" not in repr(error.__dict__)
    assert "test-secret" not in repr(error.__dict__)


def test_openai_provider_reports_two_attempts_after_a_successful_retry():
    client = FakeClient([
        _sdk_error("timeout"),
        _response(
            "重试后成功。",
            [],
            response_id="resp-retry",
            input_tokens=11,
            output_tokens=4,
        ),
    ])
    provider = OpenAIProvider(client=client, model="configured-model", retry_delay_seconds=0)

    result = asyncio.run(provider.generate(_request().model_copy(update={"tools": []})))

    assert result.provider_request_id == "resp-retry"
    assert result.usage.input_tokens == 11
    assert result.usage.output_tokens == 4
    assert result.usage.logical_generations == 1
    assert result.usage.http_attempts == 2
    assert len(client.responses.requests) == 2
