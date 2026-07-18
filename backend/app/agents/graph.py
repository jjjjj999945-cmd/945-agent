from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from backend.app.agents.nodes import context_builder, draft_validator, rag_retriever, safety_guard
from backend.app.agents.tool_registry import (
    AgentToolContext,
    execute_agent_tool,
    get_agent_tool_definitions,
)
from backend.app.llm.errors import LLMOutputInvalidError
from backend.app.llm.factory import LLMProviderRouter, get_llm_provider_router
from backend.app.llm.models import AgentModelRequest, ConversationMessage, ProviderUsage
from backend.app.models.domain import AgentMessage, RecordDraft, TodayResponseData
from backend.app.rag.retriever import KnowledgeChunk
from backend.app.services.memory_service import list_user_memory_summaries


class AgentGraphResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent: str
    reply: str
    record_draft: RecordDraft | None
    today_context: TodayResponseData | None
    rag_chunks: list[KnowledgeChunk]
    provider: str
    model: str | None = None
    degraded: bool = False
    degraded_reason: str | None = None
    usage: ProviderUsage = Field(default_factory=ProviderUsage)


def _safety_reply(locale: str) -> str:
    return (
        "你提到了可能的高风险身体信号。请先暂停训练，不要继续冲重量，并尽快咨询医生或合格专业人士。"
        if locale == "zh-CN"
        else "You mentioned possible high-risk symptoms. Stop training for now and consult a qualified professional."
    )


def _conversation(messages: list[AgentMessage]) -> list[ConversationMessage]:
    return [
        ConversationMessage(
            role="assistant" if message.role == "agent" else "user",
            content=message.content,
        )
        for message in messages[-10:]
    ]


def _sum_usage(first: ProviderUsage, second: ProviderUsage | None = None) -> ProviderUsage:
    second = second or ProviderUsage()
    return ProviderUsage(
        input_tokens=first.input_tokens + second.input_tokens,
        output_tokens=first.output_tokens + second.output_tokens,
        logical_generations=first.logical_generations + second.logical_generations,
        http_attempts=first.http_attempts + second.http_attempts,
    )


async def run_agent_graph(
    user_id: str,
    locale: str,
    message: str,
    context: dict | None = None,
    *,
    conversation: list[AgentMessage] | None = None,
    provider_router: LLMProviderRouter | None = None,
    request_id: str | None = None,
) -> AgentGraphResult:
    request_id = request_id or uuid4().hex
    date = str((context or {}).get("date", "2026-07-11"))

    if safety_guard(message):
        return AgentGraphResult(
            intent="safety_warning",
            reply=_safety_reply(locale),
            record_draft=None,
            today_context=None,
            rag_chunks=[],
            provider="local_safety",
        )

    today_context = context_builder(user_id, date)
    rag_chunks = rag_retriever(message, locale)
    memory = [
        summary.model_dump(mode="json")
        for summary in list_user_memory_summaries(user_id)[-4:]
    ]
    request_context = dict(context or {})
    request_context["memory_summaries"] = memory
    request = AgentModelRequest(
        request_id=request_id,
        user_id=user_id,
        locale=locale,
        message=message,
        context=request_context,
        conversation=_conversation(conversation or []),
        today_context=today_context,
        rag_chunks=[chunk.model_dump(mode="json") for chunk in rag_chunks],
        tools=get_agent_tool_definitions(),
    )
    router = provider_router or get_llm_provider_router()
    first = await router.generate(request)
    final = first
    draft = draft_validator(first.record_draft)

    if first.tool_call is not None:
        try:
            tool_result = execute_agent_tool(
                first.tool_call,
                AgentToolContext(
                    user_id=user_id,
                    date=date,
                    locale=locale,
                    message=message,
                ),
            )
        except LLMOutputInvalidError as exc:
            final = await router.recover(request, exc.attach_request_id(request_id))
            draft = draft_validator(final.record_draft)
        else:
            final_request = request.model_copy(
                update={
                    "continuation": first.continuation,
                    "tool_result": tool_result,
                }
            )
            final = await router.generate(final_request)
            draft = draft_validator(tool_result.record_draft or final.record_draft)

    return AgentGraphResult(
        intent=first.intent,
        reply=final.reply or first.reply,
        record_draft=draft,
        today_context=today_context,
        rag_chunks=rag_chunks,
        provider=final.provider,
        model=final.model,
        degraded=first.degraded or final.degraded,
        degraded_reason=final.degraded_reason or first.degraded_reason,
        usage=_sum_usage(first.usage, final.usage if final is not first else None),
    )
