import base64
import hashlib
import hmac
import json
import secrets
from datetime import UTC, datetime, timedelta

from backend.app.core.config import get_settings
from backend.app.models.domain import AuthCredential, AuthSession, LoginInput, PasswordChangeInput, RegisterInput, User
from backend.app.services.demo_seed import timestamp
from backend.app.services.demo_store import _active_repository_store


_credentials: dict[str, AuthCredential] = {}
_users: dict[str, User] = {}
_failed_login_attempts: dict[str, list[datetime]] = {}


def _password_hash(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 310_000).hex()


def _token(user_id: str, session_version: int) -> str:
    settings = get_settings()
    payload = {
        "sub": user_id,
        "ver": session_version,
        "exp": int((datetime.now(UTC) + timedelta(seconds=settings.auth_token_ttl_seconds)).timestamp()),
    }
    encoded = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).rstrip(b"=")
    signature = hmac.new(settings.auth_secret.get_secret_value().encode(), encoded, hashlib.sha256).digest()
    return f"{encoded.decode()}.{base64.urlsafe_b64encode(signature).rstrip(b'=').decode()}"


def register(input_data: RegisterInput) -> AuthSession | None:
    email = input_data.email.strip().lower()
    store = _active_repository_store()
    if store is None or not input_data.display_name.strip() or len(input_data.password) < 8 or store.get_credential(email):
        return None
    now = timestamp()
    user = User(
        user_id=f"user-{secrets.token_urlsafe(12)}",
        display_name=input_data.display_name.strip(),
        locale="zh-CN",
        unit_system="metric",
        created_at=now,
        updated_at=now,
    )
    salt = secrets.token_hex(16)
    credential = AuthCredential(
        email=email,
        user_id=user.user_id,
        password_hash=_password_hash(input_data.password, salt),
        password_salt=salt,
        created_at=now,
    )
    store.save_registered_user(user, credential)
    return AuthSession(access_token=_token(user.user_id, credential.session_version), user=user)


def login(input_data: LoginInput) -> AuthSession | None:
    email = input_data.email.strip().lower()
    store = _active_repository_store()
    credential = store.get_credential(email) if store else _credentials.get(email)
    if credential is None or not hmac.compare_digest(credential.password_hash, _password_hash(input_data.password, credential.password_salt)):
        _failed_login_attempts.setdefault(email, []).append(datetime.now(UTC))
        return None
    user = store.get_user(credential.user_id) if store else _users.get(credential.user_id)
    _failed_login_attempts.pop(email, None)
    return AuthSession(access_token=_token(user.user_id, credential.session_version), user=user) if user else None


def is_login_rate_limited(email: str) -> bool:
    settings = get_settings()
    cutoff = datetime.now(UTC) - timedelta(seconds=settings.auth_login_window_seconds)
    attempts = [attempt for attempt in _failed_login_attempts.get(email, []) if attempt >= cutoff]
    _failed_login_attempts[email] = attempts
    return len(attempts) >= settings.auth_login_max_attempts


def _credential_for_user(user_id: str) -> tuple[AuthCredential | None, object | None]:
    store = _active_repository_store()
    if store is None:
        return next((item for item in _credentials.values() if item.user_id == user_id), None), None
    credentials = store.repository.list_models("auth_credentials", AuthCredential, {"user_id": user_id})
    return (credentials[0] if credentials else None), store


def change_password(user_id: str, input_data: PasswordChangeInput) -> bool:
    credential, store = _credential_for_user(user_id)
    if credential is None or len(input_data.new_password) < 8:
        return False
    if not hmac.compare_digest(credential.password_hash, _password_hash(input_data.current_password, credential.password_salt)):
        return False
    updated = credential.model_copy(update={"password_salt": secrets.token_hex(16), "session_version": credential.session_version + 1})
    updated = updated.model_copy(update={"password_hash": _password_hash(input_data.new_password, updated.password_salt)})
    if store:
        store.save_credential(updated)
    else:
        _credentials[updated.email] = updated
    return True


def revoke_sessions(user_id: str) -> bool:
    credential, store = _credential_for_user(user_id)
    if credential is None:
        return False
    updated = credential.model_copy(update={"session_version": credential.session_version + 1})
    if store:
        store.save_credential(updated)
    else:
        _credentials[updated.email] = updated
    return True


def get_session(token: str) -> User | None:
    try:
        encoded, signature = token.split(".", 1)
        expected = hmac.new(get_settings().auth_secret.get_secret_value().encode(), encoded.encode(), hashlib.sha256).digest()
        received = base64.urlsafe_b64decode(signature + "=" * (-len(signature) % 4))
        if not hmac.compare_digest(expected, received):
            return None
        payload = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
        if payload["exp"] < int(datetime.now(UTC).timestamp()):
            return None
        credential, store = _credential_for_user(payload["sub"])
        if credential is None or payload.get("ver") != credential.session_version:
            return None
        return store.get_user(payload["sub"]) if store else _users.get(payload["sub"])
    except (KeyError, ValueError, json.JSONDecodeError, UnicodeDecodeError):
        return None
