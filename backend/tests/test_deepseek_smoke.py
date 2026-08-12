import asyncio
import os

import pytest

from backend.app.core.config import Settings
from backend.app.llm.factory import build_llm_provider_router
from backend.app.llm.models import AgentModelRequest


pytestmark = pytest.mark.skipif(
    os.getenv("945_RUN_DEEPSEEK_SMOKE_TESTS") != "1",
    reason="Set 945_RUN_DEEPSEEK_SMOKE_TESTS=1 to run a real DeepSeek request.",
)


def test_deepseek_returns_a_safe_training_knowledge_reply_without_draft():
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        pytest.skip("DEEPSEEK_API_KEY is not configured.")
    router = build_llm_provider_router(
        Settings(
            app_env="production",
            llm_provider="deepseek",
            deepseek_api_key=api_key,
            deepseek_model=os.getenv("945_DEEPSEEK_MODEL", "deepseek-v4-flash"),
            deepseek_max_tokens=120,
        )
    )

    result = asyncio.run(
        router.generate(
            AgentModelRequest(
                request_id="deepseek-smoke-knowledge",
                user_id="demo-user-945",
                locale="zh-CN",
                message="用一句话说明深蹲热身的作用。",
            )
        )
    )

    assert result.provider == "deepseek"
    assert result.reply
    assert result.record_draft is None
