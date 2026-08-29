import asyncio
from datetime import UTC, datetime, timedelta
from time import perf_counter
from uuid import uuid4

from backend.app.agents.graph import (
    AgentCheckpointMissingError,
    AgentGraphResult,
    get_safe_resume_checkpoint_id,
    load_completed_agent_graph_result,
    resume_agent_graph,
    run_agent_graph,
)
from backend.app.core.config import get_settings
from backend.app.llm.errors import AgentUsageLimitError, LLMError
from backend.app.llm.factory import LLMProviderRouter
from backend.app.models.domain import (
    AgentChatInput,
    AgentMessage,
    AgentRetryInput,
    AgentRun,
    AgentTraceStep,
)
from backend.app.services.demo_seed import timestamp
from backend.app.services.demo_store import (
    acquire_agent_run_lease,
    create_agent_run_with_lease,
    interrupt_expired_agent_runs,
    is_demo_user,
    list_agent_messages,
    list_agent_runs,
    mark_agent_run_messages_persisted,
    save_agent_message,
    set_agent_run_resume_checkpoint,
    transition_agent_run_with_lease,
)
from backend.app.services.agent_run_lease import (
    AgentLeaseLostError,
    AgentLeaseSession,
    AgentLeaseToken,
    lease_token_from_run,
    new_lease_owner,
)


class AgentRunExecutionError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 409) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class AgentRunResumeError(AgentRunExecutionError):
    pass


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def list_user_agent_runs(user_id: str) -> list[AgentRun] | None:
    interrupt_expired_agent_runs(user_id)
    return list_agent_runs(user_id)


def _enforce_agent_run_limit(
    user_id: str,
    exclude_run_id: str | None = None,
) -> None:
    settings = get_settings()
    runs = list_agent_runs(user_id) or []

    max_runs = settings.agent_max_runs_per_hour
    if max_runs > 0:
        threshold = datetime.now(UTC) - timedelta(hours=1)
        recent_runs = [
            run
            for run in runs
            if run.agent_run_id != exclude_run_id
            and _parse_timestamp(run.started_at) >= threshold
        ]
        if len(recent_runs) >= max_runs:
            raise AgentUsageLimitError(
                "The hourly Agent usage limit has been reached.",
                http_attempts=0,
            )

    max_tokens = settings.agent_max_tokens_per_day
    day_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    if max_tokens > 0:
        tokens_used = sum(
            run.input_tokens + run.output_tokens
            for run in runs
            if _parse_timestamp(run.started_at) >= day_start
        )
        if tokens_used >= max_tokens:
            raise AgentUsageLimitError(
                "The daily Agent token usage limit has been reached.",
                http_attempts=0,
            )

    max_generations = settings.agent_max_logical_generations_per_day
    if max_generations <= 0:
        return
    generations_used = sum(
        run.logical_generations
        for run in runs
        if _parse_timestamp(run.started_at) >= day_start
    )
    if generations_used >= max_generations:
        raise AgentUsageLimitError(
            "The daily Agent generation usage limit has been reached.",
            http_attempts=0,
        )


def _request_input(input_data: AgentChatInput) -> AgentRetryInput:
    return AgentRetryInput(
        message=input_data.message,
        locale=input_data.locale,
        context=input_data.context,
    )


def _elapsed_duration(run: AgentRun, started_clock: float) -> float:
    return round(run.duration_ms + (perf_counter() - started_clock) * 1000, 2)


def _messages_for_result(
    run: AgentRun,
    input_data: AgentChatInput,
    graph_result: AgentGraphResult,
    created_at: str,
) -> tuple[AgentMessage, AgentMessage]:
    user_message = AgentMessage(
        message_id=f"msg-user-{run.agent_run_id}",
        user_id=input_data.user_id,
        role="user",
        content=input_data.message,
        locale=input_data.locale,
        created_at=created_at,
    )
    agent_message = AgentMessage(
        message_id=f"msg-agent-{run.agent_run_id}",
        user_id=input_data.user_id,
        role="agent",
        content=graph_result.reply,
        locale=input_data.locale,
        record_draft=graph_result.record_draft,
        created_at=created_at,
    )
    return user_message, agent_message


def _complete_agent_run(
    run: AgentRun,
    token: AgentLeaseToken,
    input_data: AgentChatInput,
    graph_result: AgentGraphResult,
    started_clock: float,
) -> AgentMessage | None:
    completed_at = timestamp()
    completed = transition_agent_run_with_lease(
        token,
        run.model_copy(
            update={
                "status": "completed",
                "updated_at": completed_at,
                "completed_at": completed_at,
                "messages_persisted": False,
                "duration_ms": _elapsed_duration(run, started_clock),
                "provider": graph_result.provider,
                "model": graph_result.model,
                "intent": graph_result.intent,
                "draft_type": (
                    graph_result.record_draft.type
                    if graph_result.record_draft is not None
                    else None
                ),
                "degraded": graph_result.degraded,
                "degraded_reason": graph_result.degraded_reason,
                "error_code": None,
                "input_tokens": graph_result.usage.input_tokens,
                "output_tokens": graph_result.usage.output_tokens,
                "logical_generations": graph_result.usage.logical_generations,
                "http_attempts": graph_result.usage.http_attempts,
                "trace_steps": graph_result.trace_steps,
            }
        ),
    )
    if completed is None:
        return None

    user_message, agent_message = _messages_for_result(
        completed,
        input_data,
        graph_result,
        completed_at,
    )
    try:
        save_agent_message(user_message)
        save_agent_message(agent_message)
        mark_agent_run_messages_persisted(
            completed.user_id,
            completed.agent_run_id,
            completed.lease_version,
        )
    except Exception:
        # The completed run remains authoritative; message reads repair this turn.
        pass
    return agent_message


