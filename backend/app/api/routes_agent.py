from fastapi import APIRouter, Header
from fastapi.responses import JSONResponse

from backend.app.api.responses import error, ok
from backend.app.api.auth import authorize_user
from backend.app.data.demo_data import DEMO_USER_ID
from backend.app.llm.errors import LLMError
from backend.app.models.domain import AgentChatInput, AgentRunRetryRequest
from backend.app.services.agent_service import create_agent_reply, retry_agent_run
from backend.app.services.demo_store import list_agent_messages, list_agent_runs


router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.post("/chat")
async def chat(input_data: AgentChatInput, authorization: str | None = Header(default=None)) -> object:
    denied = authorize_user(input_data.user_id, authorization)
    if denied: return denied
    try:
        reply = await create_agent_reply(input_data)
    except LLMError as exc:
        details = {"request_id": exc.request_id}
        if exc.provider_request_id is not None:
            details["provider_request_id"] = exc.provider_request_id
        return JSONResponse(
            status_code=exc.status_code,
            content=error(exc.code, exc.message, details),
        )
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
    saved_messages = list_agent_messages(user_id)
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
    saved_runs = list_agent_runs(user_id)
    if saved_runs is None:
        return JSONResponse(
            status_code=404,
            content=error("NOT_FOUND", "Demo user not found.", {"user_id": user_id}),
        )
    return ok(
        [
            run.model_dump(exclude={"retry_input"})
            for run in sorted(saved_runs, key=lambda item: item.completed_at, reverse=True)
        ]
    )


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
    except LLMError as exc:
        details = {"request_id": exc.request_id}
        if exc.provider_request_id is not None:
            details["provider_request_id"] = exc.provider_request_id
        return JSONResponse(
            status_code=exc.status_code,
            content=error(exc.code, exc.message, details),
        )
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
