import asyncio
import os

import pytest
from langgraph.checkpoint.memory import MemorySaver

import backend.app.agents.graph as agent_graph_module
from backend.app.agents.checkpoint import create_agent_checkpointer
from backend.app.agents.graph import get_agent_graph, run_agent_graph
from backend.app.agents.nodes import safety_guard
from backend.app.core.config import Settings
from backend.app.data.demo_data import DEMO_USER_ID
from backend.app.llm.errors import LLMOutputInvalidError
from backend.app.llm.models import AgentModelResponse, ProviderContinuation, ToolCallProposal
from backend.app.models.domain import AgentMessage


class StubRouter:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    async def generate(self, request):
        self.requests.append(request)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    async def recover(self, request, exc):
        raise exc


class CrashOnceRouter:
    def __init__(self):
        self.requests = []

    async def generate(self, request):
        self.requests.append(request)
        if len(self.requests) == 1:
            raise RuntimeError("simulated process interruption")
        return AgentModelResponse(intent="ask_question", reply="恢复完成", provider="stub")

    async def recover(self, request, exc):
        raise exc


def test_agent_graph_resumes_the_same_thread_from_the_failed_node(monkeypatch):
    router = CrashOnceRouter()
    original = agent_graph_module.context_builder
    context_calls = []

    def counting_context_builder(user_id, date):
        context_calls.append((user_id, date))
        return original(user_id, date)

    monkeypatch.setattr(agent_graph_module, "context_builder", counting_context_builder)
    agent_graph_module.get_agent_graph.cache_clear()
    with pytest.raises(RuntimeError, match="simulated process interruption"):
        asyncio.run(
            run_agent_graph(
                user_id=DEMO_USER_ID,
                locale="zh-CN",
                message="如何热身？",
                context={"date": "2026-07-11"},
                provider_router=router,
                request_id="graph-resume-same-thread",
            )
        )

    result = asyncio.run(
        agent_graph_module.resume_agent_graph(
            "graph-resume-same-thread",
            provider_router=router,
        )
    )

    assert result.reply == "恢复完成"
    assert len(context_calls) == 1
    assert len(router.requests) == 2


def test_agent_graph_returns_completed_snapshot_without_provider_call():
    first = StubRouter(
        [AgentModelResponse(intent="ask_question", reply="已经完成", provider="stub")]
    )
    asyncio.run(
        run_agent_graph(
            user_id=DEMO_USER_ID,
            locale="zh-CN",
            message="如何热身？",
            provider_router=first,
            request_id="graph-resume-completed",
        )
    )
    never_called = StubRouter([RuntimeError("provider must not be called")])

    result = asyncio.run(
        agent_graph_module.resume_agent_graph(
            "graph-resume-completed",
            provider_router=never_called,
        )
    )

    assert result.reply == "已经完成"
    assert never_called.requests == []


def test_agent_graph_rejects_a_missing_checkpoint():
    with pytest.raises(agent_graph_module.AgentCheckpointMissingError):
        asyncio.run(agent_graph_module.resume_agent_graph("missing-checkpoint"))


def test_demo_storage_uses_in_memory_agent_checkpointer():
    checkpointer = create_agent_checkpointer(Settings(storage_backend="demo"))

    assert isinstance(checkpointer, MemorySaver)


def test_agent_graph_configures_langsmith_before_compiling(monkeypatch):
    configured = []
    monkeypatch.setattr(
        agent_graph_module,
        "configure_langsmith_tracing",
        lambda settings: configured.append(settings.langsmith_project),
    )
    agent_graph_module.get_agent_graph.cache_clear()

    agent_graph_module.get_agent_graph()

    assert len(configured) == 1


def test_agent_graph_passes_only_anonymous_metadata_to_runtime_config(monkeypatch):
    captured = {}

    class StubGraph:
        async def ainvoke(self, state, config):
            captured["config"] = config
            return {"result": "done"}

    monkeypatch.setattr(agent_graph_module, "get_agent_graph", lambda: StubGraph())
    monkeypatch.setattr(agent_graph_module, "AgentGraphResult", lambda **_: "done")

    result = asyncio.run(
        agent_graph_module.run_agent_graph(
            user_id="demo-user-945",
            locale="zh-CN",
            message="sensitive workout details",
            context={"date": "2026-07-11"},
            request_id="run-123",
        )
    )

    metadata = captured["config"]["metadata"]
    assert result == "done"
    assert metadata["945_request_id"] == "run-123"
    assert metadata["945_user_hash"] != "demo-user-945"
    assert "message" not in metadata
    assert "sensitive workout details" not in str(metadata)


