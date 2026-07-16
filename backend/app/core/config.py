import os
from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, ConfigDict


StorageBackend = Literal["demo", "mongo"]


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    storage_backend: StorageBackend = "demo"
    mongodb_uri: str = "mongodb://127.0.0.1:27017"
    mongodb_database: str = "945"


@lru_cache
def get_settings() -> Settings:
    return Settings(
        storage_backend=os.getenv("945_STORAGE_BACKEND", "demo"),
        mongodb_uri=os.getenv("945_MONGODB_URI", "mongodb://127.0.0.1:27017"),
        mongodb_database=os.getenv("945_MONGODB_DATABASE", "945")
    )
