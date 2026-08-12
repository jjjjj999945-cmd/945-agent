from fastapi import Header
from fastapi.responses import JSONResponse

from backend.app.api.responses import error
from backend.app.core.config import get_settings
from backend.app.services.auth_service import get_session


def authorize_user(user_id: str, authorization: str | None = Header(default=None)) -> JSONResponse | None:
    """Allow demo requests without a token, but never allow an authenticated token to cross user boundaries."""
    if authorization is None:
        if get_settings().auth_required:
            return JSONResponse(status_code=401, content=error("UNAUTHORIZED", "A valid session is required."))
        return None
    if not authorization.startswith("Bearer "):
        return JSONResponse(status_code=401, content=error("UNAUTHORIZED", "Bearer token is required."))
    token = authorization.removeprefix("Bearer ")
    user = get_session(token)
    if user is None:
        return JSONResponse(status_code=401, content=error("UNAUTHORIZED", "A valid session is required."))
    if user.user_id != user_id:
        return JSONResponse(status_code=403, content=error("FORBIDDEN", "The session cannot access another user's data."))
    return None
