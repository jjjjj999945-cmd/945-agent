from collections.abc import AsyncIterator, Iterator, Sequence
from functools import lru_cache
from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import (
    BaseCheckpointSaver,
    ChannelVersions,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
)
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.mongodb import MongoDBSaver
from pymongo import MongoClient

from backend.app.core.config import Settings, get_settings
from backend.app.services.agent_run_lease import (
    AgentLeaseLostError,
    AgentLeaseToken,
    lease_token_from_config,
)
from backend.app.services.demo_store import agent_run_lease_is_valid


class LeaseFencedCheckpointer(BaseCheckpointSaver):
    def __init__(self, delegate: Any) -> None:
        super().__init__(serde=getattr(delegate, "serde", None))
        self.delegate = delegate

    @property
    def config_specs(self) -> list:
        return getattr(self.delegate, "config_specs", [])

    def get_next_version(self, current: Any, channel: Any) -> Any:
        return self.delegate.get_next_version(current, channel)

    def _assert_write_lease(
        self,
        config: RunnableConfig,
    ) -> AgentLeaseToken | None:
        token = lease_token_from_config(config)
        if token is not None and not agent_run_lease_is_valid(token):
            raise AgentLeaseLostError(token.agent_run_id)
        return token

    def get_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        return self.delegate.get_tuple(config)

    def list(
        self,
        config: RunnableConfig | None,
        *,
        filter: dict[str, Any] | None = None,
        before: RunnableConfig | None = None,
        limit: int | None = None,
    ) -> Iterator[CheckpointTuple]:
        return self.delegate.list(
            config,
            filter=filter,
            before=before,
            limit=limit,
        )

    def put(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        token = self._assert_write_lease(config)
        safe_metadata = dict(metadata)
        if token is not None:
            safe_metadata.update(
                {
                    "agent_run_id": token.agent_run_id,
                    "lease_version": token.version,
                }
            )
        return self.delegate.put(
            config,
            checkpoint,
            safe_metadata,
            new_versions,
        )

    def put_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        self._assert_write_lease(config)
        self.delegate.put_writes(config, writes, task_id, task_path)

    async def aget_tuple(
        self,
        config: RunnableConfig,
    ) -> CheckpointTuple | None:
        return await self.delegate.aget_tuple(config)

    async def alist(
        self,
        config: RunnableConfig | None,
        *,
        filter: dict[str, Any] | None = None,
        before: RunnableConfig | None = None,
        limit: int | None = None,
    ) -> AsyncIterator[CheckpointTuple]:
        async for checkpoint in self.delegate.alist(
            config,
            filter=filter,
            before=before,
            limit=limit,
        ):
            yield checkpoint

    async def aput(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        token = self._assert_write_lease(config)
        safe_metadata = dict(metadata)
        if token is not None:
            safe_metadata.update(
                {
                    "agent_run_id": token.agent_run_id,
                    "lease_version": token.version,
                }
            )
        return await self.delegate.aput(
            config,
            checkpoint,
            safe_metadata,
            new_versions,
        )

    async def aput_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        self._assert_write_lease(config)
        await self.delegate.aput_writes(config, writes, task_id, task_path)


def create_agent_checkpointer(settings: Settings) -> Any:
    """Create the durable-checkpoint implementation selected by storage mode."""
    if settings.storage_backend == "demo":
        return LeaseFencedCheckpointer(MemorySaver())

    client = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=5000)
    return LeaseFencedCheckpointer(
        MongoDBSaver(
            client,
            db_name=settings.mongodb_database,
            checkpoint_collection_name="agent_checkpoints",
            writes_collection_name="agent_checkpoint_writes",
        )
    )


@lru_cache
def get_agent_checkpointer() -> Any:
    return create_agent_checkpointer(get_settings())
