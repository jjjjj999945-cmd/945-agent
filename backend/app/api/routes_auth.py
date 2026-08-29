from fastapi import APIRouter, Cookie, Header, Request
from fastapi.responses import JSONResponse

from backend.app.api.responses import error, ok
from backend.app.core.config import get_settings
from backend.app.models.domain import LoginInput, PasswordChangeInput, RegisterInput
from backend.app.services.auth_service import (
    change_password,
    get_authenticated_session,
    get_session,
    is_login_rate_limited,
    list_device_sessions,
    login_with_refresh,
    refresh_authenticated_session,
    register_with_refresh,
    revoke_current_device_session,
    revoke_sessions,
)


router = APIRouter(prefix="/api/auth", tags=["auth"])
_REFRESH_COOKIE = "945_refresh_token"


def _device_name(request: Request) -> str:
    return request.headers.get("user-agent", "Unknown device")[:160]


def _set_refresh_cookie(response: JSONResponse, raw_token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        _REFRESH_COOKIE,
        raw_token,
        httponly=True,
        samesite="lax",
        path="/api/auth",
        secure=settings.app_env == "production",
        max_age=settings.auth_refresh_token_ttl_seconds,
    )


def _clear_refresh_cookie(response: JSONResponse) -> None:
    response.delete_cookie(_REFRESH_COOKIE, path="/api/auth")


def _session_response(session_data: object, raw_refresh_token: str) -> JSONResponse:
    response = JSONResponse(content=ok(session_data))
    _set_refresh_cookie(response, raw_refresh_token)
    return response


def _authorized_session(authorization: str | None) -> object | None:
    token = authorization.removeprefix("Bearer ") if authorization and authorization.startswith("Bearer ") else ""
    return get_authenticated_session(token)


@router.post("/register")
def register_user(input_data: RegisterInput, request: Request) -> object:
    result = register_with_refresh(input_data, device_name=_device_name(request))
    if result is None:
        return JSONResponse(status_code=409, content=error("REGISTRATION_FAILED", "Email already exists or password is too short."))
    session, raw_refresh_token = result
    return _session_response(session.model_dump(), raw_refresh_token)


@router.post("/login")
def login_user(input_data: LoginInput, request: Request) -> object:
    if is_login_rate_limited(input_data.email.strip().lower()):
        return JSONResponse(status_code=429, content=error("LOGIN_RATE_LIMITED", "Too many failed login attempts. Try again later."))
    result = login_with_refresh(input_data, device_name=_device_name(request))
    if result is None:
        return JSONResponse(status_code=401, content=error("INVALID_CREDENTIALS", "Email or password is incorrect."))
    session, raw_refresh_token = result
    return _session_response(session.model_dump(), raw_refresh_token)


@router.post("/refresh")
def refresh_session(refresh_token: str | None = Cookie(default=None, alias=_REFRESH_COOKIE)) -> object:
    result = refresh_authenticated_session(refresh_token) if refresh_token else None
    if result is None:
        response = JSONResponse(status_code=401, content=error("UNAUTHORIZED", "A valid session is required."))
        _clear_refresh_cookie(response)
        return response
    session, raw_refresh_token = result
    return _session_response(session.model_dump(), raw_refresh_token)


@router.get("/me")
def current_user(authorization: str | None = Header(default=None)) -> object:
    token = authorization.removeprefix("Bearer ") if authorization else ""
    user = get_session(token)
    if user is None:
        return JSONResponse(status_code=401, content=error("UNAUTHORIZED", "A valid session is required."))
    return ok(user.model_dump())


@router.get("/sessions")
def device_sessions(authorization: str | None = Header(default=None)) -> object:
    session = _authorized_session(authorization)
    if session is None:
        return JSONResponse(status_code=401, content=error("UNAUTHORIZED", "A valid session is required."))
    return ok([item.model_dump() for item in list_device_sessions(session.user.user_id, session.session_id)])


@router.delete("/sessions/{session_id}")
def revoke_device_session(session_id: str, authorization: str | None = Header(default=None)) -> object:
    session = _authorized_session(authorization)
    if session is None:
        return JSONResponse(status_code=401, content=error("UNAUTHORIZED", "A valid session is required."))
    if not revoke_current_device_session(session.user.user_id, session_id):
        return JSONResponse(status_code=404, content=error("NOT_FOUND", "Device session not found."))
    return ok({"revoked": True})


@router.post("/change-password")
def update_password(input_data: PasswordChangeInput, authorization: str | None = Header(default=None)) -> object:
    session = _authorized_session(authorization)
    if session is None:
        return JSONResponse(status_code=401, content=error("UNAUTHORIZED", "A valid session is required."))
    if not change_password(session.user.user_id, input_data):
        return JSONResponse(status_code=400, content=error("PASSWORD_CHANGE_FAILED", "Current password is incorrect or the new password is too short."))
    response = JSONResponse(content=ok({"changed": True}))
    _clear_refresh_cookie(response)
    return response


@router.post("/logout")
def logout(authorization: str | None = Header(default=None)) -> object:
    session = _authorized_session(authorization)
    if session is None:
        return JSONResponse(status_code=401, content=error("UNAUTHORIZED", "A valid session is required."))
    revoke_current_device_session(session.user.user_id, session.session_id)
    response = JSONResponse(content=ok({"logged_out": True}))
    _clear_refresh_cookie(response)
    return response


@router.post("/logout-all")
def logout_all(authorization: str | None = Header(default=None)) -> object:
    session = _authorized_session(authorization)
    if session is None:
        return JSONResponse(status_code=401, content=error("UNAUTHORIZED", "A valid session is required."))
    revoke_sessions(session.user.user_id)
    response = JSONResponse(content=ok({"logged_out": True}))
    _clear_refresh_cookie(response)
    return response
