import os

from backend.app.core.config import Settings
from backend.app.observability.langsmith import agent_trace_metadata, configure_langsmith_tracing


def test_langsmith_tracing_is_disabled_without_explicit_configuration(monkeypatch):
    monkeypatch.delenv("LANGSMITH_TRACING", raising=False)

    enabled = configure_langsmith_tracing(Settings())

    assert enabled is False
    assert "LANGSMITH_TRACING" not in os.environ


def test_enabled_langsmith_hides_inputs_and_outputs(monkeypatch):
    settings = Settings(
        langsmith_tracing=True,
        langsmith_api_key="test-key",
        langsmith_project="945-test",
    )

    keys = [
        "LANGSMITH_TRACING",
        "LANGSMITH_API_KEY",
        "LANGSMITH_PROJECT",
        "LANGSMITH_HIDE_INPUTS",
        "LANGSMITH_HIDE_OUTPUTS",
    ]
    original_values = {key: os.getenv(key) for key in keys}
    try:
        enabled = configure_langsmith_tracing(settings)

        assert enabled is True
        assert os.environ["LANGSMITH_TRACING"] == "true"
        assert os.environ["LANGSMITH_API_KEY"] == "test-key"
        assert os.environ["LANGSMITH_PROJECT"] == "945-test"
        assert os.environ["LANGSMITH_HIDE_INPUTS"] == "true"
        assert os.environ["LANGSMITH_HIDE_OUTPUTS"] == "true"
    finally:
        for key, value in original_values.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def test_agent_trace_metadata_is_anonymous_and_excludes_message_content():
    metadata = agent_trace_metadata(
        request_id="run-123",
        user_id="demo-user-945",
        locale="zh-CN",
        provider="deterministic",
    )

    assert metadata["945_request_id"] == "run-123"
    assert metadata["945_locale"] == "zh-CN"
    assert metadata["945_provider"] == "deterministic"
    assert metadata["945_user_hash"] != "demo-user-945"
    assert "message" not in metadata
