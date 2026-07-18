import asyncio
import os

import pytest

from backend.app.agents.graph import run_agent_graph
from backend.app.core.config import get_settings
from backend.app.data.demo_data import DEMO_USER_ID
from backend.app.llm.factory import build_llm_provider_router


RUN_REAL_API = os.getenv("945_RUN_OPENAI_SMOKE_TESTS") == "1"
pytestmark = pytest.mark.skipif(
    not RUN_REAL_API,
    reason="Set 945_RUN_OPENAI_SMOKE_TESTS=1 to run paid OpenAI smoke tests.",
)


def _router():
    settings = get_settings()
    if settings.llm_provider != "openai":
        pytest.fail("945_LLM_PROVIDER must be openai for the real API smoke tests.")
    if settings.openai_api_key is None or not settings.openai_model:
        pytest.fail("OPENAI_API_KEY and 945_OPENAI_MODEL are required for the real API smoke tests.")
    return build_llm_provider_router(settings)


def test_real_openai_answers_one_chinese_fitness_question():
    result = asyncio.run(
        run_agent_graph(
            user_id=DEMO_USER_ID,
            locale="zh-CN",
            message="深蹲时应该如何保持躯干稳定？",
            context={"date": "2026-07-11"},
            provider_router=_router(),
        )
    )

    assert result.provider == "openai"
    assert result.reply.strip()
    assert result.record_draft is None


def test_real_openai_creates_confirmable_workout_draft_without_saving():
    result = asyncio.run(
        run_agent_graph(
            user_id=DEMO_USER_ID,
            locale="zh-CN",
            message="今天做了深蹲 4 组，每组 8 次，80kg，帮我记录。",
            context={"date": "2026-07-11"},
            provider_router=_router(),
        )
    )

    assert result.provider == "openai"
    assert result.record_draft.type == "workout_log"
    assert result.record_draft.requires_confirmation is True
