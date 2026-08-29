from backend.app.models.domain import AuthDeviceSession, AuthDeviceSessionSummary, RegisterInput
from backend.app.services.auth_service import (
    get_session,
    refresh_authenticated_session,
    register_with_refresh,
    revoke_current_device_session,
)


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


def test_refresh_rotates_and_old_refresh_token_cannot_be_reused():
    session, first_refresh = register_with_refresh(
        RegisterInput(
            display_name="Refresh User",
            email="refresh-user@example.com",
            password="secure-pass-945",
        )
    )

    refreshed = refresh_authenticated_session(first_refresh)

    assert refreshed is not None
    second_session, second_refresh = refreshed
    assert first_refresh != second_refresh
    assert second_session.session_id == session.session_id
    assert refresh_authenticated_session(first_refresh) is None


def test_revoked_device_access_token_is_immediately_invalid():
    session, _refresh = register_with_refresh(
        RegisterInput(
            display_name="Revoked User",
            email="revoked-user@example.com",
            password="secure-pass-945",
        )
    )

    assert get_session(session.access_token) is not None
    assert revoke_current_device_session(session.user.user_id, session.session_id) is True
    assert get_session(session.access_token) is None
