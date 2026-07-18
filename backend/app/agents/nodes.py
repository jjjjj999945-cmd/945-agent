from backend.app.agents.tools import (
    create_meal_log_draft,
    create_plan_adjustment_draft,
    create_workout_log_draft,
    get_today_context,
)
from backend.app.llm.models import AgentIntent
from backend.app.models.domain import RecordDraft
from backend.app.rag.retriever import KnowledgeChunk, retrieve_knowledge


HIGH_RISK_TERMS = ["胸闷", "眩晕", "晕厥", "强烈疼痛", "疑似受伤", "心脏不适", "极端节食", "进食障碍"]


def safety_guard(message: str) -> bool:
    return any(term in message for term in HIGH_RISK_TERMS)


def intent_router(message: str) -> AgentIntent:
    normalized = message.lower()
    if safety_guard(message):
        return "safety_warning"
    if "深蹲" in normalized or "squat" in normalized:
        if "做了" in normalized or "today" in normalized:
            return "log_workout"
        return "ask_question"
    if "吃" in normalized or "meal" in normalized or "food" in normalized:
        return "log_meal"
    if "调整" in normalized or "adjust" in normalized:
        return "adjust_plan"
    return "ask_question"


def context_builder(user_id: str, date: str):
    return get_today_context(user_id=user_id, date=date)


def rag_retriever(message: str, locale: str) -> list[KnowledgeChunk]:
    return retrieve_knowledge(message, locale=locale)


def tool_planner(intent: AgentIntent, message: str, locale: str) -> RecordDraft | None:
    if intent == "log_workout":
        return create_workout_log_draft(message)
    if intent == "log_meal":
        return create_meal_log_draft(message, locale=locale)
    if intent == "adjust_plan":
        return create_plan_adjustment_draft(message)
    return None


def draft_validator(draft: RecordDraft | None) -> RecordDraft | None:
    if draft is None:
        return None
    if draft.requires_confirmation is not True:
        return None
    return draft
