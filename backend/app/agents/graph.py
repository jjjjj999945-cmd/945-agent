from functools import lru_cache
from typing import Any, TypedDict
from uuid import uuid4

from langgraph.graph import END, START, StateGraph
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, ConfigDict, Field

from backend.app.agents.nodes import context_builder, draft_validator, followup_tool_planner, intent_router, rag_retriever, safety_guard, tool_planner
from backend.app.agents.checkpoint import get_agent_checkpointer
from backend.app.agents.tool_registry import AgentToolContext, execute_agent_tool, get_agent_tool_definitions
from backend.app.core.config import get_settings
from backend.app.data.demo_data import TODAY_DATE
from backend.app.llm.errors import LLMOutputInvalidError
from backend.app.llm.factory import LLMProviderRouter, get_llm_provider_router
from backend.app.llm.models import AgentModelRequest, AgentModelResponse, ConversationMessage, ProviderUsage
from backend.app.models.domain import AgentMessage, AgentTraceStep, RecordDraft, TodayResponseData
from backend.app.observability.langsmith import agent_trace_metadata, configure_langsmith_tracing
from backend.app.rag.retriever import KnowledgeChunk
from backend.app.services.agent_run_lease import (
    AgentLeaseLostError,
    AgentLeaseToken,
    lease_config,
    lease_token_from_config,
)
from backend.app.services.demo_store import agent_run_lease_is_valid
from backend.app.services.memory_service import list_user_memory_summaries


class AgentCheckpointMissingError(Exception):
    pass


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
    trace_steps: list[AgentTraceStep] = Field(default_factory=list)


class AgentWorkflowState(TypedDict, total=False):
    user_id: str
    locale: str
    message: str
    context: dict[str, Any]
    conversation: list[AgentMessage]
    request_id: str
    date: str
    today_context: TodayResponseData
    rag_chunks: list[KnowledgeChunk]
    memory: list[dict[str, Any]]
    request: AgentModelRequest
    first: AgentModelResponse
    final: AgentModelResponse
    draft: RecordDraft | None
    resolved_intent: str
    tool_status: str
    tool_metadata: dict[str, str | int | float | bool]
    result: AgentGraphResult


def _assert_graph_lease(config: RunnableConfig) -> None:
    token = lease_token_from_config(config)
    if token is not None and not agent_run_lease_is_valid(token):
        raise AgentLeaseLostError(token.agent_run_id)


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


def _without_dsml_tool_markup(reply: str, locale: str) -> str:
    cleaned = "\n".join(line for line in reply.splitlines() if "DSML" not in line).strip()
    if cleaned:
        return cleaned
    return "已生成可确认的草稿，请确认后保存。" if locale == "zh-CN" else "I created a confirmation-required draft. Please review it before saving."


async def _safety_node(
    state: AgentWorkflowState,
    config: RunnableConfig,
) -> dict[str, Any]:
    _assert_graph_lease(config)
    if not safety_guard(state["message"]):
        output = {"date": str(state["context"].get("date", TODAY_DATE))}
    else:
        output = {
            "result": AgentGraphResult(
                intent="safety_warning",
                reply=_safety_reply(state["locale"]),
                record_draft=None,
                today_context=None,
                rag_chunks=[],
                provider="local_safety",
                trace_steps=[
                    AgentTraceStep(
                        name="safety_guard",
                        status="completed",
                        metadata={"risk_detected": True},
                    )
                ],
            )
        }
    _assert_graph_lease(config)
    return output


def _after_safety(state: AgentWorkflowState) -> str:
    return "finalize" if "result" in state else "context"


async def _context_node(
    state: AgentWorkflowState,
    config: RunnableConfig,
) -> dict[str, Any]:
    _assert_graph_lease(config)
    today_context = context_builder(state["user_id"], state["date"])
    rag_chunks = rag_retriever(state["message"], state["locale"])
    memory = [
        summary.model_dump(mode="json")
        for summary in list_user_memory_summaries(state["user_id"])[-4:]
    ]
    request_context = dict(state["context"])
    request_context["memory_summaries"] = memory
    output = {
        "today_context": today_context,
        "rag_chunks": rag_chunks,
        "memory": memory,
        "request": AgentModelRequest(
            request_id=state["request_id"],
            user_id=state["user_id"],
            locale=state["locale"],
            message=state["message"],
            context=request_context,
            conversation=_conversation(state["conversation"]),
            today_context=today_context,
            rag_chunks=[chunk.model_dump(mode="json") for chunk in rag_chunks],
            tools=get_agent_tool_definitions(),
        ),
    }
    _assert_graph_lease(config)
    return output


