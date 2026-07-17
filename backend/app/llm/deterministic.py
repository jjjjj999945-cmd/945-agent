from backend.app.agents.nodes import draft_validator, intent_router, tool_planner
from backend.app.llm.models import AgentModelRequest, AgentModelResponse, ProviderUsage
from backend.app.models.domain import RecordDraft


def _intent_for_draft(draft: RecordDraft | None) -> str:
    if draft is None:
        return "ask_question"
    return {
        "workout_log": "log_workout",
        "meal_log": "log_meal",
        "plan_adjustment": "adjust_plan",
        "daily_checkin": "ask_question",
    }[draft.type]


def _reply(intent: str, locale: str, draft: RecordDraft | None, has_rag: bool) -> str:
    if intent == "safety_warning":
        return (
            "你提到了可能的高风险身体信号。请先暂停训练，不要继续冲重量，并尽快咨询医生或合格专业人士。"
            if locale == "zh-CN"
            else "You mentioned possible high-risk symptoms. Stop training for now and consult a qualified professional."
        )
    if draft is not None:
        return (
            "我可以帮你整理成记录草稿。保存前请先确认。"
            if locale == "zh-CN"
            else "I can turn that into a record draft. Please confirm before saving."
        )
    if has_rag:
        return (
            "我会结合结构化记录和知识库回答。以下建议来自结构化记录与本地 RAG 知识片段。"
            if locale == "zh-CN"
            else "I will answer using structured records plus local RAG knowledge."
        )
    return (
        "我已读取你的问题。当前 demo 会优先基于今日计划、记录和建议回答。"
        if locale == "zh-CN"
        else "I read your question. This demo answers from today's plan, logs, and advice first."
    )


class DeterministicProvider:
    name = "deterministic"

    async def generate(self, request: AgentModelRequest) -> AgentModelResponse:
        if request.tool_result is not None:
            draft = draft_validator(request.tool_result.record_draft)
            intent = _intent_for_draft(draft)
        else:
            intent = intent_router(request.message)
            draft = draft_validator(tool_planner(intent, request.message, request.locale))

        return AgentModelResponse(
            intent=intent,
            reply=_reply(intent, request.locale, draft, bool(request.rag_chunks)),
            record_draft=draft,
            provider=self.name,
            model="rules-v1",
            usage=ProviderUsage(logical_generations=1, http_attempts=0),
        )
