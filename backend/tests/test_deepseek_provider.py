import asyncio
from types import SimpleNamespace

from backend.app.llm.deepseek_provider import DeepSeekProvider
from backend.app.llm.models import AgentModelRequest, AgentToolDefinition, ProviderContinuation, ToolExecutionResult


class FakeCompletions:
    def __init__(self, response):
        self.response = response
        self.requests = []

    async def create(self, **kwargs):
        self.requests.append(kwargs)
        return self.response


class FakeClient:
    def __init__(self, response):
        self.chat = SimpleNamespace(completions=FakeCompletions(response))


def _request() -> AgentModelRequest:
    return AgentModelRequest(
        request_id="deepseek-request",
        user_id="demo-user-945",
        locale="zh-CN",
        message="Please log my squat workout.",
        tools=[
            AgentToolDefinition(
                name="create_workout_log_draft",
                description="Create a workout draft.",
                parameters={"type": "object", "properties": {}, "required": [], "additionalProperties": False},
            )
        ],
    )


def test_deepseek_provider_generates_draft_tool_call_with_thinking_disabled():
    tool_call = SimpleNamespace(
        id="call-1",
        function=SimpleNamespace(
            name="create_workout_log_draft",
            arguments='{"exercise_name":"squat","sets":4,"reps":8,"weight_kg":80,"effort_note":"done"}',
        ),
    )
    response = SimpleNamespace(
        id="deepseek-response",
        model="deepseek-v4-flash",
        choices=[SimpleNamespace(message=SimpleNamespace(content=None, tool_calls=[tool_call]))],
        usage=SimpleNamespace(prompt_tokens=20, completion_tokens=10),
    )
    client = FakeClient(response)
    provider = DeepSeekProvider(client=client, model="deepseek-v4-flash", retry_delay_seconds=0)

    result = asyncio.run(provider.generate(_request()))

    assert result.provider == "deepseek"
    assert result.intent == "log_workout"
    assert result.tool_call.call_id == "call-1"
    assert result.tool_call.arguments["sets"] == 4
    payload = client.chat.completions.requests[0]
    assert payload["model"] == "deepseek-v4-flash"
    assert payload["max_tokens"] == 600
    assert payload["extra_body"] == {"thinking": {"type": "disabled"}}
    assert payload["tools"][0]["function"]["name"] == "create_workout_log_draft"
    assert "strict" not in payload["tools"][0]["function"]


def test_deepseek_provider_keeps_the_only_draft_tool_when_model_requests_a_read_and_draft_pair():
    read_call = SimpleNamespace(
        id="call-read",
        function=SimpleNamespace(name="get_current_plan", arguments="{}"),
    )
    draft_call = SimpleNamespace(
        id="call-draft",
        function=SimpleNamespace(
            name="create_plan_adjustment_draft",
            arguments='{"adjustment_type":"change_schedule","reason":"Focus on chest"}',
        ),
    )
    response = SimpleNamespace(
        id="deepseek-response",
        model="deepseek-v4-flash",
        choices=[SimpleNamespace(message=SimpleNamespace(content=None, tool_calls=[read_call, draft_call]))],
        usage=SimpleNamespace(prompt_tokens=20, completion_tokens=10),
    )
    request = _request().model_copy(
        update={
            "tools": [
                AgentToolDefinition(
                    name="get_current_plan",
                    description="Read the current plan.",
                    parameters={"type": "object", "properties": {}, "required": [], "additionalProperties": False},
                ),
                AgentToolDefinition(
                    name="create_plan_adjustment_draft",
                    description="Create a plan adjustment draft.",
                    parameters={"type": "object", "properties": {}, "required": [], "additionalProperties": False},
                ),
            ]
        }
    )
    provider = DeepSeekProvider(client=FakeClient(response), model="deepseek-v4-flash", retry_delay_seconds=0)

    result = asyncio.run(provider.generate(request))

    assert result.tool_call.call_id == "call-draft"
    assert result.tool_call.name == "create_plan_adjustment_draft"
    assert result.continuation.output_items[0]["tool_calls"] == [
        {
            "id": "call-draft",
            "type": "function",
            "function": {
                "name": "create_plan_adjustment_draft",
                "arguments": '{"adjustment_type":"change_schedule","reason":"Focus on chest"}',
            },
        }
    ]