async def _model_node(state: AgentWorkflowState, config: RunnableConfig) -> dict[str, Any]:
    _assert_graph_lease(config)
    router = config["configurable"].get("provider_router") or get_llm_provider_router()
    request = state["request"]
    first = await router.generate(request)
    final = first
    draft = draft_validator(first.record_draft)
    resolved_intent = first.intent
    tool_status = "skipped"
    tool_metadata: dict[str, str | int | float | bool] = {}

    if first.tool_call is not None:
        tool_metadata = {"tool": first.tool_call.name}
        try:
            tool_result = execute_agent_tool(
                first.tool_call,
                AgentToolContext(
                    user_id=state["user_id"],
                    date=state["date"],
                    locale=state["locale"],
                    message=state["message"],
                ),
            )
        except LLMOutputInvalidError as exc:
            final = await router.recover(request, exc.attach_request_id(state["request_id"]))
            draft = draft_validator(final.record_draft)
            tool_status = "failed"
        else:
            final = await router.generate(
                request.model_copy(
                    update={"continuation": first.continuation, "tool_result": tool_result}
                )
            )
            draft = draft_validator(tool_result.record_draft or final.record_draft)
            tool_status = "completed"

    # Some compatible model providers answer a clear record request in prose
    # instead of emitting a tool call. Keep the confirmation boundary intact by
    # producing only a local draft from the same constrained parser.
    if draft is None:
        local_intent = intent_router(state["message"])
        local_draft = draft_validator(
            followup_tool_planner(state["message"], state["conversation"], state["date"])
        )
        if local_draft is not None:
            local_intent = "adjust_plan"
        else:
            local_draft = draft_validator(
                tool_planner(local_intent, state["message"], state["locale"], state["date"])
            )
        if local_draft is not None:
            draft = local_draft
            resolved_intent = local_intent
            tool_status = "completed"
            tool_metadata["draft_source"] = "intent_fallback"
            final = final.model_copy(
                update={"reply": _without_dsml_tool_markup(final.reply, state["locale"])}
            )

    output = {
        "first": first,
        "final": final,
        "draft": draft,
        "resolved_intent": resolved_intent,
        "tool_status": tool_status,
        "tool_metadata": tool_metadata,
    }
    _assert_graph_lease(config)
    return output


async def _finalize_node(
    state: AgentWorkflowState,
    config: RunnableConfig,
) -> dict[str, Any]:
    _assert_graph_lease(config)
    if "result" in state:
        _assert_graph_lease(config)
        return {}
    first = state["first"]
    final = state["final"]
    draft = state["draft"]
    output = {
        "result": AgentGraphResult(
            intent=state["resolved_intent"],
            reply=final.reply or first.reply,
            record_draft=draft,
            today_context=state["today_context"],
            rag_chunks=state["rag_chunks"],
            provider=final.provider,
            model=final.model,
            degraded=first.degraded or final.degraded,
            degraded_reason=final.degraded_reason or first.degraded_reason,
            usage=_sum_usage(first.usage, final.usage if final is not first else None),
            trace_steps=[
                AgentTraceStep(name="safety_guard", status="completed", metadata={"risk_detected": False}),
                AgentTraceStep(name="context_builder", status="completed", metadata={"available": True}),
                AgentTraceStep(name="rag_retriever", status="completed", metadata={"chunk_count": len(state["rag_chunks"])}),
                AgentTraceStep(name="memory_context", status="completed", metadata={"summary_count": len(state["memory"])}),
                AgentTraceStep(name="model_generation", status="completed", metadata={"intent": first.intent}),
                AgentTraceStep(name="tool_execution", status=state["tool_status"], metadata=state["tool_metadata"]),
                AgentTraceStep(name="draft_validator", status="completed", metadata={"requires_confirmation": draft is not None}),
            ],
        )
    }
    _assert_graph_lease(config)
    return output


