import base64
import hashlib
import hmac
import json
import secrets
from datetime import UTC, datetime, timedelta

from backend.app.core.config import get_settings
from backend.app.models.domain import AuthCredential, AuthDeviceSession, AuthDeviceSessionSummary, AuthSession, LoginInput, PasswordChangeInput, RegisterInput, User
from backend.app.services import demo_store
from backend.app.services.demo_seed import timestamp
from backend.app.services.demo_store import _active_repository_store


_credentials: dict[str, AuthCredential] = {}
_users: dict[str, User] = {}
_failed_login_attempts: dict[str, list[datetime]] = {}


def _password_hash(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 310_000).hex()


def _token(user_id: str, session_version: int, session_id: str) -> str:
    settings = get_settings()
    payload = {
        "sub": user_id,
        "ver": session_version,
        "sid": session_id,
        "exp": int((datetime.now(UTC) + timedelta(seconds=settings.auth_access_token_ttl_seconds)).timestamp()),
    }
    encoded = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).rstrip(b"=")
    signature = hmac.new(settings.auth_secret.get_secret_value().encode(), encoded, hashlib.sha256).digest()
    return f"{encoded.decode()}.{base64.urlsafe_b64encode(signature).rstrip(b'=').decode()}"


def _refresh_token_hash(raw_token: str) -> str:
    secret = get_settings().auth_secret.get_secret_value().encode()
    return hmac.new(secret, raw_token.encode(), hashlib.sha256).hexdigest()


