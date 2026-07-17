import os
from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, ConfigDict, SecretStr


StorageBackend = Literal["demo", "mongo"]
AppEnvironment = Literal["development", "production"]
LLMProviderName = Literal["deterministic", "openai"]


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    storage_backend: StorageBackend = "demo"
    mongodb_uri: str = "mongodb://127.0.0.1:27017"
    mongodb_database: str = "945"
    app_env: AppEnvironment = "development"
    llm_provider: LLMProviderName = "deterministic"
    openai_api_key: SecretStr | None = None
    openai_model: str | None = None
    llm_timeout_seconds: float = 20.0


@lru_cache
def get_settings() -> Settings:
    return Settings(
        storage_backend=os.getenv("945_STORAGE_BACKEND", "demo"),
        mongodb_uri=os.getenv("945_MONGODB_URI", "mongodb://127.0.0.1:27017"),
        mongodb_database=os.getenv("945_MONGODB_DATABASE", "945"),
        app_env=os.getenv("945_APP_ENV", "development"),
        llm_provider=os.getenv("945_LLM_PROVIDER", "deterministic"),
        openai_api_key=os.getenv("OPENAI_API_KEY") or None,
        openai_model=os.getenv("945_OPENAI_MODEL") or None,
        llm_timeout_seconds=os.getenv("945_LLM_TIMEOUT_SECONDS", "20"),
    )
