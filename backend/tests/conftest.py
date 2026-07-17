import pytest

from backend.app.core.config import get_settings
from backend.app.services.demo_store import reset_demo_store


@pytest.fixture(autouse=True)
def clean_demo_store():
    get_settings.cache_clear()
    reset_demo_store()
    yield
    reset_demo_store()
    get_settings.cache_clear()
