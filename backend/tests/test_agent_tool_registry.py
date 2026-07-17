import pytest

from backend.app.agents.tool_registry import (
    AgentToolContext,
    execute_agent_tool,
    get_agent_tool_definitions,
)
from backend.app.llm.errors import LLMOutputInvalidError
from backend.app.llm.models import ToolCallProposal
from backend.app.services.demo_store import list_workout_logs


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
