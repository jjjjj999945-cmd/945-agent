from backend.app.llm.models import (
    AgentModelResponse,
    AgentToolDefinition,
    ProviderContinuation,
    ProviderUsage,
    ToolCallProposal,
)


def test_tool_definition_exports_strict_responses_schema():
    definition = AgentToolDefinition(
        name="get_profile",
        description="Read the current user profile.",
        parameters={
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
    )

    assert definition.to_openai_tool() == {
        "type": "function",
        "name": "get_profile",
        "description": "Read the current user profile.",
        "parameters": definition.parameters,
        "strict": True,
    }


def test_provider_continuation_is_not_serialized_to_api_payloads():
    response = AgentModelResponse(
        intent="ask_question",
        reply="ok",
        provider="openai",
        model="configured-model",
        provider_request_id="resp-1",
        usage=ProviderUsage(input_tokens=10, output_tokens=5, logical_generations=1, http_attempts=1),
        continuation=ProviderContinuation(output_items=[{"type": "message", "id": "msg-1"}]),
    )

    assert response.continuation is not None
    assert "continuation" not in response.model_dump()


def test_tool_call_requires_a_call_id_name_and_object_arguments():
    proposal = ToolCallProposal(
        call_id="call-1",
        name="create_workout_log_draft",
        arguments={"exercise_name": "娣辫共"},
    )

    assert proposal.call_id == "call-1"
    assert proposal.arguments == {"exercise_name": "娣辫共"}
