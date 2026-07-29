import asyncio

import pytest

from backend.app.core.config import Settings
from backend.app.llm.errors import LLMConfigError, LLMTimeoutError
from backend.app.llm.factory import LLMProviderRouter, build_llm_provider_router
from backend.app.llm.models import AgentModelRequest, AgentModelResponse, ProviderUsage


class StubProvider:
    def __init__(self, name: str, result=None, error=None):
        self.name = name
        self.result = result
        self.error = error
        self.calls = 0

    async def generate(self, request):
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.result


def _request() -> AgentModelRequest:
    return AgentModelRequest(
        request_id="req-router",
        user_id="demo-user-945",
        locale="zh-CN",
        message="今天练什么？",
    )


def _fallback_result() -> AgentModelResponse:
    return AgentModelResponse(
        intent="ask_question",
        reply="本地回复",
        provider="deterministic",
        model="rules-v1",
        usage=ProviderUsage(logical_generations=1),
    )


def test_development_router_falls_back_and_marks_response():
    primary = StubProvider(
        "openai",
        error=LLMTimeoutError("timeout", request_id="req-router", http_attempts=2),
    )
    fallback = StubProvider("deterministic", result=_fallback_result())
    router = LLMProviderRouter(primary=primary, fallback=fallback, app_env="development")

    result = asyncio.run(router.generate(_request()))

    assert primary.calls == 1
    assert fallback.calls == 1
    assert result.provider == "deterministic"
    assert result.degraded is True
    assert result.degraded_reason == "LLM_TIMEOUT"
    assert result.usage.http_attempts == 2


def test_router_logs_latency_and_degraded_reason(caplog):
    primary = StubProvider(
        "openai",
        error=LLMTimeoutError("timeout", request_id="req-router", http_attempts=2),
    )
    fallback = StubProvider("deterministic", result=_fallback_result())
    router = LLMProviderRouter(primary=primary, fallback=fallback, app_env="development")

    with caplog.at_level("INFO", logger="backend.app.llm.factory"):
        asyncio.run(router.generate(_request()))

    call = next(record for record in caplog.records if record.message == "llm_provider_call")
    assert call.request_id == "req-router"
    assert call.provider == "deterministic"
    assert call.degraded is True
    assert call.degraded_reason == "LLM_TIMEOUT"
    assert call.latency_ms >= 0


def test_production_router_returns_the_original_stable_error():
    error = LLMTimeoutError("timeout", http_attempts=2)
    router = LLMProviderRouter(
        primary=StubProvider("openai", error=error),
        fallback=StubProvider("deterministic", result=_fallback_result()),
        app_env="production",
    )

    with pytest.raises(LLMTimeoutError) as captured:
        asyncio.run(router.generate(_request()))

    assert captured.value is error
    assert captured.value.request_id == "req-router"


def test_missing_openai_configuration_degrades_only_in_development():
    development = build_llm_provider_router(
        Settings(app_env="development", llm_provider="openai")
    )
    production = build_llm_provider_router(
        Settings(app_env="production", llm_provider="openai")
    )

    assert asyncio.run(development.generate(_request())).degraded is True
    with pytest.raises(LLMConfigError):
        asyncio.run(production.generate(_request()))


def test_openai_client_factory_disables_sdk_retries(monkeypatch):
    captured = {}

    class FakeAsyncOpenAI:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr("backend.app.llm.factory.AsyncOpenAI", FakeAsyncOpenAI)

    router = build_llm_provider_router(
        Settings(
            app_env="production",
            llm_provider="openai",
            openai_api_key="sk-test",
            openai_model="configured-model",
            llm_timeout_seconds=13,
        )
    )

    assert router.primary.name == "openai"
    assert captured == {
        "api_key": "sk-test",
        "timeout": 13.0,
        "max_retries": 0,
    }