def test_deepseek_provider_prefers_the_draft_that_matches_an_explicit_plan_adjustment_request():
    workout_call = SimpleNamespace(
        id="call-workout",
        function=SimpleNamespace(
            name="create_workout_log_draft",
            arguments='{"exercise_name":"Bench press","sets":4,"reps":8,"weight_kg":60,"effort_note":"done"}',
        ),
    )
    plan_call = SimpleNamespace(
        id="call-plan",
        function=SimpleNamespace(
            name="create_plan_adjustment_draft",
            arguments='{"adjustment_type":"change_schedule","reason":"Focus on chest"}',
        ),
    )
    response = SimpleNamespace(
        id="deepseek-response",
        model="deepseek-v4-flash",
        choices=[SimpleNamespace(message=SimpleNamespace(content=None, tool_calls=[workout_call, plan_call]))],
        usage=SimpleNamespace(prompt_tokens=20, completion_tokens=10),
    )
    request = _request().model_copy(
        update={
            "message": "Please adjust today's plan and create a plan adjustment draft.",
            "tools": [
                AgentToolDefinition(
                    name="create_workout_log_draft",
                    description="Create a workout draft.",
                    parameters={"type": "object", "properties": {}, "required": [], "additionalProperties": False},
                ),
                AgentToolDefinition(
                    name="create_plan_adjustment_draft",
                    description="Create a plan adjustment draft.",
                    parameters={"type": "object", "properties": {}, "required": [], "additionalProperties": False},
                ),
            ],
        }
    )
    provider = DeepSeekProvider(client=FakeClient(response), model="deepseek-v4-flash", retry_delay_seconds=0)

    result = asyncio.run(provider.generate(request))

    assert result.tool_call.call_id == "call-plan"


def test_deepseek_provider_ignores_an_unknown_companion_tool_when_one_allowed_read_tool_remains():
    read_call = SimpleNamespace(
        id="call-read",
        function=SimpleNamespace(name="get_current_plan", arguments="{}"),
    )
    unknown_call = SimpleNamespace(
        id="call-unknown",
        function=SimpleNamespace(name="draft_workout_record", arguments="{}"),
    )
    response = SimpleNamespace(
        id="deepseek-response",
        model="deepseek-v4-flash",
        choices=[SimpleNamespace(message=SimpleNamespace(content=None, tool_calls=[read_call, unknown_call]))],
        usage=SimpleNamespace(prompt_tokens=20, completion_tokens=10),
    )
    request = _request().model_copy(
        update={
            "tools": [
                AgentToolDefinition(
                    name="get_current_plan",
                    description="Read the current plan.",
                    parameters={"type": "object", "properties": {}, "required": [], "additionalProperties": False},
                )
            ]
        }
    )
    provider = DeepSeekProvider(client=FakeClient(response), model="deepseek-v4-flash", retry_delay_seconds=0)

    result = asyncio.run(provider.generate(request))

    assert result.tool_call.call_id == "call-read"
    assert result.tool_call.name == "get_current_plan"


def test_deepseek_provider_ignores_unknown_tool_markup_after_a_read_result():
    unknown_call = SimpleNamespace(
        id="call-unknown",
        function=SimpleNamespace(name="draft_workout_record", arguments="{}"),
    )
    response = SimpleNamespace(
        id="deepseek-response",
        model="deepseek-v4-flash",
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content="DSML: draft_workout_record",
                    tool_calls=[unknown_call],
                )
            )
        ],
        usage=SimpleNamespace(prompt_tokens=20, completion_tokens=10),
    )
    request = _request().model_copy(
        update={
            "tool_result": ToolExecutionResult(
                call_id="call-read",
                name="get_current_plan",
                output={"plan": "current"},
            )
            ,
            "continuation": ProviderContinuation(
                output_items=[
                    {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call-read",
                                "type": "function",
                                "function": {"name": "get_current_plan", "arguments": "{}"},
                            }
                        ],
                    }
                ]
            ),
        }
    )
    provider = DeepSeekProvider(client=FakeClient(response), model="deepseek-v4-flash", retry_delay_seconds=0)

    result = asyncio.run(provider.generate(request))

    assert result.reply == "DSML: draft_workout_record"
    assert result.tool_call is None


