from pydantic import BaseModel, ConfigDict

from backend.app.agents.nodes import (
    context_builder,
    draft_validator,
    intent_router,
    rag_retriever,
    tool_planner,
)
from backend.app.models.domain import RecordDraft, TodayResponseData
from backend.app.rag.retriever import KnowledgeChunk


class AgentGraphResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent: str
    reply: str
    record_draft: RecordDraft | None
    today_context: TodayResponseData | None
    rag_chunks: list[KnowledgeChunk]


def _response_generator(intent: str, locale: str, draft: RecordDraft | None, rag_chunks: list[KnowledgeChunk]) -> str:
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
    if rag_chunks:
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


def run_agent_graph(user_id: str, locale: str, message: str, context: dict | None = None) -> AgentGraphResult:
    date = str((context or {}).get("date", "2026-07-11"))
    intent = intent_router(message)
    today_context = context_builder(user_id, date)
    rag_chunks = [] if intent in ("log_workout", "log_meal") else rag_retriever(message, locale)
    draft = draft_validator(tool_planner(intent, message, locale))
    return AgentGraphResult(
        intent=intent,
        reply=_response_generator(intent, locale, draft, rag_chunks),
        record_draft=draft,
        today_context=today_context,
        rag_chunks=rag_chunks
    )
