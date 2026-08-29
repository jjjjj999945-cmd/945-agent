import asyncio
from datetime import UTC, datetime, timedelta
from time import perf_counter

import pytest

from backend.app.agents.graph import AgentGraphResult
from backend.app.llm.errors import LLMTimeoutError
from backend.app.llm.models import AgentModelResponse
from backend.app.models.domain import AgentChatInput, AgentMessage, AgentRetryInput, AgentRun
from backend.app.services import demo_store
from backend.app.services import agent_service
from backend.app.services import agent_run_lease
from backend.app.services.agent_observability import summarize_agent_runs
from backend.app.services.agent_run_lease import (
    AgentLeaseLostError,
    AgentLeaseToken,
    lease_token_from_run,
)
from backend.app.services.agent_service import create_agent_reply
from backend.app.services.demo_seed import timestamp
from backend.app.services.demo_store import list_agent_messages


def _lease_test_run(run_id: str) -> AgentRun:
    return AgentRun(
        agent_run_id=run_id,
        user_id="demo-user-945",
        status="running",
        started_at="2026-08-21T12:00:00Z",
        request_input=AgentRetryInput(message="继续任务", locale="zh-CN"),
    )


def _lease_test_input() -> AgentChatInput:
    return AgentChatInput(
        user_id="demo-user-945",
        locale="zh-CN",
        message="继续任务",
    )


def _lease_test_result(reply: str) -> AgentGraphResult:
    return AgentGraphResult(
        intent="ask_question",
        reply=reply,
        record_draft=None,
        today_context=None,
        rag_chunks=[],
        provider="stub",
    )


def _lease_test_token() -> AgentLeaseToken:
    return AgentLeaseToken(
        user_id="demo-user-945",
        agent_run_id="run-heartbeat",
        owner="worker-a",
        version=1,
        expires_at=datetime(2026, 8, 21, 12, 1, tzinfo=UTC),
    )


class FailingRouter:
    async def generate(self, request):
        raise LLMTimeoutError("timeout", request_id=request.request_id)

    async def recover(self, request, exc):
        raise exc


class InspectingRouter:
    def __init__(self):
        self.observed_status = None

    async def generate(self, request):
        self.observed_status = demo_store.list_agent_runs(request.user_id)[0].status
        return AgentModelResponse(intent="ask_question", reply="执行完成", provider="stub")

    async def recover(self, request, exc):
        raise exc


class RuntimeCrashOnceRouter:
    def __init__(self):
        self.attempts = 0

    async def generate(self, request):
        self.attempts += 1
        if self.attempts == 1:
            raise RuntimeError("simulated interruption")
        return AgentModelResponse(intent="ask_question", reply="恢复后的回复", provider="stub")

    async def recover(self, request, exc):
        raise exc


class CancelledRouter:
    async def generate(self, request):
        raise asyncio.CancelledError()

    async def recover(self, request, exc):
        raise exc


def test_demo_store_upserts_agent_runs_and_messages_by_id():
    now = timestamp()
    run = AgentRun(
        agent_run_id="run-upsert",
        user_id="demo-user-945",
        status="running",
        started_at=now,
        updated_at=now,
        request_input=AgentRetryInput(message="继续任务", locale="zh-CN"),
    )
    demo_store.save_agent_run(run)
    demo_store.save_agent_run(run.model_copy(update={"status": "interrupted"}))
    message = AgentMessage(
        message_id="msg-agent-run-upsert",
        user_id="demo-user-945",
        role="agent",
        content="旧内容",
        locale="zh-CN",
        created_at=now,
    )
    demo_store.save_agent_message(message)
    demo_store.save_agent_message(message.model_copy(update={"content": "新内容"}))

    assert len(demo_store.list_agent_runs("demo-user-945")) == 1
    assert demo_store.list_agent_runs("demo-user-945")[0].status == "interrupted"
    assert len(demo_store.list_agent_messages("demo-user-945")) == 1
    assert demo_store.list_agent_messages("demo-user-945")[0].content == "新内容"


