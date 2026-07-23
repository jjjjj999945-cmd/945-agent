import base64
import hashlib
import hmac
import json
import secrets
from datetime import UTC, datetime, timedelta

from backend.app.core.config import get_settings
from backend.app.models.domain import AuthCredential, AuthSession, LoginInput, RegisterInput, User
from backend.app.services.demo_seed import timestamp
from backend.app.services.demo_store import _active_repository_store


_credentials: dict[str, AuthCredential] = {}
_users: dict[str, User] = {}


def _password_hash(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 310_000).hex()


def _token(user_id: str) -> str:
    settings = get_settings()
    payload = {"sub": user_id, "exp": int((datetime.now(UTC) + timedelta(seconds=settings.auth_token_ttl_seconds)).timestamp())}
    encoded = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).rstrip(b"=")
    signature = hmac.new(settings.auth_secret.get_secret_value().encode(), encoded, hashlib.sha256).digest()
    return f"{encoded.decode()}.{base64.urlsafe_b64encode(signature).rstrip(b'=').decode()}"


def register(input_data: RegisterInput) -> AuthSession | None:
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
    return AuthSession(access_token=_token(user.user_id), user=user)


def login(input_data: LoginInput) -> AuthSession | None:
    store = _active_repository_store()
    credential = store.get_credential(input_data.email.strip().lower()) if store else _credentials.get(input_data.email.strip().lower())
    if credential is None or not hmac.compare_digest(credential.password_hash, _password_hash(input_data.password, credential.password_salt)):
        return None
    user = store.get_user(credential.user_id) if store else _users.get(credential.user_id)
    return AuthSession(access_token=_token(user.user_id), user=user) if user else None


def get_session(token: str) -> User | None:
    try:
        encoded, signature = token.split(".", 1)
        expected = hmac.new(get_settings().auth_secret.get_secret_value().encode(), encoded.encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(expected, base64.urlsafe_b64decode(signature + "=" * (-len(signature) % 4))):
            return None
        payload = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
        if payload["exp"] < int(datetime.now(UTC).timestamp()):
            return None
        store = _active_repository_store()
        return store.get_user(payload["sub"]) if store else _users.get(payload["sub"])
    except (KeyError, ValueError, json.JSONDecodeError):
        return None
