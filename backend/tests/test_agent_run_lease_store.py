from datetime import UTC, datetime

from backend.app.models.domain import AgentRun
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
