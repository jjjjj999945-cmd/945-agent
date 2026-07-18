from uuid import uuid4

from backend.app.agents.graph import run_agent_graph
from backend.app.llm.factory import LLMProviderRouter
from backend.app.models.domain import AgentChatInput, AgentMessage
from backend.app.services.demo_seed import timestamp
from backend.app.services.demo_store import (
    is_demo_user,
    list_agent_messages,
    save_agent_message,
)


async def create_agent_reply(
    input_data: AgentChatInput,
    *,
    provider_router: LLMProviderRouter | None = None,
) -> AgentMessage | None:
    if not is_demo_user(input_data.user_id):
        return None

    existing = list_agent_messages(input_data.user_id) or []
    request_id = uuid4().hex
    graph_result = await run_agent_graph(
        user_id=input_data.user_id,
        locale=input_data.locale,
        message=input_data.message,
        context=input_data.context,
        conversation=existing[-10:],
        provider_router=provider_router,
        request_id=request_id,
    )
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
    return agent_message