@lru_cache
def get_agent_graph():
    configure_langsmith_tracing(get_settings())
    workflow = StateGraph(AgentWorkflowState)
    workflow.add_node("safety", _safety_node)
    workflow.add_node("context", _context_node)
    workflow.add_node("model", _model_node)
    workflow.add_node("finalize", _finalize_node)
    workflow.add_edge(START, "safety")
    workflow.add_conditional_edges("safety", _after_safety, {"context": "context", "finalize": "finalize"})
    workflow.add_edge("context", "model")
    workflow.add_edge("model", "finalize")
    workflow.add_edge("finalize", END)
    return workflow.compile(checkpointer=get_agent_checkpointer())


async def run_agent_graph(
    user_id: str,
    locale: str,
    message: str,
    context: dict | None = None,
    *,
    conversation: list[AgentMessage] | None = None,
    provider_router: LLMProviderRouter | None = None,
    request_id: str | None = None,
    lease_token: AgentLeaseToken | None = None,
) -> AgentGraphResult:
    request_id = request_id or uuid4().hex
    settings = get_settings()
    configurable: dict[str, Any] = {
        "thread_id": request_id,
        "provider_router": provider_router,
    }
    if lease_token is not None:
        configurable.update(lease_config(lease_token))
    state = await get_agent_graph().ainvoke(
        {
            "user_id": user_id,
            "locale": locale,
            "message": message,
            "context": dict(context or {}),
            "conversation": conversation or [],
            "request_id": request_id,
        },
        config={
            "configurable": configurable,
            "metadata": agent_trace_metadata(
                request_id=request_id,
                user_id=user_id,
                locale=locale,
                provider=settings.llm_provider,
            ),
        },
    )
    return state["result"]


def get_safe_resume_checkpoint_id(
    request_id: str,
    before_version: int,
) -> str | None:
    config = {"configurable": {"thread_id": request_id}}
    for saved in get_agent_checkpointer().list(config):
        metadata = saved.metadata or {}
        if int(metadata.get("lease_version", 0)) > before_version:
            continue
        checkpoint_id = saved.config.get("configurable", {}).get("checkpoint_id")
        if checkpoint_id is not None:
            return str(checkpoint_id)
    return None


def load_completed_agent_graph_result(
    request_id: str,
    lease_version: int,
) -> AgentGraphResult | None:
    config = {"configurable": {"thread_id": request_id}}
    for saved in get_agent_checkpointer().list(config):
        metadata = saved.metadata or {}
        if int(metadata.get("lease_version", 0)) != lease_version:
            continue
        result = saved.checkpoint.get("channel_values", {}).get("result")
        if result is not None:
            return AgentGraphResult.model_validate(result)
    return None


async def resume_agent_graph(
    request_id: str,
    *,
    checkpoint_id: str,
    lease_token: AgentLeaseToken,
    provider_router: LLMProviderRouter | None = None,
) -> AgentGraphResult:
    graph = get_agent_graph()
    configurable = {
        "thread_id": request_id,
        "checkpoint_ns": "",
        "checkpoint_id": checkpoint_id,
        "provider_router": provider_router,
        **lease_config(lease_token),
    }
    snapshot = graph.get_state({"configurable": configurable})
    values = dict(snapshot.values or {})
    saved_result = values.get("result")
    if saved_result is not None:
        await graph.aupdate_state(
            {"configurable": configurable},
            {"result": saved_result},
        )
        return AgentGraphResult.model_validate(saved_result)
    if not values or not snapshot.next:
        raise AgentCheckpointMissingError(request_id)

    user_id = str(values["user_id"])
    locale = str(values["locale"])
    settings = get_settings()
    state = await graph.ainvoke(
        None,
        config={
            "configurable": configurable,
            "metadata": agent_trace_metadata(
                request_id=request_id,
                user_id=user_id,
                locale=locale,
                provider=settings.llm_provider,
            ),
        },
    )
    result = state.get("result")
    if result is None:
        raise AgentCheckpointMissingError(request_id)
    return AgentGraphResult.model_validate(result)
