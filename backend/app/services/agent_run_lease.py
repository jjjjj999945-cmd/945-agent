from dataclasses import dataclass
from datetime import datetime
from os import getpid
from uuid import uuid4

from backend.app.models.domain import AgentRun


class AgentLeaseLostError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class AgentLeaseToken:
    user_id: str
    agent_run_id: str
    owner: str
    version: int
    expires_at: datetime


def new_lease_owner() -> str:
    return f"{getpid()}:{uuid4().hex}"


def lease_token_from_run(run: AgentRun) -> AgentLeaseToken:
    if run.lease_owner is None or run.lease_expires_at is None:
        raise ValueError("Agent run does not hold a lease.")
    return AgentLeaseToken(
        user_id=run.user_id,
        agent_run_id=run.agent_run_id,
        owner=run.lease_owner,
        version=run.lease_version,
        expires_at=run.lease_expires_at,
    )


def lease_config(token: AgentLeaseToken) -> dict[str, object]:
    return {
        "agent_user_id": token.user_id,
        "agent_run_id": token.agent_run_id,
        "agent_lease_owner": token.owner,
        "agent_lease_version": token.version,
        "agent_lease_expires_at": token.expires_at.isoformat(),
    }


def lease_token_from_config(config: dict) -> AgentLeaseToken | None:
    values = config.get("configurable", {})
    if "agent_lease_version" not in values:
        return None
    return AgentLeaseToken(
        user_id=str(values["agent_user_id"]),
        agent_run_id=str(values["agent_run_id"]),
        owner=str(values["agent_lease_owner"]),
        version=int(values["agent_lease_version"]),
        expires_at=datetime.fromisoformat(str(values["agent_lease_expires_at"])),
    )