def test_agent_metrics_exclude_nonterminal_runs_from_rate_and_latency():
    now = timestamp()
    runs = [
        AgentRun(
            agent_run_id="completed",
            user_id="demo-user-945",
            status="completed",
            started_at=now,
            updated_at=now,
            completed_at=now,
            duration_ms=100,
        ),
        AgentRun(
            agent_run_id="failed",
            user_id="demo-user-945",
            status="failed",
            started_at=now,
            updated_at=now,
            completed_at=now,
            duration_ms=300,
            error_code="LLM_TIMEOUT",
        ),
        AgentRun(
            agent_run_id="running",
            user_id="demo-user-945",
            status="running",
            started_at=now,
            updated_at=now,
            duration_ms=900,
        ),
        AgentRun(
            agent_run_id="interrupted",
            user_id="demo-user-945",
            status="interrupted",
            started_at=now,
            updated_at=now,
            duration_ms=700,
        ),
    ]

    metrics = summarize_agent_runs(runs)

    assert (metrics.total_runs, metrics.completed_runs, metrics.failed_runs) == (4, 1, 1)
    assert (metrics.running_runs, metrics.interrupted_runs) == (1, 1)
    assert metrics.success_rate == 0.5
    assert metrics.average_duration_ms == 200


def test_agent_service_persists_running_before_provider_execution():
    router = InspectingRouter()
    reply = asyncio.run(
        create_agent_reply(
            AgentChatInput(
                user_id="demo-user-945",
                locale="zh-CN",
                message="如何热身？",
            ),
            provider_router=router,
        )
    )

    runs = demo_store.list_agent_runs("demo-user-945")
    assert router.observed_status == "running"
    assert len(runs) == 1
    assert runs[0].status == "completed"
    assert reply.message_id == f"msg-agent-{runs[0].agent_run_id}"


def test_agent_service_resumes_interrupted_run_in_place_without_writes():
    router = RuntimeCrashOnceRouter()
    input_data = AgentChatInput(
        user_id="demo-user-945",
        locale="zh-CN",
        message="今天深蹲 4 组，每组 8 次，80kg，帮我记录",
    )
    with pytest.raises(RuntimeError, match="simulated interruption"):
        asyncio.run(create_agent_reply(input_data, provider_router=router))

    interrupted = demo_store.list_agent_runs("demo-user-945")[0]
    assert interrupted.status == "interrupted"
    assert list_agent_messages("demo-user-945") == []

    reply = asyncio.run(
        agent_service.resume_agent_run(
            "demo-user-945",
            interrupted.agent_run_id,
            provider_router=router,
        )
    )

    runs = demo_store.list_agent_runs("demo-user-945")
    messages = list_agent_messages("demo-user-945")
    assert len(runs) == 1
    assert runs[0].agent_run_id == interrupted.agent_run_id
    assert runs[0].status == "completed"
    assert runs[0].resume_count == 1
    assert [message.message_id for message in messages] == [
        f"msg-user-{interrupted.agent_run_id}",
        f"msg-agent-{interrupted.agent_run_id}",
    ]
    assert reply.message_id == f"msg-agent-{interrupted.agent_run_id}"
    assert demo_store.list_workout_logs("demo-user-945") == []
    assert demo_store.list_meal_logs("demo-user-945") == []


def test_agent_service_marks_orphaned_running_run_interrupted():
    now = timestamp()
    demo_store.save_agent_run(
        AgentRun(
            agent_run_id="orphaned-run",
            user_id="demo-user-945",
            status="running",
            started_at=now,
            updated_at=now,
            request_input=AgentRetryInput(message="继续任务", locale="zh-CN"),
        )
    )

    runs = agent_service.list_user_agent_runs("demo-user-945")

    assert runs[0].status == "interrupted"


def test_agent_service_keeps_a_foreign_live_lease_running(monkeypatch):
    now = datetime(2026, 8, 21, 12, 0, tzinfo=UTC)
    monkeypatch.setattr(demo_store, "_agent_lease_now", lambda: now)
    run = demo_store.create_agent_run_with_lease(
        AgentRun(
            agent_run_id="foreign-live-run",
            user_id="demo-user-945",
            status="running",
            started_at="2026-08-21T12:00:00Z",
        ),
        "other-worker",
    )
    assert run is not None

    listed = agent_service.list_user_agent_runs(run.user_id)

    assert listed is not None
    assert listed[0].status == "running"


def test_stale_worker_cannot_publish_messages_after_a_new_lease(monkeypatch):
    now = datetime(2026, 8, 21, 12, 0, tzinfo=UTC)
    monkeypatch.setattr(demo_store, "_agent_lease_now", lambda: now)
    first = demo_store.create_agent_run_with_lease(
        _lease_test_run("stale-run"),
        "worker-a",
    )
    assert first is not None
    first_token = lease_token_from_run(first)
    now += timedelta(seconds=61)
    demo_store.interrupt_expired_agent_runs(first.user_id)
    second = demo_store.acquire_agent_run_lease(
        first.user_id,
        first.agent_run_id,
        "worker-b",
    )

    result = agent_service._complete_agent_run(
        first,
        first_token,
        _lease_test_input(),
        _lease_test_result("旧结果"),
        perf_counter(),
    )

    assert result is None
    assert demo_store.list_agent_messages(first.user_id) == []
    assert second is not None
    assert second.lease_version == 2


