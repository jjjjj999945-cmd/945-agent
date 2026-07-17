import asyncio

from backend.app.llm.deterministic import DeterministicProvider
from backend.app.llm.models import AgentModelRequest, ToolExecutionResult
from backend.app.models.domain import RecordDraft


def _request(message: str, locale: str = "zh-CN") -> AgentModelRequest:
    return AgentModelRequest(
        request_id="req-deterministic",
        user_id="demo-user-945",
        locale=locale,
        message=message,
    )


def test_deterministic_provider_preserves_workout_draft_behavior():
    result = asyncio.run(
        DeterministicProvider().generate(
            _request("今天深蹲做了 4 组，每组 8 次，80kg。")
        )
    )

    assert result.intent == "log_workout"
    assert result.record_draft.type == "workout_log"
    assert result.record_draft.requires_confirmation is True
    assert result.provider == "deterministic"
    assert result.usage.http_attempts == 0


def test_deterministic_provider_finalizes_an_executed_draft_tool():
    draft = RecordDraft(
        type="meal_log",
        requires_confirmation=True,
        payload={"meal_name": "鸡胸肉饭", "note": "午饭"},
    )
    request = _request("帮我记录午饭").model_copy(
        update={
            "tool_result": ToolExecutionResult(
                call_id="call-1",
                name="create_meal_log_draft",
                output=draft.model_dump(),
                record_draft=draft,
            )
        }
    )

    result = asyncio.run(DeterministicProvider().generate(request))

    assert result.intent == "log_meal"
    assert result.record_draft == draft
    assert "确认" in result.reply


def test_deterministic_provider_keeps_english_reply_support():
    result = asyncio.run(
        DeterministicProvider().generate(
            _request("What should I focus on today?", locale="en-US")
        )
    )

    assert result.intent == "ask_question"
    assert result.reply.startswith("I read your question")
