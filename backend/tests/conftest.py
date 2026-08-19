import os

os.environ.setdefault("945_REFERENCE_DATE", "2026-07-11")

import pytest

from backend.app.agents.checkpoint import get_agent_checkpointer
from backend.app.agents.graph import get_agent_graph
from backend.app.core.config import get_settings
from backend.app.llm.factory import get_llm_provider_router
from backend.app.services import agent_service
from backend.app.services.demo_store import reset_demo_store


@pytest.fixture(autouse=True)
def clean_demo_store():
    get_settings.cache_clear()
    get_llm_provider_router.cache_clear()
    get_agent_graph.cache_clear()
    get_agent_checkpointer.cache_clear()
    agent_service._active_agent_run_ids.clear()
    reset_demo_store()
    yield
    reset_demo_store()
    agent_service._active_agent_run_ids.clear()
    get_agent_graph.cache_clear()
    get_agent_checkpointer.cache_clear()
    get_llm_provider_router.cache_clear()
    get_settings.cache_clear()