def test_agent_service_allows_only_one_concurrent_resume(monkeypatch):
    interrupted = _lease_test_run("concurrent-resume").model_copy(
        update={"status": "interrupted"}
    )
    demo_store.save_agent_run(interrupted)
    started = asyncio.Event()
    release = asyncio.Event()
    calls = 0

    monkeypatch.setattr(
        agent_service,
        "get_safe_resume_checkpoint_id",
        lambda run_id, before_version: "checkpoint-safe",
    )

    async def slow_resume(*args, **kwargs):
        nonlocal calls
        calls += 1
        started.set()
        await release.wait()
        return _lease_test_result("恢复完成")

    monkeypatch.setattr(agent_service, "resume_agent_graph", slow_resume)

    async def scenario():
        first = asyncio.create_task(
            agent_service.resume_agent_run(
                interrupted.user_id,
                interrupted.agent_run_id,
            )
        )
        await started.wait()
        with pytest.raises(agent_service.AgentRunResumeError) as captured:
            await agent_service.resume_agent_run(
                interrupted.user_id,
                interrupted.agent_run_id,
            )
        assert captured.value.code == "AGENT_RUN_ACTIVE"
        release.set()
        await first

    asyncio.run(scenario())

    saved = demo_store.list_agent_runs(interrupted.user_id)[0]
    assert calls == 1
    assert saved.resume_count == 1
    assert saved.status == "completed"


def test_agent_service_fails_explicitly_when_checkpoint_is_missing():
    now = timestamp()
    demo_store.save_agent_run(
        AgentRun(
            agent_run_id="missing-checkpoint",
            user_id="demo-user-945",
            status="interrupted",
            started_at=now,
            updated_at=now,
            request_input=AgentRetryInput(message="继续任务", locale="zh-CN"),
        )
    )

    with pytest.raises(agent_service.AgentRunResumeError) as captured:
        asyncio.run(
            agent_service.resume_agent_run("demo-user-945", "missing-checkpoint")
        )

    run = demo_store.list_agent_runs("demo-user-945")[0]
    assert captured.value.code == "AGENT_CHECKPOINT_MISSING"
    assert run.status == "failed"
    assert run.error_code == "AGENT_CHECKPOINT_MISSING"
    assert run.retry_input.message == "继续任务"


def test_agent_service_marks_cancelled_execution_interrupted():
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(
            create_agent_reply(
                AgentChatInput(
                    user_id="demo-user-945",
                    locale="zh-CN",
                    message="如何热身？",
                ),
                provider_router=CancelledRouter(),
            )
        )

    run = demo_store.list_agent_runs("demo-user-945")[0]
    assert run.status == "interrupted"
    assert list_agent_messages("demo-user-945") == []


def test_lease_session_cancels_work_when_renewal_loses_ownership(monkeypatch):
    token = _lease_test_token()
    monkeypatch.setattr(agent_run_lease, "renew_agent_run_lease", lambda _: None)

    async def never_finishes():
        await asyncio.Event().wait()

    with pytest.raises(AgentLeaseLostError):
        asyncio.run(
            agent_run_lease.AgentLeaseSession(
                token,
                heartbeat_seconds=0,
            ).run(never_finishes())
        )


def test_message_repair_reads_the_final_checkpoint_without_running_the_graph(
    monkeypatch,
):
    run = _lease_test_run("repair-messages").model_copy(
        update={
            "status": "completed",
            "lease_version": 1,
            "messages_persisted": False,
            "completed_at": "2026-08-21T12:01:00Z",
        }
    )
    demo_store.save_agent_run(run)
    monkeypatch.setattr(
        agent_service,
        "load_completed_agent_graph_result",
        lambda run_id, lease_version: _lease_test_result("检查点回复"),
    )

    async def forbidden_graph_call(*args, **kwargs):
        raise AssertionError("message repair must not execute the graph")

    monkeypatch.setattr(agent_service, "run_agent_graph", forbidden_graph_call)
    monkeypatch.setattr(agent_service, "resume_agent_graph", forbidden_graph_call)

    messages = agent_service.list_user_agent_messages(run.user_id)

    assert messages is not None
    assert [message.message_id for message in messages] == [
        f"msg-user-{run.agent_run_id}",
        f"msg-agent-{run.agent_run_id}",
    ]
    repaired = demo_store.list_agent_runs(run.user_id)[0]
    assert repaired.messages_persisted is True


