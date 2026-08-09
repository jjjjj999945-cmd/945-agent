import pytest

from backend.app.core.config import get_settings
from backend.app.llm.factory import get_llm_provider_router
from backend.app.repositories.mongo import MongoRepository
from backend.app.services import demo_store
from backend.app.services.demo_store import reset_demo_store
from backend.app.services.repository_store import RepositoryBackedStore
from backend.tests.test_mongo_repository import FakeDatabase


@pytest.fixture(autouse=True)
def clean_demo_store():
    get_settings.cache_clear()
    get_llm_provider_router.cache_clear()
    reset_demo_store()
    yield
    reset_demo_store()
    get_llm_provider_router.cache_clear()
    get_settings.cache_clear()


@pytest.fixture
def mongo_store(monkeypatch):
    monkeypatch.setenv("945_STORAGE_BACKEND", "mongo")
    get_settings.cache_clear()
    store = RepositoryBackedStore(MongoRepository(FakeDatabase()))
    store.seed_demo_data()
    demo_store.set_repository_store_for_tests(store)
    try:
        yield store
    finally:
        demo_store.set_repository_store_for_tests(None)
        get_settings.cache_clear()