def _timestamp_at(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _is_expired(value: str) -> bool:
    return datetime.fromisoformat(value.replace("Z", "+00:00")) <= datetime.now(UTC)


def _create_device_session(session: AuthDeviceSession) -> AuthDeviceSession | None:
    store = _active_repository_store()
    return store.create_auth_device_session(session) if store else demo_store.create_auth_device_session(session)


def _get_device_session_by_hash(refresh_token_hash: str) -> AuthDeviceSession | None:
    store = _active_repository_store()
    return store.get_auth_device_session_by_hash(refresh_token_hash) if store else demo_store.get_auth_device_session_by_hash(refresh_token_hash)


def _get_device_session(user_id: str, session_id: str) -> AuthDeviceSession | None:
    store = _active_repository_store()
    return store.get_auth_device_session(user_id, session_id) if store else demo_store.get_auth_device_session(user_id, session_id)


def _rotate_device_session(session_id: str, old_hash: str, new_hash: str) -> AuthDeviceSession | None:
    store = _active_repository_store()
    return store.rotate_auth_device_session(session_id, old_hash, new_hash) if store else demo_store.rotate_auth_device_session(session_id, old_hash, new_hash)


def _revoke_all_device_sessions(user_id: str) -> int:
    store = _active_repository_store()
    return store.revoke_all_auth_device_sessions(user_id) if store else demo_store.revoke_all_auth_device_sessions(user_id)


def _create_authenticated_session(
    user: User,
    credential: AuthCredential,
    device_name: str,
) -> tuple[AuthSession, str] | None:
    raw_refresh_token = secrets.token_urlsafe(48)
    now = datetime.now(UTC)
    device_session = AuthDeviceSession(
        session_id=f"session-{secrets.token_urlsafe(18)}",
        user_id=user.user_id,
        refresh_token_hash=_refresh_token_hash(raw_refresh_token),
        device_name=device_name,
        created_at=_timestamp_at(now),
        last_used_at=_timestamp_at(now),
        expires_at=_timestamp_at(now + timedelta(seconds=get_settings().auth_refresh_token_ttl_seconds)),
    )
    if _create_device_session(device_session) is None:
        return None
    return (
        AuthSession(
            access_token=_token(user.user_id, credential.session_version, device_session.session_id),
            session_id=device_session.session_id,
            user=user,
        ),
        raw_refresh_token,
    )


def _find_credential_by_user_id(user_id: str) -> AuthCredential | None:
    store = _active_repository_store()
    if store is not None:
        credentials = store.repository.list_models("auth_credentials", AuthCredential, {"user_id": user_id})
        return credentials[0] if credentials else None
    return next((item for item in _credentials.values() if item.user_id == user_id), None)


def register_with_refresh(
    input_data: RegisterInput,
    *,
    device_name: str = "Unknown device",
) -> tuple[AuthSession, str] | None:
    email = input_data.email.strip().lower()
    store = _active_repository_store()
    if not input_data.display_name.strip() or len(input_data.password) < 8:
        return None
    if store is not None and store.get_credential(email) is not None:
        return None
    if store is None and email in _credentials:
        return None
    now = timestamp()
    user = User(user_id=f"user-{secrets.token_urlsafe(12)}", display_name=input_data.display_name.strip(), locale="zh-CN", unit_system="metric", created_at=now, updated_at=now)
    salt = secrets.token_hex(16)
    credential = AuthCredential(email=email, user_id=user.user_id, password_hash=_password_hash(input_data.password, salt), password_salt=salt, created_at=now)
    if store is not None:
        store.save_registered_user(user, credential)
    else:
        _credentials[email] = credential
        _users[user.user_id] = user
        demo_store.register_demo_user(user)
    return _create_authenticated_session(user, credential, device_name)


def register(input_data: RegisterInput) -> AuthSession | None:
    result = register_with_refresh(input_data)
    return result[0] if result else None


def login_with_refresh(
    input_data: LoginInput,
    *,
    device_name: str = "Unknown device",
) -> tuple[AuthSession, str] | None:
    email = input_data.email.strip().lower()
    if is_login_rate_limited(email):
        return None
    store = _active_repository_store()
    credential = store.get_credential(email) if store else _credentials.get(email)
    if credential is None or not hmac.compare_digest(credential.password_hash, _password_hash(input_data.password, credential.password_salt)):
        record_failed_login(email)
        return None
    user = store.get_user(credential.user_id) if store else _users.get(credential.user_id)
    _failed_login_attempts.pop(email, None)
    return _create_authenticated_session(user, credential, device_name) if user else None


def login(input_data: LoginInput) -> AuthSession | None:
    result = login_with_refresh(input_data)
    return result[0] if result else None


def refresh_authenticated_session(raw_refresh_token: str) -> tuple[AuthSession, str] | None:
    old_hash = _refresh_token_hash(raw_refresh_token)
    device_session = _get_device_session_by_hash(old_hash)
    if device_session is None or _is_expired(device_session.expires_at):
        return None
    credential = _find_credential_by_user_id(device_session.user_id)
    store = _active_repository_store()
    user = store.get_user(device_session.user_id) if store else _users.get(device_session.user_id)
    if credential is None or user is None:
        return None
    new_refresh_token = secrets.token_urlsafe(48)
    if _rotate_device_session(device_session.session_id, old_hash, _refresh_token_hash(new_refresh_token)) is None:
        return None
    return (
        AuthSession(
            access_token=_token(user.user_id, credential.session_version, device_session.session_id),
            session_id=device_session.session_id,
            user=user,
        ),
        new_refresh_token,
    )


def is_login_rate_limited(email: str) -> bool:
    settings = get_settings()
    cutoff = datetime.now(UTC) - timedelta(seconds=settings.auth_login_window_seconds)
    attempts = [item for item in _failed_login_attempts.get(email, []) if item >= cutoff]
    _failed_login_attempts[email] = attempts
    return len(attempts) >= settings.auth_login_max_attempts


def record_failed_login(email: str) -> None:
    _failed_login_attempts.setdefault(email, []).append(datetime.now(UTC))


def change_password(user_id: str, input_data: PasswordChangeInput) -> bool:
    store = _active_repository_store()
    credential = _find_credential_by_user_id(user_id)
    if credential is None or len(input_data.new_password) < 8:
        return False
    if not hmac.compare_digest(credential.password_hash, _password_hash(input_data.current_password, credential.password_salt)):
        return False
    updated = credential.model_copy(update={"password_salt": secrets.token_hex(16), "session_version": credential.session_version + 1})
    updated = updated.model_copy(update={"password_hash": _password_hash(input_data.new_password, updated.password_salt)})
    if store is not None:
        store.save_credential(updated)
    else:
        _credentials[updated.email] = updated
    _revoke_all_device_sessions(user_id)
    return True


def revoke_sessions(user_id: str) -> bool:
    store = _active_repository_store()
    credential = _find_credential_by_user_id(user_id)
    if credential is None:
        return False
    updated = credential.model_copy(update={"session_version": credential.session_version + 1})
    if store is not None:
        store.save_credential(updated)
    else:
        _credentials[updated.email] = updated
    _revoke_all_device_sessions(user_id)
    return True


def revoke_current_device_session(user_id: str, session_id: str) -> bool:
    store = _active_repository_store()
    return store.revoke_auth_device_session(user_id, session_id) if store else demo_store.revoke_auth_device_session(user_id, session_id)


def _validated_token_payload(token: str) -> dict[str, object] | None:
    try:
        encoded, signature = token.split(".", 1)
        expected = hmac.new(get_settings().auth_secret.get_secret_value().encode(), encoded.encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(expected, base64.urlsafe_b64decode(signature + "=" * (-len(signature) % 4))):
            return None
        payload = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
        if payload["exp"] < int(datetime.now(UTC).timestamp()):
            return None
        if not isinstance(payload.get("sub"), str) or not isinstance(payload.get("sid"), str):
            return None
        credential = _find_credential_by_user_id(payload["sub"])
        if credential is None or payload.get("ver") != credential.session_version:
            return None
        device_session = _get_device_session(payload["sub"], payload["sid"])
        if device_session is None or _is_expired(device_session.expires_at):
            return None
        return payload
    except (KeyError, ValueError, json.JSONDecodeError):
        return None


def get_authenticated_session(token: str) -> AuthSession | None:
    payload = _validated_token_payload(token)
    if payload is None:
        return None
    store = _active_repository_store()
    user = store.get_user(payload["sub"]) if store else _users.get(payload["sub"])
    credential = _find_credential_by_user_id(payload["sub"])
    if user is None or credential is None:
        return None
    return AuthSession(
        access_token=token,
        session_id=payload["sid"],
        user=user,
    )


def get_session(token: str) -> User | None:
    session = get_authenticated_session(token)
    return session.user if session else None


def list_device_sessions(user_id: str, current_session_id: str) -> list[AuthDeviceSessionSummary]:
    store = _active_repository_store()
    sessions = store.list_auth_device_sessions(user_id) if store else demo_store.list_auth_device_sessions(user_id)
    return [
        AuthDeviceSessionSummary.from_session(item, current_session_id=current_session_id)
        for item in sessions
    ]