def test_completed_run_repairs_messages_after_persistence_failure(monkeypatch):
    input_data = AgentChatInput(
        user_id="demo-user-945",
        locale="zh-CN",
        message="如何热身？",
    )
    real_save_agent_message = agent_service.save_agent_message

    def fail_message_persistence(message):
        raise RuntimeError("simulated message persistence failure")

    monkeypatch.setattr(
        agent_service,
        "save_agent_message",
        fail_message_persistence,
    )

    reply = asyncio.run(agent_service.create_agent_reply(input_data))

    assert reply is not None
    runs = demo_store.list_agent_runs(input_data.user_id)
    assert runs is not None
    assert runs[0].status == "completed"
    assert runs[0].messages_persisted is False
    assert demo_store.list_agent_messages(input_data.user_id) == []

    monkeypatch.setattr(
        agent_service,
        "save_agent_message",
        real_save_agent_message,
    )
    messages = agent_service.list_user_agent_messages(input_data.user_id)

    assert messages is not None
    assert [message.content for message in messages] == [
        "如何热身？",
        reply.content,
    ]
    repaired = demo_store.list_agent_runs(input_data.user_id)[0]
    assert repaired.messages_persisted is True


@pytest.mark.parametrize("status", ["completed", "failed"])
def test_agent_service_rejects_resuming_a_terminal_run_without_messages(status):
    now = timestamp()
    run = AgentRun(
        agent_run_id=f"terminal-{status}",
        user_id="demo-user-945",
        status=status,
        started_at=now,
        updated_at=now,
        completed_at=now,
        request_input=AgentRetryInput(message="继续任务", locale="zh-CN"),
    )
    demo_store.save_agent_run(run)

    with pytest.raises(agent_service.AgentRunResumeError) as captured:
        asyncio.run(agent_service.resume_agent_run(run.user_id, run.agent_run_id))

    assert captured.value.code == "AGENT_RUN_NOT_RESUMABLE"
    assert list_agent_messages(run.user_id) == []


def test_agent_service_does_not_save_partial_turn_on_provider_error():
    input_data = AgentChatInput(
        user_id="demo-user-945",
        locale="zh-CN",
        message="今天练什么？",
    )

    with pytest.raises(LLMTimeoutError):
        asyncio.run(create_agent_reply(input_data, provider_router=FailingRouter()))

    assert list_agent_messages("demo-user-945") == []
    runs = demo_store.list_agent_runs("demo-user-945")
    assert len(runs) == 1
    assert runs[0].status == "failed"
    assert runs[0].error_code == "LLM_TIMEOUT"
    assert runs[0].retry_input.message == input_data.message


def test_agent_service_saves_a_completed_run_without_model_reasoning():
    input_data = AgentChatInput(
        user_id="demo-user-945",
        locale="zh-CN",
        message="How should I warm up before a squat session?",
    )

    reply = asyncio.run(create_agent_reply(input_data))

    runs = demo_store.list_agent_runs("demo-user-945")
    assert reply is not None
    assert len(runs) == 1
    assert runs[0].status == "completed"
    assert runs[0].intent == "ask_question"
    assert runs[0].provider == "deterministic"
    assert runs[0].draft_type is None
    assert runs[0].error_code is None
    assert runs[0].input_tokens == 0
    assert runs[0].output_tokens == 0
    assert runs[0].logical_generations == 1
    assert runs[0].http_attempts == 0


def test_retrying_a_failed_run_creates_a_new_completed_run_without_writing_records():
    input_data = AgentChatInput(
        user_id="demo-user-945",
        locale="zh-CN",
        message="今天深蹲做了 4 组，每组 8 次，80kg，帮我记录",
    )

    with pytest.raises(LLMTimeoutError):
        asyncio.run(create_agent_reply(input_data, provider_router=FailingRouter()))

    failed_run = demo_store.list_agent_runs("demo-user-945")[0]
    reply = asyncio.run(agent_service.retry_agent_run("demo-user-945", failed_run.agent_run_id))

    runs = demo_store.list_agent_runs("demo-user-945")
    assert reply.record_draft.type == "workout_log"
    assert [message.role for message in list_agent_messages("demo-user-945")] == ["user", "agent"]
    assert [run.status for run in runs] == ["failed", "completed"]
    assert runs[1].retry_of_agent_run_id == failed_run.agent_run_id
    assert demo_store.list_workout_logs("demo-user-945") == []