def _fail_agent_run(
    run: AgentRun,
    token: AgentLeaseToken,
    input_data: AgentChatInput,
    exc: LLMError,
    started_clock: float,
) -> AgentRun:
    completed_at = timestamp()
    failed = transition_agent_run_with_lease(
        token,
        run.model_copy(
            update={
                "status": "failed",
                "updated_at": completed_at,
                "completed_at": completed_at,
                "duration_ms": _elapsed_duration(run, started_clock),
                "error_code": exc.code,
                "http_attempts": exc.http_attempts,
                "retry_input": _request_input(input_data),
                "trace_steps": [
                    AgentTraceStep(
                        name="model_generation",
                        status="failed",
                        metadata={"error_code": exc.code},
                    )
                ],
            }
        ),
    )
    if failed is None:
        raise AgentLeaseLostError(run.agent_run_id)
    return failed


def _interrupt_agent_run(
    run: AgentRun,
    token: AgentLeaseToken,
    started_clock: float,
) -> AgentRun:
    interrupted = transition_agent_run_with_lease(
        token,
        run.model_copy(
            update={
                "status": "interrupted",
                "updated_at": timestamp(),
                "completed_at": None,
                "duration_ms": _elapsed_duration(run, started_clock),
            }
        ),
    )
    if interrupted is None:
        raise AgentLeaseLostError(run.agent_run_id)
    return interrupted


def list_user_agent_messages(user_id: str) -> list[AgentMessage] | None:
    runs = list_agent_runs(user_id)
    if runs is None:
        return None

    for run in runs:
        if run.status != "completed" or run.messages_persisted:
            continue
        graph_result = load_completed_agent_graph_result(
            run.agent_run_id,
            run.lease_version,
        )
        if graph_result is None or run.request_input is None:
            continue
        input_data = AgentChatInput(
            user_id=run.user_id,
            locale=run.request_input.locale,
            message=run.request_input.message,
            context=run.request_input.context,
        )
        created_at = run.completed_at or run.updated_at or run.started_at
        user_message, agent_message = _messages_for_result(
            run,
            input_data,
            graph_result,
            created_at,
        )
        save_agent_message(user_message)
        save_agent_message(agent_message)
        mark_agent_run_messages_persisted(
            run.user_id,
            run.agent_run_id,
            run.lease_version,
        )

    return list_agent_messages(user_id)


def _lease_lost_execution_error(agent_run_id: str) -> AgentRunExecutionError:
    return AgentRunExecutionError(
        "AGENT_RUN_LEASE_LOST",
        f"Agent run ownership was lost: {agent_run_id}",
    )


async def create_agent_reply(
    input_data: AgentChatInput,
    *,
    provider_router: LLMProviderRouter | None = None,
    retry_of_agent_run_id: str | None = None,
) -> AgentMessage | None:
    if not is_demo_user(input_data.user_id):
        return None

    _enforce_agent_run_limit(input_data.user_id)
    existing = list_agent_messages(input_data.user_id) or []
    request_id = uuid4().hex
    started_at = timestamp()
    started_clock = perf_counter()
    run = AgentRun(
        agent_run_id=request_id,
        user_id=input_data.user_id,
        status="running",
        started_at=started_at,
        updated_at=started_at,
        request_input=_request_input(input_data),
        retry_of_agent_run_id=retry_of_agent_run_id,
    )
    leased_run = create_agent_run_with_lease(run, new_lease_owner())
    if leased_run is None:
        raise AgentRunExecutionError(
            "AGENT_RUN_CONFLICT",
            "Agent run already exists.",
        )
    token = lease_token_from_run(leased_run)
    session = AgentLeaseSession(token)
    try:
        try:
            graph_result = await session.run(
                run_agent_graph(
                    user_id=input_data.user_id,
                    locale=input_data.locale,
                    message=input_data.message,
                    context=input_data.context,
                    conversation=existing[-10:],
                    provider_router=provider_router,
                    request_id=request_id,
                    lease_token=token,
                )
            )
            completed_message = _complete_agent_run(
                leased_run,
                session.token,
                input_data,
                graph_result,
                started_clock,
            )
            if completed_message is None:
                raise AgentLeaseLostError(request_id)
            return completed_message
        except LLMError as exc:
            _fail_agent_run(
                leased_run,
                session.token,
                input_data,
                exc,
                started_clock,
            )
            raise
        except asyncio.CancelledError:
            _interrupt_agent_run(leased_run, session.token, started_clock)
            raise
        except AgentLeaseLostError:
            raise
        except Exception:
            _interrupt_agent_run(leased_run, session.token, started_clock)
            raise
    except AgentLeaseLostError as exc:
        raise _lease_lost_execution_error(request_id) from exc


