from time import perf_counter
from uuid import uuid4

from backend.app.agents.graph import run_agent_graph
from backend.app.llm.errors import LLMError
from backend.app.llm.factory import LLMProviderRouter
from backend.app.models.domain import AgentChatInput, AgentMessage, AgentRetryInput, AgentRun
from backend.app.services.demo_seed import timestamp
from backend.app.services.demo_store import (
    is_demo_user,
    list_agent_runs,
    list_agent_messages,
    save_agent_run,
    save_agent_message,
)


async def create_agent_reply(
    input_data: AgentChatInput,
    *,
    provider_router: LLMProviderRouter | None = None,
    retry_of_agent_run_id: str | None = None,
) -> AgentMessage | None:
    if not is_demo_user(input_data.user_id):
        return None

    existing = list_agent_messages(input_data.user_id) or []
    request_id = uuid4().hex
    started_at = timestamp()
    started_clock = perf_counter()
    try:
        graph_result = await run_agent_graph(
            user_id=input_data.user_id,
            locale=input_data.locale,
            message=input_data.message,
            context=input_data.context,
            conversation=existing[-10:],
            provider_router=provider_router,
            request_id=request_id,
        )
    except LLMError as exc:
        save_agent_run(
            AgentRun(
                agent_run_id=request_id,
                user_id=input_data.user_id,
                status="failed",
                started_at=started_at,
                completed_at=timestamp(),
                duration_ms=round((perf_counter() - started_clock) * 1000, 2),
            error_code=exc.code,
            http_attempts=exc.http_attempts,
                retry_input=AgentRetryInput(
                    message=input_data.message,
                    locale=input_data.locale,
                    context=input_data.context,
                ),
                retry_of_agent_run_id=retry_of_agent_run_id,
            )
        )
        raise
    user_message = AgentMessage(
        message_id=f"msg-user-{uuid4().hex}",
        user_id=input_data.user_id,
        role="user",
        content=input_data.message,
        locale=input_data.locale,
        created_at=timestamp(),
    )
    agent_message = AgentMessage(
        message_id=f"msg-agent-{uuid4().hex}",
        user_id=input_data.user_id,
        role="agent",
        content=graph_result.reply,
        locale=input_data.locale,
        record_draft=graph_result.record_draft,
        created_at=timestamp(),
    )
    save_agent_message(user_message)
    save_agent_message(agent_message)
    save_agent_run(
        AgentRun(
            agent_run_id=request_id,
            user_id=input_data.user_id,
            status="completed",
            started_at=started_at,
            completed_at=timestamp(),
            duration_ms=round((perf_counter() - started_clock) * 1000, 2),
            provider=graph_result.provider,
            model=graph_result.model,
            intent=graph_result.intent,
            draft_type=(graph_result.record_draft.type if graph_result.record_draft else None),
            degraded=graph_result.degraded,
            degraded_reason=graph_result.degraded_reason,
            input_tokens=graph_result.usage.input_tokens,
            output_tokens=graph_result.usage.output_tokens,
            logical_generations=graph_result.usage.logical_generations,
            http_attempts=graph_result.usage.http_attempts,
            retry_of_agent_run_id=retry_of_agent_run_id,
        )
    )
    return agent_message


async def retry_agent_run(
    user_id: str,
    agent_run_id: str,
    *,
    provider_router: LLMProviderRouter | None = None,
) -> AgentMessage | None:
    runs = list_agent_runs(user_id) or []
    failed_run = next((run for run in runs if run.agent_run_id == agent_run_id), None)
    if failed_run is None or failed_run.status != "failed" or failed_run.retry_input is None:
        return None
    return await create_agent_reply(
        AgentChatInput(
            user_id=user_id,
            locale=failed_run.retry_input.locale,
            message=failed_run.retry_input.message,
            context=failed_run.retry_input.context,
        ),
        provider_router=provider_router,
        retry_of_agent_run_id=agent_run_id,
    )
