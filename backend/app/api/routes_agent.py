from fastapi import APIRouter, Header
from fastapi.responses import JSONResponse

from backend.app.api.responses import error, ok
from backend.app.api.auth import authorize_user
from backend.app.data.demo_data import DEMO_USER_ID
from backend.app.llm.errors import LLMError
from backend.app.models.domain import AgentChatInput, AgentRunRetryRequest
from backend.app.services.agent_service import (
    AgentRunExecutionError,
    create_agent_reply,
    list_user_agent_messages,
    list_user_agent_runs,
    resume_agent_run,
    retry_agent_run,
)
from backend.app.services.agent_observability import summarize_agent_runs


router = APIRouter(prefix="/api/agent", tags=["agent"])
AGENT_RUN_INTERNAL_FIELDS = {
    "request_input",
    "retry_input",
    "trace_steps",
    "lease_owner",
    "lease_version",
    "lease_expires_at",
    "last_heartbeat_at",
    "resume_checkpoint_id",
    "messages_persisted",
}


def _llm_error_response(exc: LLMError) -> JSONResponse:
    details = {"request_id": exc.request_id}
    if exc.provider_request_id is not None:
        details["provider_request_id"] = exc.provider_request_id
    return JSONResponse(
        status_code=exc.status_code,
        content=error(exc.code, exc.message, details),
    )


def _agent_run_error_response(
    exc: AgentRunExecutionError,
    agent_run_id: str | None = None,
) -> JSONResponse:
    details = {} if agent_run_id is None else {"agent_run_id": agent_run_id}
    return JSONResponse(
        status_code=exc.status_code,
        content=error(exc.code, exc.message, details),
    )


@router.post("/chat")
async def chat(input_data: AgentChatInput, authorization: str | None = Header(default=None)) -> object:
    denied = authorize_user(input_data.user_id, authorization)
    if denied: return denied
    try:
        reply = await create_agent_reply(input_data)
    except AgentRunExecutionError as exc:
        return _agent_run_error_response(exc)
    except LLMError as exc:
        return _llm_error_response(exc)
    if reply is None:
        return JSONResponse(
            status_code=404,
            content=error("NOT_FOUND", "Demo user not found.", {"user_id": input_data.user_id})
        )
    return ok(reply.model_dump())


@router.get("/messages")
def messages(user_id: str = DEMO_USER_ID, authorization: str | None = Header(default=None)) -> object:
    denied = authorize_user(user_id, authorization)
    if denied: return denied
    saved_messages = list_user_agent_messages(user_id)
    if saved_messages is None:
        return JSONResponse(
            status_code=404,
            content=error("NOT_FOUND", "Demo user not found.", {"user_id": user_id})
        )
    return ok([message.model_dump() for message in saved_messages])


@router.get("/runs")
def runs(user_id: str = DEMO_USER_ID, authorization: str | None = Header(default=None)) -> object:
    denied = authorize_user(user_id, authorization)
    if denied:
        return denied
    saved_runs = list_user_agent_runs(user_id)
    if saved_runs is None:
        return JSONResponse(
            status_code=404,
            content=error("NOT_FOUND", "Demo user not found.", {"user_id": user_id}),
        )
    return ok(
        [
            run.model_dump(exclude=AGENT_RUN_INTERNAL_FIELDS)
            for run in sorted(
                saved_runs,
                key=lambda item: item.updated_at or item.completed_at or item.started_at,
                reverse=True,
            )
        ]
    )


@router.get("/runs/{agent_run_id}/trace")
def run_trace(
    agent_run_id: str,
    user_id: str = DEMO_USER_ID,
    authorization: str | None = Header(default=None),
) -> object:
    denied = authorize_user(user_id, authorization)
    if denied:
        return denied
    saved_runs = list_user_agent_runs(user_id)
    run = next((item for item in saved_runs or [] if item.agent_run_id == agent_run_id), None)
    if run is None:
        return JSONResponse(
            status_code=404,
            content=error("NOT_FOUND", "Agent run not found.", {"agent_run_id": agent_run_id}),
        )
    return ok([step.model_dump() for step in run.trace_steps])


@router.get("/metrics")
def metrics(user_id: str = DEMO_USER_ID, authorization: str | None = Header(default=None)) -> object:
    denied = authorize_user(user_id, authorization)
    if denied:
        return denied
    saved_runs = list_user_agent_runs(user_id)
    if saved_runs is None:
        return JSONResponse(
            status_code=404,
            content=error("NOT_FOUND", "Demo user not found.", {"user_id": user_id}),
        )
    return ok(summarize_agent_runs(saved_runs).model_dump())


@router.post("/runs/{agent_run_id}/retry")
async def retry(
    agent_run_id: str,
    input_data: AgentRunRetryRequest,
    authorization: str | None = Header(default=None),
) -> object:
    denied = authorize_user(input_data.user_id, authorization)
    if denied:
        return denied
    try:
        reply = await retry_agent_run(input_data.user_id, agent_run_id)
    except AgentRunExecutionError as exc:
        return _agent_run_error_response(exc, agent_run_id)
    except LLMError as exc:
        return _llm_error_response(exc)
    if reply is None:
        return JSONResponse(
            status_code=404,
            content=error(
                "NOT_FOUND",
                "Failed agent run not found or cannot be retried.",
                {"agent_run_id": agent_run_id},
            ),
        )
    return ok(reply.model_dump())


@router.post("/runs/{agent_run_id}/resume")
async def resume(
    agent_run_id: str,
    input_data: AgentRunRetryRequest,
    authorization: str | None = Header(default=None),
) -> object:
    denied = authorize_user(input_data.user_id, authorization)
    if denied:
        return denied
    try:
        reply = await resume_agent_run(input_data.user_id, agent_run_id)
    except AgentRunExecutionError as exc:
        return _agent_run_error_response(exc, agent_run_id)
    except LLMError as exc:
        return _llm_error_response(exc)
    if reply is None:
        return JSONResponse(
            status_code=404,
            content=error(
                "NOT_FOUND",
                "Agent run not found.",
                {"agent_run_id": agent_run_id},
            ),
        )
    return ok(reply.model_dump())
