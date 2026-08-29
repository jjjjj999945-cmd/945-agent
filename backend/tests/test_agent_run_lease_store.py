from datetime import UTC, datetime, timedelta

from backend.app.models.domain import AgentRetryInput, AgentRun
from backend.app.services import demo_store
from backend.app.services.agent_run_lease import lease_token_from_run


def test_agent_run_builds_an_internal_lease_token():
    expires_at = datetime(2026, 8, 21, 12, 1, tzinfo=UTC)
    run = AgentRun(
        agent_run_id="run-lease-1",
        user_id="demo-user-945",
        status="running",
        started_at="2026-08-21T12:00:00Z",
        lease_owner="worker-a:attempt-1",
        lease_version=1,
        lease_expires_at=expires_at,
    )

    token = lease_token_from_run(run)

    assert token.agent_run_id == run.agent_run_id
    assert token.owner == "worker-a:attempt-1"
    assert token.version == 1
    assert token.expires_at == expires_at


def test_demo_lease_expires_then_only_one_new_owner_can_resume(monkeypatch):
    now = datetime(2026, 8, 21, 12, 0, tzinfo=UTC)
    monkeypatch.setattr(demo_store, "_agent_lease_now", lambda: now)
    run = AgentRun(
        agent_run_id="run-race",
        user_id="demo-user-945",
        status="running",
        started_at="2026-08-21T12:00:00Z",
        request_input=AgentRetryInput(message="继续任务", locale="zh-CN"),
    )

    first = demo_store.create_agent_run_with_lease(run, "worker-a")
    assert first is not None
    first_token = lease_token_from_run(first)
    assert (
        demo_store.acquire_agent_run_lease(
            run.user_id,
            run.agent_run_id,
            "worker-b",
        )
        is None
    )

    now += timedelta(seconds=61)
    assert demo_store.interrupt_expired_agent_runs(run.user_id) == 1

    second = demo_store.acquire_agent_run_lease(
        run.user_id,
        run.agent_run_id,
        "worker-b",
    )
    assert second is not None
    assert second.lease_version == 2
    assert (
        demo_store.acquire_agent_run_lease(
            run.user_id,
            run.agent_run_id,
            "worker-c",
        )
        is None
    )

    stale_completion = first.model_copy(update={"status": "completed"})
    assert (
        demo_store.transition_agent_run_with_lease(first_token, stale_completion)
        is None
    )


def test_demo_lease_renewal_and_checkpoint_require_the_current_token(monkeypatch):
    now = datetime(2026, 8, 21, 12, 0, tzinfo=UTC)
    monkeypatch.setattr(demo_store, "_agent_lease_now", lambda: now)
    created = demo_store.create_agent_run_with_lease(
        AgentRun(
            agent_run_id="run-renew",
            user_id="demo-user-945",
            status="running",
            started_at="2026-08-21T12:00:00Z",
        ),
        "worker-a",
    )
    assert created is not None
    token = lease_token_from_run(created)

    now += timedelta(seconds=10)
    renewed = demo_store.renew_agent_run_lease(token)
    assert renewed is not None
    renewed_token = lease_token_from_run(renewed)
    pinned = demo_store.set_agent_run_resume_checkpoint(
        renewed_token,
        "checkpoint-1",
    )

    assert pinned is not None
    assert pinned.resume_checkpoint_id == "checkpoint-1"
    assert demo_store.agent_run_lease_is_valid(lease_token_from_run(pinned))

    stale_token = renewed_token.__class__(
        user_id=renewed_token.user_id,
        agent_run_id=renewed_token.agent_run_id,
        owner="worker-b",
        version=renewed_token.version,
        expires_at=renewed_token.expires_at,
    )
    assert demo_store.renew_agent_run_lease(stale_token) is None
    assert (
        demo_store.set_agent_run_resume_checkpoint(stale_token, "checkpoint-stale")
        is None
    )


def test_legacy_runs_without_lease_fields_keep_terminal_states_and_interrupt_running():
    for status in ("completed", "failed"):
        demo_store.save_agent_run(
            AgentRun(
                agent_run_id=f"legacy-{status}",
                user_id="demo-user-945",
                status=status,
                started_at="2026-08-21T12:00:00Z",
            )
        )
    demo_store.save_agent_run(
        AgentRun(
            agent_run_id="legacy-running",
            user_id="demo-user-945",
            status="running",
            started_at="2026-08-21T12:00:00Z",
        )
    )

    assert demo_store.interrupt_expired_agent_runs("demo-user-945") == 1
    states = {
        run.agent_run_id: run.status
        for run in demo_store.list_agent_runs("demo-user-945") or []
    }
    assert states == {
        "legacy-completed": "completed",
        "legacy-failed": "failed",
        "legacy-running": "interrupted",
    }

    legacy_interrupted = AgentRun(
        agent_run_id="legacy-interrupted",
        user_id="demo-user-945",
        status="interrupted",
        started_at="2026-08-21T12:00:00Z",
    )
    demo_store.save_agent_run(legacy_interrupted)
    resumed = demo_store.acquire_agent_run_lease(
        legacy_interrupted.user_id,
        legacy_interrupted.agent_run_id,
        "worker-a",
    )

    assert resumed is not None
    assert resumed.lease_version == 1
