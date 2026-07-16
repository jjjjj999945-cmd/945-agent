import pytest

from backend.app.services.demo_store import reset_demo_store


@pytest.fixture(autouse=True)
def clean_demo_store():
    reset_demo_store()
    yield
    reset_demo_store()
