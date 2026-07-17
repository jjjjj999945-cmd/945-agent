from backend.app.core.config import get_settings


def test_llm_settings_default_to_local_deterministic_mode(monkeypatch):
    for name in (
        "945_APP_ENV",
        "945_LLM_PROVIDER",
        "OPENAI_API_KEY",
        "945_OPENAI_MODEL",
        "945_LLM_TIMEOUT_SECONDS",
    ):
        monkeypatch.delenv(name, raising=False)
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.app_env == "development"
    assert settings.llm_provider == "deterministic"
    assert settings.openai_api_key is None
    assert settings.openai_model is None
    assert settings.llm_timeout_seconds == 20.0


def test_openai_key_is_stored_as_a_redacted_secret(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-secret")
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.openai_api_key.get_secret_value() == "sk-test-secret"
    assert "sk-test-secret" not in repr(settings)
