from backend.app.agents.tools import (
    create_meal_log_draft,
    create_plan_adjustment_draft,
    create_workout_log_draft,
    get_today_context,
)
from backend.app.llm.models import AgentIntent
from backend.app.models.domain import AgentMessage, RecordDraft
from backend.app.rag.retriever import KnowledgeChunk, retrieve_knowledge


HIGH_RISK_TERMS = [
    "胸闷",
    "眩晕",
    "晕厥",
    "昏倒",
    "强烈疼痛",
    "剧烈疼痛",
    "呼吸困难",
    "疑似受伤",
    "心脏不适",
    "极端节食",
    "进食障碍",
]


def safety_guard(message: str) -> bool:
    return any(term in message for term in HIGH_RISK_TERMS)


def _looks_like_question(message: str) -> bool:
    normalized = message.lower()
    return any(term in normalized for term in ("?", "？", "怎么", "要点", "技巧", "多少", "是否", "能不能", "what", "how", "why"))


def _looks_like_record(message: str) -> bool:
    normalized = message.lower()
    return any(term in normalized for term in (
        "记录", "做了", "练了", "完成了", "吃了", "刚吃", "我吃", "log", "i did", "i ate", "i had",
    ))


def intent_router(message: str) -> AgentIntent:
    normalized = message.lower()
    if safety_guard(message):
        return "safety_warning"
    if ("深蹲" in normalized or "squat" in normalized) and _looks_like_record(message):
        return "log_workout"
    if _looks_like_record(message) and ("吃" in normalized or "meal" in normalized or "food" in normalized):
        return "log_meal"
    if _looks_like_question(message):
        return "ask_question"
    if "调整" in normalized or "adjust" in normalized:
        return "adjust_plan"
    return "ask_question"


def context_builder(user_id: str, date: str):
    return get_today_context(user_id=user_id, date=date)


def rag_retriever(message: str, locale: str) -> list[KnowledgeChunk]:
    return retrieve_knowledge(message, locale=locale)


def tool_planner(intent: AgentIntent, message: str, locale: str, date: str | None = None) -> RecordDraft | None:
    if intent == "log_workout":
        return create_workout_log_draft(message)
    if intent == "log_meal":
        return create_meal_log_draft(message, locale=locale)
    if intent == "adjust_plan":
        return create_plan_adjustment_draft(message, target_date=date)
    return None


def followup_tool_planner(
    message: str,
    conversation: list[AgentMessage],
    date: str,
) -> RecordDraft | None:
    normalized = message.lower().strip()
    confirmations = ("帮我生成", "生成吧", "生成一下", "go ahead", "create it")
    if not any(term in normalized for term in confirmations):
        return None

    recent = conversation[-4:]
    previous_agent = next((item for item in reversed(recent) if item.role == "agent"), None)
    previous_user = next((item for item in reversed(recent) if item.role == "user"), None)
    if previous_agent is None or previous_user is None:
        return None

    offer = previous_agent.content.lower()
    plan_offer_terms = ("计划调整草稿", "调整草稿", "调整预览", "plan adjustment")
    if not any(term in offer for term in plan_offer_terms):
        return None

    planning_context = f"{previous_user.content}\n{previous_agent.content}"
    return create_plan_adjustment_draft(
        planning_context,
        target_date=date,
        reason=previous_user.content,
    )


def draft_validator(draft: RecordDraft | None) -> RecordDraft | None:
    if draft is None:
        return None
    if draft.requires_confirmation is not True:
        return None
    return draft