def test_deepseek_provider_keeps_a_safe_reply_when_unknown_second_round_tool_has_no_content():
    unknown_call = SimpleNamespace(
        id="call-unknown",
        function=SimpleNamespace(name="draft_workout_record", arguments="{}"),
    )
    response = SimpleNamespace(
        id="deepseek-response",
        model="deepseek-v4-flash",
        choices=[SimpleNamespace(message=SimpleNamespace(content=None, tool_calls=[unknown_call]))],
        usage=SimpleNamespace(prompt_tokens=20, completion_tokens=10),
    )
    request = _request().model_copy(
        update={
            "tool_result": ToolExecutionResult(
                call_id="call-read",
                name="get_current_plan",
                output={"plan": "current"},
            ),
            "continuation": ProviderContinuation(
                output_items=[
                    {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call-read",
                                "type": "function",
                                "function": {"name": "get_current_plan", "arguments": "{}"},
                            }
                        ],
                    }
                ]
            ),
        }
    )
    provider = DeepSeekProvider(client=FakeClient(response), model="deepseek-v4-flash", retry_delay_seconds=0)

    result = asyncio.run(provider.generate(request))

    assert result.reply == "已整理出可确认的草稿。"
    assert result.tool_call is None


def test_deepseek_provider_ignores_a_single_unknown_tool_without_content():
    unknown_call = SimpleNamespace(
        id="call-unknown",
        function=SimpleNamespace(name="draft_workout_record", arguments="{}"),
    )
    response = SimpleNamespace(
        id="deepseek-response",
        model="deepseek-v4-flash",
        choices=[SimpleNamespace(message=SimpleNamespace(content=None, tool_calls=[unknown_call]))],
        usage=SimpleNamespace(prompt_tokens=20, completion_tokens=10),
    )
    provider = DeepSeekProvider(client=FakeClient(response), model="deepseek-v4-flash", retry_delay_seconds=0)

    result = asyncio.run(provider.generate(_request()))

    assert result.reply == "已整理出可确认的草稿。"
    assert result.tool_call is None


def test_deepseek_provider_keeps_one_read_tool_when_model_requests_two_reads():
    plan_call = SimpleNamespace(
        id="call-plan",
        function=SimpleNamespace(name="get_current_plan", arguments="{}"),
    )
    today_call = SimpleNamespace(
        id="call-today",
        function=SimpleNamespace(name="get_today_context", arguments="{}"),
    )
    response = SimpleNamespace(
        id="deepseek-response",
        model="deepseek-v4-flash",
        choices=[SimpleNamespace(message=SimpleNamespace(content=None, tool_calls=[plan_call, today_call]))],
        usage=SimpleNamespace(prompt_tokens=20, completion_tokens=10),
    )
    request = _request().model_copy(
        update={
            "tools": [
                AgentToolDefinition(
                    name="get_current_plan",
                    description="Read the current plan.",
                    parameters={"type": "object", "properties": {}, "required": [], "additionalProperties": False},
                ),
                AgentToolDefinition(
                    name="get_today_context",
                    description="Read today's context.",
                    parameters={"type": "object", "properties": {}, "required": [], "additionalProperties": False},
                ),
            ]
        }
    )
    provider = DeepSeekProvider(client=FakeClient(response), model="deepseek-v4-flash", retry_delay_seconds=0)

    result = asyncio.run(provider.generate(request))

    assert result.tool_call.call_id == "call-plan"
    assert result.tool_call.name == "get_current_plan"
