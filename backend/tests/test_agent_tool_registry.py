import pytest

from backend.app.agents.tool_registry import (
    AgentToolContext,
    execute_agent_tool,
    get_agent_tool_definitions,
)
from backend.app.llm.errors import LLMOutputInvalidError
from backend.app.llm.models import ToolCallProposal
from backend.app.services.demo_store import list_meal_logs, list_workout_logs
from backend.app.services.plan_service import get_current_plan


def _context() -> AgentToolContext:
    return AgentToolContext(
        user_id="demo-user-945",
        date="2026-07-11",
        locale="zh-CN",
        message="今天深蹲 4 组 8 次 80kg。",
    )


def test_registry_exports_only_the_eight_read_and_draft_tools():
    definitions = get_agent_tool_definitions()

    assert [item.name for item in definitions] == [
        "get_profile",
        "get_today_context",
        "get_current_plan",
        "list_recent_workout_logs",
        "list_recent_meal_logs",
        "create_workout_log_draft",
        "create_meal_log_draft",
        "create_plan_adjustment_draft",
    ]
    assert all(item.to_openai_tool()["strict"] is True for item in definitions)
    assert "accept_advice" not in [item.name for item in definitions]


def test_registry_exports_strict_json_schemas():
    definitions = get_agent_tool_definitions()

    for definition in definitions:
        schema = definition.parameters
        assert schema["additionalProperties"] is False
        assert set(schema.get("required", [])) == set(schema["properties"])

    workout_schema = next(
        item.parameters
        for item in definitions
        if item.name == "create_workout_log_draft"
    )
    weight_schema = workout_schema["properties"]["weight_kg"]
    assert {item["type"] for item in weight_schema["anyOf"]} == {"number", "null"}


def test_registry_builds_workout_draft_without_writing():
    result = execute_agent_tool(
        ToolCallProposal(
            call_id="call-workout",
            name="create_workout_log_draft",
            arguments={
                "exercise_name": "深蹲",
                "sets": 4,
                "reps": 8,
                "weight_kg": 80,
                "effort_note": "感觉很累",
            },
        ),
        _context(),
    )

    assert result.record_draft.type == "workout_log"
    assert result.record_draft.requires_confirmation is True
    assert result.record_draft.payload["weight_kg"] == 80
    assert list_workout_logs("demo-user-945") == []


def test_registry_builds_meal_draft_without_writing():
    result = execute_agent_tool(
        ToolCallProposal(
            call_id="call-meal",
            name="create_meal_log_draft",
            arguments={"meal_name": "午餐", "note": "鸡胸肉饭"},
        ),
        _context(),
    )

    assert result.record_draft.type == "meal_log"
    assert result.record_draft.requires_confirmation is True
    assert result.record_draft.payload["meal_name"] == "午餐"
    assert list_meal_logs("demo-user-945") == []


def test_registry_builds_plan_adjustment_draft_without_writing():
    plan_before = get_current_plan("demo-user-945").model_dump()

    result = execute_agent_tool(
        ToolCallProposal(
            call_id="call-plan",
            name="create_plan_adjustment_draft",
            arguments={
                "adjustment_type": "reduce_intensity",
                "reason": "今天太累",
            },
        ),
        _context(),
    )

    assert result.record_draft.type == "plan_adjustment"
    assert result.record_draft.requires_confirmation is True
    assert result.record_draft.payload["adjustment_type"] == "reduce_intensity"
    assert get_current_plan("demo-user-945").model_dump() == plan_before


def test_registry_rejects_unknown_tool():
    with pytest.raises(LLMOutputInvalidError, match="not allowed"):
        execute_agent_tool(
            ToolCallProposal(call_id="call-bad", name="delete_all_data", arguments={}),
            _context(),
        )


def test_registry_rejects_invalid_workout_arguments():
    with pytest.raises(LLMOutputInvalidError, match="Invalid arguments"):
        execute_agent_tool(
            ToolCallProposal(
                call_id="call-bad-args",
                name="create_workout_log_draft",
                arguments={
                    "exercise_name": "深蹲",
                    "sets": 0,
                    "reps": 8,
                    "weight_kg": 80,
                    "effort_note": "无",
                },
            ),
            _context(),
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [("sets", "4"), ("reps", "8"), ("weight_kg", "80")],
)
def test_registry_rejects_string_encoded_workout_numbers(field, value):
    arguments = {
        "exercise_name": "深蹲",
        "sets": 4,
        "reps": 8,
        "weight_kg": 80,
        "effort_note": "感觉很累",
    }
    arguments[field] = value

    with pytest.raises(LLMOutputInvalidError, match="Invalid arguments"):
        execute_agent_tool(
            ToolCallProposal(
                call_id=f"call-string-{field}",
                name="create_workout_log_draft",
                arguments=arguments,
            ),
            _context(),
        )
