import pytest

from backend.app.core.config import get_settings
from backend.app.llm.factory import get_llm_provider_router
from backend.app.services.demo_store import reset_demo_store


@pytest.fixture(autouse=True)
def clean_demo_store():
    get_settings.cache_clear()
    get_llm_provider_router.cache_clear()
    reset_demo_store()
    yield
    reset_demo_store()
    get_llm_provider_router.cache_clear()
    get_settings.cache_clear()