def _fail_missing_checkpoint(
    run: AgentRun,
    token: AgentLeaseToken,
    started_clock: float,
) -> AgentRun:
    completed_at = timestamp()
    failed = transition_agent_run_with_lease(
        token,
        run.model_copy(
            update={
                "status": "failed",
                "updated_at": completed_at,
                "completed_at": completed_at,
                "duration_ms": _elapsed_duration(run, started_clock),
                "error_code": "AGENT_CHECKPOINT_MISSING",
                "retry_input": run.request_input,
            }
        ),
    )
    if failed is None:
        raise AgentLeaseLostError(run.agent_run_id)
    return failed


async def resume_agent_run(
    user_id: str,
    agent_run_id: str,
    *,
    provider_router: LLMProviderRouter | None = None,
) -> AgentMessage | None:
    interrupt_expired_agent_runs(user_id)
    runs = list_agent_runs(user_id)
    if runs is None:
        return None
    run = next((item for item in runs if item.agent_run_id == agent_run_id), None)
    if run is None:
        return None
    if run.status == "running":
        raise AgentRunResumeError("AGENT_RUN_ACTIVE", "Agent run is still active.")
    if run.status != "interrupted":
        raise AgentRunResumeError(
            "AGENT_RUN_NOT_RESUMABLE",
            "Agent run is not interrupted.",
        )

    _enforce_agent_run_limit(user_id, exclude_run_id=agent_run_id)
    leased_run = acquire_agent_run_lease(user_id, agent_run_id, new_lease_owner())
    if leased_run is None:
        latest_runs = list_agent_runs(user_id) or []
        latest = next(
            (item for item in latest_runs if item.agent_run_id == agent_run_id),
            None,
        )
        if latest is None:
            return None
        if latest.status in {"running", "interrupted"}:
            raise AgentRunResumeError(
                "AGENT_RUN_ACTIVE",
                "Agent run is still active.",
            )
        raise AgentRunResumeError(
            "AGENT_RUN_NOT_RESUMABLE",
            "Agent run is not interrupted.",
        )

    token = lease_token_from_run(leased_run)
    started_clock = perf_counter()
    try:
        if leased_run.request_input is None:
            _fail_missing_checkpoint(leased_run, token, started_clock)
            raise AgentRunResumeError(
                "AGENT_CHECKPOINT_MISSING",
                "Agent checkpoint is missing.",
            )

        checkpoint_id = get_safe_resume_checkpoint_id(
            agent_run_id,
            leased_run.lease_version - 1,
        )
        if checkpoint_id is None:
            _fail_missing_checkpoint(leased_run, token, started_clock)
            raise AgentRunResumeError(
                "AGENT_CHECKPOINT_MISSING",
                "Agent checkpoint is missing.",
            )

        pinned_run = set_agent_run_resume_checkpoint(token, checkpoint_id)
        if pinned_run is None:
            raise AgentLeaseLostError(agent_run_id)
        token = lease_token_from_run(pinned_run)
        input_data = AgentChatInput(
            user_id=user_id,
            locale=pinned_run.request_input.locale,
            message=pinned_run.request_input.message,
            context=pinned_run.request_input.context,
        )
        session = AgentLeaseSession(token)
        try:
            graph_result = await session.run(
                resume_agent_graph(
                    agent_run_id,
                    checkpoint_id=checkpoint_id,
                    lease_token=token,
                    provider_router=provider_router,
                )
            )
            completed_message = _complete_agent_run(
                pinned_run,
                session.token,
                input_data,
                graph_result,
                started_clock,
            )
            if completed_message is None:
                raise AgentLeaseLostError(agent_run_id)
            return completed_message
        except AgentCheckpointMissingError as exc:
            _fail_missing_checkpoint(pinned_run, session.token, started_clock)
            raise AgentRunResumeError(
                "AGENT_CHECKPOINT_MISSING",
                "Agent checkpoint is missing.",
            ) from exc
        except LLMError as exc:
            _fail_agent_run(
                pinned_run,
                session.token,
                input_data,
                exc,
                started_clock,
            )
            raise
        except asyncio.CancelledError:
            _interrupt_agent_run(pinned_run, session.token, started_clock)
            raise
        except AgentLeaseLostError:
            raise
        except Exception:
            _interrupt_agent_run(pinned_run, session.token, started_clock)
            raise
    except AgentLeaseLostError as exc:
        raise _lease_lost_execution_error(agent_run_id) from exc


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