def test_mongo_storage_uses_mongodb_agent_checkpointer(monkeypatch):
    from backend.app.agents import checkpoint

    class StubMongoDBSaver:
        def __init__(self, client, **kwargs):
            self.client = client
            self.kwargs = kwargs

    monkeypatch.setattr(checkpoint, "MongoDBSaver", StubMongoDBSaver)
    settings = Settings(
        storage_backend="mongo",
        mongodb_uri="mongodb://checkpoint-test:27017",
        mongodb_database="945_test",
    )

    checkpointer = create_agent_checkpointer(settings)

    assert isinstance(checkpointer, StubMongoDBSaver)
    assert checkpointer.kwargs["db_name"] == "945_test"
    assert checkpointer.kwargs["checkpoint_collection_name"] == "agent_checkpoints"
    assert checkpointer.kwargs["writes_collection_name"] == "agent_checkpoint_writes"


@pytest.mark.skipif(
    os.getenv("945_RUN_MONGO_INTEGRATION_TESTS") != "1",
    reason="Set 945_RUN_MONGO_INTEGRATION_TESTS=1 to run against local MongoDB.",
)
def test_mongo_agent_checkpointer_persists_checkpoint_between_saver_instances():
    settings = Settings(storage_backend="mongo", mongodb_database="945_checkpoint_test")
    write_config = {"configurable": {"thread_id": "checkpoint-integration", "checkpoint_ns": ""}}
    checkpoint = {
        "v": 1,
        "id": "checkpoint-integration-1",
        "ts": "2026-07-30T00:00:00+00:00",
        "channel_values": {"message": "persisted"},
        "channel_versions": {},
        "versions_seen": {},
        "pending_sends": [],
    }

    first = create_agent_checkpointer(settings)
    first.put(write_config, checkpoint, {}, {})
    second = create_agent_checkpointer(settings)
    restored = second.get(write_config)

    assert restored is not None
    assert restored["channel_values"]["message"] == "persisted"


@pytest.mark.skipif(
    os.getenv("945_RUN_MONGO_INTEGRATION_TESTS") != "1",
    reason="Set 945_RUN_MONGO_INTEGRATION_TESTS=1 to run against local MongoDB.",
)
def test_agent_graph_persists_execution_checkpoints_in_mongo(monkeypatch):
    from pymongo import MongoClient

    from backend.app.agents.checkpoint import get_agent_checkpointer
    from backend.app.core.config import get_settings

    database_name = "945_agent_graph_checkpoint_test"
    client = MongoClient("mongodb://127.0.0.1:27017")
    client.drop_database(database_name)
    monkeypatch.setenv("945_STORAGE_BACKEND", "mongo")
    monkeypatch.setenv("945_MONGODB_DATABASE", database_name)
    get_settings.cache_clear()
    get_agent_checkpointer.cache_clear()
    get_agent_graph.cache_clear()
    try:
        result = asyncio.run(
            run_agent_graph(
                user_id=DEMO_USER_ID,
                locale="en-US",
                message="What should I eat today?",
                context={"date": "2026-07-11"},
            )
        )

        assert result.reply
        assert client[database_name]["agent_checkpoints"].count_documents({}) > 0
        assert client[database_name]["agent_checkpoint_writes"].count_documents({}) > 0
    finally:
        client.drop_database(database_name)
        get_agent_graph.cache_clear()
        get_agent_checkpointer.cache_clear()
        get_settings.cache_clear()


