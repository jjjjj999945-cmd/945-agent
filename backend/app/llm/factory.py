import logging
from functools import lru_cache
from typing import Any

from openai import AsyncOpenAI

from backend.app.core.config import Settings, get_settings
from backend.app.llm.deterministic import DeterministicProvider
from backend.app.llm.errors import LLMConfigError, LLMError
from backend.app.llm.models import AgentModelRequest, AgentModelResponse
from backend.app.llm.openai_provider import OpenAIProvider


logger = logging.getLogger(__name__)


class UnavailableProvider:
    name = "openai"

    def __init__(self, message: str) -> None:
        self.message = message

    async def generate(self, request: AgentModelRequest) -> AgentModelResponse:
        raise LLMConfigError(self.message, request_id=request.request_id)


class LLMProviderRouter:
    def __init__(self, *, primary: Any, fallback: Any, app_env: str) -> None:
        self.primary = primary
        self.fallback = fallback
        self.app_env = app_env

    async def generate(self, request: AgentModelRequest) -> AgentModelResponse:
        try:
            result = await self.primary.generate(request)
        except LLMError as exc:
            result = await self.recover(request, exc)
        logger.info(
            "llm_provider_call",
            extra={
                "request_id": request.request_id,
                "provider": result.provider,
                "model": result.model,
                "provider_request_id": result.provider_request_id,
                "input_tokens": result.usage.input_tokens,
                "output_tokens": result.usage.output_tokens,
                "logical_generations": result.usage.logical_generations,
                "http_attempts": result.usage.http_attempts,
                "degraded": result.degraded,
            },
        )
        return result

    async def recover(self, request: AgentModelRequest, exc: LLMError) -> AgentModelResponse:
        exc.attach_request_id(request.request_id)
        if self.app_env != "development" or self.primary.name == "deterministic":
            raise exc

        logger.warning(
            "llm_provider_fallback",
            extra={
                "request_id": request.request_id,
                "provider": self.primary.name,
                "error_code": exc.code,
                "http_attempts": exc.http_attempts,
            },
        )
        fallback_request = request.model_copy(update={"continuation": None})
        result = await self.fallback.generate(fallback_request)
        return result.model_copy(
            update={
                "degraded": True,
                "degraded_reason": exc.code,
                "usage": result.usage.model_copy(
                    update={"http_attempts": result.usage.http_attempts + exc.http_attempts}
                ),
            }
        )


def build_llm_provider_router(
    settings: Settings | None = None,
    *,
    openai_client: Any | None = None,
) -> LLMProviderRouter:
    settings = settings or get_settings()
    fallback = DeterministicProvider()
    if settings.llm_provider == "deterministic":
        return LLMProviderRouter(primary=fallback, fallback=fallback, app_env=settings.app_env)

    if settings.openai_api_key is None or not settings.openai_model:
        primary = UnavailableProvider("OpenAI API key and model must be configured.")
    else:
        client = openai_client or AsyncOpenAI(
            api_key=settings.openai_api_key.get_secret_value(),
            timeout=settings.llm_timeout_seconds,
            max_retries=0,
        )
        primary = OpenAIProvider(client=client, model=settings.openai_model)
    return LLMProviderRouter(primary=primary, fallback=fallback, app_env=settings.app_env)


@lru_cache
def get_llm_provider_router() -> LLMProviderRouter:
    return build_llm_provider_router()
