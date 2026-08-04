from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from backend.app.agents.tools import (
    build_meal_log_draft,
    build_plan_adjustment_draft,
    build_workout_log_draft,
    get_current_plan_tool,
    get_profile_tool,
    get_today_context,
    list_recent_meal_logs,
    list_recent_workout_logs,
)
from backend.app.llm.errors import LLMOutputInvalidError
from backend.app.llm.models import AgentToolDefinition, ToolCallProposal, ToolExecutionResult
from backend.app.models.domain import Locale, RecordDraft


class ToolArguments(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class EmptyArguments(ToolArguments):
    pass


class WorkoutDraftArguments(ToolArguments):
    exercise_name: str = Field(min_length=1, max_length=100)
    sets: int = Field(ge=1, le=20)
    reps: int = Field(ge=1, le=100)
    weight_kg: float | None = Field(ge=0, le=1000)
    effort_note: str = Field(min_length=1, max_length=500)


class MealDraftArguments(ToolArguments):
    meal_name: str = Field(min_length=1, max_length=100)
    note: str = Field(min_length=1, max_length=500)


class PlanAdjustmentArguments(ToolArguments):
    adjustment_type: Literal[
        "reduce_intensity",
        "increase_intensity",
        "change_schedule",
        "swap_exercise",
        "skip_workout",
        "swap_meal",
        "adjust_nutrition",
    ]
    reason: str = Field(min_length=1, max_length=500)
    target_date: str | None = None
    target_exercise_id: str | None = None
    target_meal_id: str | None = None
    replacement_name: str | None = Field(default=None, min_length=1, max_length=100)


class AgentToolContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str
    date: str
    locale: Locale
    message: str


TOOL_ARGUMENT_MODELS: dict[str, type[ToolArguments]] = {
    "get_profile": EmptyArguments,
    "get_today_context": EmptyArguments,
    "get_current_plan": EmptyArguments,
    "list_recent_workout_logs": EmptyArguments,
    "list_recent_meal_logs": EmptyArguments,
    "create_workout_log_draft": WorkoutDraftArguments,
    "create_meal_log_draft": MealDraftArguments,
    "create_plan_adjustment_draft": PlanAdjustmentArguments,
}


TOOL_DESCRIPTIONS = {
    "get_profile": "Read the current user's fitness profile.",
    "get_today_context": "Read today's plan, check-in, progress, and advice.",
    "get_current_plan": "Read the current active workout and meal plan.",
    "list_recent_workout_logs": "Read the latest ten workout logs.",
    "list_recent_meal_logs": "Read the latest ten meal logs.",
    "create_workout_log_draft": "Create a workout log preview that requires user confirmation and does not save data.",
    "create_meal_log_draft": "Create a meal log preview that requires user confirmation and does not save data.",
    "create_plan_adjustment_draft": "Create a plan adjustment preview that requires user confirmation and does not modify the plan.",
}


def get_agent_tool_definitions() -> list[AgentToolDefinition]:
    definitions = []
    for name, model_type in TOOL_ARGUMENT_MODELS.items():
        schema = model_type.model_json_schema()
        # OpenAI strict function tools require every property to be listed as required;
        # nullable fields carry the "not provided" meaning as null.
        schema["required"] = list(schema["properties"])
        definitions.append(AgentToolDefinition(
            name=name,
            description=TOOL_DESCRIPTIONS[name],
            parameters=schema,
        ))
    return definitions


def _serialize(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    if value is None:
        return {"found": False}
    return value


def _result(
    proposal: ToolCallProposal,
    output: Any,
    draft: RecordDraft | None = None,
) -> ToolExecutionResult:
    return ToolExecutionResult(
        call_id=proposal.call_id,
        name=proposal.name,
        output=_serialize(output),
        record_draft=draft,
    )


def execute_agent_tool(
    proposal: ToolCallProposal,
    context: AgentToolContext,
) -> ToolExecutionResult:
    argument_model = TOOL_ARGUMENT_MODELS.get(proposal.name)
    if argument_model is None:
        raise LLMOutputInvalidError(f"Tool '{proposal.name}' is not allowed.")
    try:
        arguments = argument_model.model_validate(proposal.arguments)
    except ValidationError as exc:
        raise LLMOutputInvalidError(
            f"Invalid arguments for tool '{proposal.name}'."
        ) from exc

    if proposal.name == "get_profile":
        return _result(proposal, get_profile_tool(context.user_id))
    if proposal.name == "get_today_context":
        return _result(proposal, get_today_context(context.user_id, context.date))
    if proposal.name == "get_current_plan":
        return _result(proposal, get_current_plan_tool(context.user_id))
    if proposal.name == "list_recent_workout_logs":
        return _result(proposal, list_recent_workout_logs(context.user_id, limit=10))
    if proposal.name == "list_recent_meal_logs":
        return _result(proposal, list_recent_meal_logs(context.user_id, limit=10))
    if proposal.name == "create_workout_log_draft":
        draft = build_workout_log_draft(**arguments.model_dump())
        return _result(proposal, draft, draft)
    if proposal.name == "create_meal_log_draft":
        draft = build_meal_log_draft(**arguments.model_dump())
        return _result(proposal, draft, draft)
    if proposal.name == "create_plan_adjustment_draft":
        draft = build_plan_adjustment_draft(**arguments.model_dump())
        return _result(proposal, draft, draft)
    raise LLMOutputInvalidError(f"Tool '{proposal.name}' is not allowed.")
