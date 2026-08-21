import asyncio
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from os import getpid
from typing import Awaitable, TypeVar
from uuid import uuid4

from backend.app.models.domain import AgentRun


ResultT = TypeVar("ResultT")


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


def renew_agent_run_lease(token: AgentLeaseToken) -> AgentRun | None:
    from backend.app.services.demo_store import renew_agent_run_lease as renew

    return renew(token)


class AgentLeaseSession:
    def __init__(
        self,
        token: AgentLeaseToken,
        heartbeat_seconds: float | None = None,
    ) -> None:
        if heartbeat_seconds is None:
            from backend.app.core.config import get_settings

            heartbeat_seconds = get_settings().agent_lease_heartbeat_seconds
        self.token = token
        self.heartbeat_seconds = heartbeat_seconds
        self.lease_lost = False

    async def run(self, awaitable: Awaitable[ResultT]) -> ResultT:
        work = asyncio.create_task(awaitable)
        heartbeat = asyncio.create_task(self._heartbeat(work))
        try:
            return await work
        except asyncio.CancelledError as exc:
            if self.lease_lost:
                raise AgentLeaseLostError(self.token.agent_run_id) from exc
            raise
        finally:
            heartbeat.cancel()
            with suppress(asyncio.CancelledError):
                await heartbeat

    async def _heartbeat(self, work: asyncio.Task) -> None:
        while not work.done():
            await asyncio.sleep(self.heartbeat_seconds)
            try:
                renewed = renew_agent_run_lease(self.token)
            except Exception:
                if datetime.now(UTC) < self.token.expires_at:
                    continue
                renewed = None
            if renewed is None:
                self.lease_lost = True
                work.cancel()
                return
            self.token = lease_token_from_run(renewed)
