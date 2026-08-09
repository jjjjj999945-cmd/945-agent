from fastapi import APIRouter, Header
from fastapi.responses import JSONResponse

from backend.app.api.responses import error, ok
from backend.app.core.config import get_settings
from backend.app.models.domain import LoginInput, PasswordChangeInput, RegisterInput
from backend.app.services.auth_service import change_password, get_session, is_login_rate_limited, login, register, revoke_sessions


router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register")
def register_user(input_data: RegisterInput) -> object:
    if get_settings().storage_backend != "mongo":
        return JSONResponse(status_code=503, content=error("STORAGE_CONFIG_ERROR", "User registration requires MongoDB storage."))
    session = register(input_data)
    if session is None:
        return JSONResponse(status_code=409, content=error("REGISTRATION_FAILED", "Email already exists or password is too short."))
    return ok(session.model_dump())


@router.post("/login")
def login_user(input_data: LoginInput) -> object:
    if is_login_rate_limited(input_data.email.strip().lower()):
        return JSONResponse(status_code=429, content=error("LOGIN_RATE_LIMITED", "Too many failed login attempts. Try again later."))
    session = login(input_data)
    if session is None:
        return JSONResponse(status_code=401, content=error("INVALID_CREDENTIALS", "Email or password is incorrect."))
    return ok(session.model_dump())


@router.get("/me")
def current_user(authorization: str | None = Header(default=None)) -> object:
    user = get_session(authorization.removeprefix("Bearer ")) if authorization else None
    if user is None:
        return JSONResponse(status_code=401, content=error("UNAUTHORIZED", "A valid session is required."))
    return ok(user.model_dump())


@router.post("/change-password")
def update_password(input_data: PasswordChangeInput, authorization: str | None = Header(default=None)) -> object:
    user = get_session(authorization.removeprefix("Bearer ")) if authorization and authorization.startswith("Bearer ") else None
    if user is None:
        return JSONResponse(status_code=401, content=error("UNAUTHORIZED", "A valid session is required."))
    if not change_password(user.user_id, input_data):
        return JSONResponse(status_code=400, content=error("PASSWORD_CHANGE_FAILED", "Current password is incorrect or the new password is too short."))
    return ok({"changed": True})


@router.post("/logout")
def logout(authorization: str | None = Header(default=None)) -> object:
    user = get_session(authorization.removeprefix("Bearer ")) if authorization and authorization.startswith("Bearer ") else None
    if user is None:
        return JSONResponse(status_code=401, content=error("UNAUTHORIZED", "A valid session is required."))
    revoke_sessions(user.user_id)
    return ok({"logged_out": True})
