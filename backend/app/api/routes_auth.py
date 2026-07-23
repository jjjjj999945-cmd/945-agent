from fastapi import APIRouter, Header
from fastapi.responses import JSONResponse

from backend.app.api.responses import error, ok
from backend.app.models.domain import LoginInput, RegisterInput
from backend.app.services.auth_service import get_session, login, register

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register")
def register_user(input_data: RegisterInput) -> object:
    session = register(input_data)
    if session is None:
        return JSONResponse(status_code=409, content=error("REGISTRATION_FAILED", "Email already exists or password is too short."))
    return ok(session.model_dump())


@router.post("/login")
def login_user(input_data: LoginInput) -> object:
    session = login(input_data)
    if session is None:
        return JSONResponse(status_code=401, content=error("INVALID_CREDENTIALS", "Email or password is incorrect."))
    return ok(session.model_dump())


@router.get("/me")
def current_user(authorization: str | None = Header(default=None)) -> object:
    token = authorization.removeprefix("Bearer ") if authorization else ""
    user = get_session(token)
    if user is None:
        return JSONResponse(status_code=401, content=error("UNAUTHORIZED", "A valid session is required."))
    return ok(user.model_dump())
