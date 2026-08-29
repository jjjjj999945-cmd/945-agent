from backend.app.models.domain import AuthDeviceSession, AuthDeviceSessionSummary


def test_device_session_summary_never_exposes_refresh_token_hash():
    session = AuthDeviceSession(
        session_id="session-1",
        user_id="user-1",
        refresh_token_hash="secret-hash",
        device_name="Chrome on Windows",
        created_at="2026-08-29T00:00:00Z",
        last_used_at="2026-08-29T00:00:00Z",
        expires_at="2026-09-28T00:00:00Z",
    )

    summary = AuthDeviceSessionSummary.from_session(session, current_session_id="session-1")

    assert "refresh_token_hash" not in summary.model_dump()
    assert summary.current is True