@pytest.mark.skipif(
    os.getenv("945_RUN_MONGO_INTEGRATION_TESTS") != "1",
    reason="Set 945_RUN_MONGO_INTEGRATION_TESTS=1 to run against local MongoDB.",
)
def test_mongo_checkpoint_resumes_after_graph_and_saver_recreation(monkeypatch):
    from pymongo import MongoClient

    from backend.app.agents.checkpoint import get_agent_checkpointer
    from backend.app.core.config import get_settings

    database_name = "945_agent_resume_checkpoint_test"
    client = MongoClient("mongodb://127.0.0.1:27017")
    client.drop_database(database_name)
    monkeypatch.setenv("945_STORAGE_BACKEND", "mongo")
    monkeypatch.setenv("945_MONGODB_DATABASE", database_name)
    get_settings.cache_clear()
    get_agent_checkpointer.cache_clear()
    get_agent_graph.cache_clear()
    router = CrashOnceRouter()
    try:
        with pytest.raises(RuntimeError, match="simulated process interruption"):
            asyncio.run(
                run_agent_graph(
                    user_id=DEMO_USER_ID,
                    locale="zh-CN",
                    message="如何热身？",
                    provider_router=router,
                    request_id="mongo-resume-after-restart",
                )
            )

        get_agent_graph.cache_clear()
        get_agent_checkpointer.cache_clear()
        result = asyncio.run(
            agent_graph_module.resume_agent_graph(
                "mongo-resume-after-restart",
                provider_router=router,
            )
        )

        assert result.reply == "恢复完成"
    finally:
        client.drop_database(database_name)
        get_agent_graph.cache_clear()
        get_agent_checkpointer.cache_clear()
        get_settings.cache_clear()


def test_agent_graph_is_compiled_with_a_checkpoint_saver():
    graph = get_agent_graph()

    assert graph.checkpointer is not None


@pytest.mark.parametrize(
    "message",
    [
        "我现在剧烈疼痛，还应该训练吗？",
        "训练后呼吸困难，需要继续吗？",
        "我刚刚昏倒过，今天还能练吗？",
    ],
)
def test_safety_guard_recognizes_common_high_risk_variants(message):
    assert safety_guard(message) is True


def test_agent_graph_routes_high_risk_to_safety_response_before_provider():
    router = StubRouter(
        [
            AgentModelResponse(
                intent="ask_question",
                reply="should not be used",
                provider="stub",
            )
        ]
    )

    result = asyncio.run(
        run_agent_graph(
            user_id=DEMO_USER_ID,
            locale="zh-CN",
            message="我训练时胸闷眩晕，还能继续冲重量吗？",
            context={"date": "2026-07-11"},
            provider_router=router,
        )
    )

    assert result.intent == "safety_warning"
    assert result.record_draft is None
    assert "暂停训练" in result.reply
    assert router.requests == []


def test_agent_graph_generates_workout_draft_without_writing():
    router = StubRouter(
        [
            AgentModelResponse(
                intent="log_workout",
                reply="",
                provider="stub",
                tool_call=ToolCallProposal(
                    call_id="call-1",
                    name="create_workout_log_draft",
                    arguments={
                        "exercise_name": "深蹲",
                        "sets": 4,
                        "reps": 8,
                        "weight_kg": 80,
                        "effort_note": "今天深蹲 4 组 8 次 80kg",
                    },
                ),
                continuation=ProviderContinuation(
                    output_items=[
                        {
                            "type": "function_call",
                            "call_id": "call-1",
                            "name": "create_workout_log_draft",
                            "arguments": "{}",
                        }
                    ]
                ),
            ),
            AgentModelResponse(
                intent="log_workout",
                reply="训练草稿已整理，请确认后保存。",
                provider="stub",
            ),
        ]
    )

    result = asyncio.run(
        run_agent_graph(
            user_id=DEMO_USER_ID,
            locale="zh-CN",
            message="今天深蹲做了 4 组，每组 8 次，80kg。",
            context={"date": "2026-07-11"},
            provider_router=router,
        )
    )

    assert result.intent == "log_workout"
    assert result.record_draft.type == "workout_log"
    assert result.record_draft.payload["exercise_name"] == "深蹲"
    assert len(router.requests) == 2
    assert router.requests[1].tool_result.call_id == "call-1"


def test_agent_graph_creates_a_local_draft_when_provider_omits_a_record_tool_call():
    router = StubRouter(
        [
            AgentModelResponse(
                intent="ask_question",
                reply="I can prepare that record for you.",
                provider="stub",
            )
        ]
    )

    result = asyncio.run(
        run_agent_graph(
            user_id=DEMO_USER_ID,
            locale="en-US",
            message="I did squat 4 sets 8 reps 80kg, log it.",
            context={"date": "2026-07-11"},
            provider_router=router,
        )
    )

    assert result.intent == "log_workout"
    assert result.record_draft.type == "workout_log"
    assert result.record_draft.payload["exercise_name"] == "Squat"
    assert result.record_draft.payload["sets"] == 4
    assert len(router.requests) == 1


