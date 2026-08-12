import hashlib
import os

from backend.app.core.config import Settings


def configure_langsmith_tracing(settings: Settings) -> bool:
    """Enable LangSmith only when the server is explicitly configured for it."""
    if not settings.langsmith_tracing or settings.langsmith_api_key is None:
        return False

    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key.get_secret_value()
    os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project
    os.environ["LANGSMITH_HIDE_INPUTS"] = "true"
    os.environ["LANGSMITH_HIDE_OUTPUTS"] = "true"
    return True


def agent_trace_metadata(*, request_id: str, user_id: str, locale: str, provider: str) -> dict[str, str]:
    return {
        "945_request_id": request_id,
        "945_user_hash": hashlib.sha256(user_id.encode("utf-8")).hexdigest()[:16],
        "945_locale": locale,
        "945_provider": provider,
    }
