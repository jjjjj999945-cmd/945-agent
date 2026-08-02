from functools import lru_cache
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.mongodb import MongoDBSaver
from pymongo import MongoClient

from backend.app.core.config import Settings, get_settings


def create_agent_checkpointer(settings: Settings) -> Any:
    """Create the durable-checkpoint implementation selected by storage mode."""
    if settings.storage_backend == "demo":
        return MemorySaver()

    client = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=5000)
    return MongoDBSaver(
        client,
        db_name=settings.mongodb_database,
        checkpoint_collection_name="agent_checkpoints",
        writes_collection_name="agent_checkpoint_writes",
    )


@lru_cache
def get_agent_checkpointer() -> Any:
    return create_agent_checkpointer(get_settings())
