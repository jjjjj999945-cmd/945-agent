from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend.app.api.responses import error, ok
from backend.app.data.demo_data import DEMO_USER_ID
from backend.app.models.domain import AgentChatInput
from backend.app.services.demo_store import create_agent_reply, list_agent_messages


router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.post("/chat")
def chat(input_data: AgentChatInput) -> object:
    reply = create_agent_reply(input_data)
    if reply is None:
        return JSONResponse(
            status_code=404,
            content=error("NOT_FOUND", "Demo user not found.", {"user_id": input_data.user_id})
        )
    return ok(reply.model_dump())


@router.get("/messages")
def messages(user_id: str = DEMO_USER_ID) -> object:
    saved_messages = list_agent_messages(user_id)
    if saved_messages is None:
        return JSONResponse(
            status_code=404,
            content=error("NOT_FOUND", "Demo user not found.", {"user_id": user_id})
        )
    return ok([message.model_dump() for message in saved_messages])