def test_agent_graph_creates_plan_draft_for_confirmed_followup_when_provider_only_replies_in_prose():
    router = StubRouter(
        [
            AgentModelResponse(
                intent="ask_question",
                reply="好的，已经为你生成训练调整预览。",
                provider="stub",
            )
        ]
    )
    conversation = [
        AgentMessage(
            message_id="msg-user-prior",
            user_id=DEMO_USER_ID,
            role="user",
            content="我今天想练胸，能不能推荐动作给我？",
            locale="zh-CN",
            created_at="2026-07-11T08:00:00Z",
        ),
        AgentMessage(
            message_id="msg-agent-prior",
            user_id=DEMO_USER_ID,
            role="agent",
            content="可以，我可以把今天的安排调整成以练胸为主，并生成计划调整草稿。需要我生成吗？",
            locale="zh-CN",
            created_at="2026-07-11T08:00:01Z",
        ),
    ]

    result = asyncio.run(
        run_agent_graph(
            user_id=DEMO_USER_ID,
            locale="zh-CN",
            message="你帮我生成吧",
            context={"date": "2026-07-11"},
            conversation=conversation,
            provider_router=router,
        )
    )

    assert result.intent == "adjust_plan"
    assert result.record_draft is not None
    assert result.record_draft.type == "plan_adjustment"
    assert result.record_draft.payload["adjustment_type"] == "change_schedule"
    assert result.record_draft.payload["target_date"] == "2026-07-11"


def test_agent_graph_falls_back_to_a_plan_draft_after_a_read_tool_returns_dsml_markup():
    router = StubRouter(
        [
            AgentModelResponse(
                intent="ask_question",
                reply="",
                provider="stub",
                tool_call=ToolCallProposal(
                    call_id="call-read-plan",
                    name="get_current_plan",
                    arguments={},
                ),
            ),
            AgentModelResponse(
                intent="ask_question",
                reply=(
                    "我已经为你生成调整草稿。\n\n"
                    "<||DSML||tool_calls>\n"
                    "<||DSML||invoke name=\"draft_workout_record\">\n"
                    "</||DSML||invoke>\n"
                    "</||DSML||tool_calls>"
                ),
                provider="stub",
            ),
        ]
    )

    result = asyncio.run(
        run_agent_graph(
            user_id=DEMO_USER_ID,
            locale="zh-CN",
            message="请把今天训练调整成练胸为主，并生成计划调整草稿。",
            context={"date": "2026-07-11"},
            provider_router=router,
        )
    )

    assert result.intent == "adjust_plan"
    assert result.record_draft is not None
    assert result.record_draft.type == "plan_adjustment"
    assert result.record_draft.requires_confirmation is True
    assert "DSML" not in result.reply


def test_agent_graph_retrieves_knowledge_for_question():
    router = StubRouter(
        [
            AgentModelResponse(
                intent="ask_question",
                reply="深蹲时注意脚跟稳定、核心收紧。",
                provider="stub",
            )
        ]
    )

    result = asyncio.run(
        run_agent_graph(
            user_id=DEMO_USER_ID,
            locale="zh-CN",
            message="深蹲动作要点是什么？",
            context={"date": "2026-07-11"},
            provider_router=router,
        )
    )

    assert result.intent == "ask_question"
    assert result.record_draft is None
    assert any(chunk.metadata["topic"] == "squat" for chunk in result.rag_chunks)
    assert router.requests[0].rag_chunks


def test_agent_graph_rejects_invalid_tool_output_in_production_router():
    router = StubRouter(
        [
            AgentModelResponse(
                intent="log_workout",
                reply="",
                provider="stub",
                tool_call=ToolCallProposal(
                    call_id="call-1",
                    name="create_workout_log_draft",
                    arguments={"exercise_name": "深蹲", "sets": "4"},
                ),
                continuation=ProviderContinuation(
                    output_items=[
                        {
                            "type": "function_call",
                            "call_id": "call-1",
                            "name": "create_workout_log_draft",
                            "arguments": "{}",
                        }
                    ]
                ),
            )
        ]
    )

    with pytest.raises(LLMOutputInvalidError):
        asyncio.run(
            run_agent_graph(
                user_id=DEMO_USER_ID,
                locale="zh-CN",
                message="今天练什么？",
                context={"date": "2026-07-11"},
                provider_router=router,
            )
        )
