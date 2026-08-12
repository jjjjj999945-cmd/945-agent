from fastapi import APIRouter, Header
from fastapi.responses import JSONResponse

from backend.app.api.responses import error, ok
from backend.app.api.auth import authorize_user
from backend.app.data.demo_data import DEMO_USER_ID
from backend.app.models.domain import SettingsPatchInput
from backend.app.services.export_service import export_user_data
from backend.app.services.demo_store import get_settings, update_settings


router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/export")
def export_data(user_id: str = DEMO_USER_ID, authorization: str | None = Header(default=None)) -> object:
    if denied := authorize_user(user_id, authorization): return denied
    data = export_user_data(user_id)
    if data is None:
        return JSONResponse(status_code=404, content=error("NOT_FOUND", "Demo user not found.", {"user_id": user_id}))
    return ok(data)


@router.get("")
def read_settings(user_id: str = DEMO_USER_ID, authorization: str | None = Header(default=None)) -> object:
    if denied := authorize_user(user_id, authorization): return denied
    settings = get_settings(user_id)
    if settings is None:
        return JSONResponse(
            status_code=404,
            content=error("NOT_FOUND", "Demo user not found.", {"user_id": user_id})
        )
    return ok(settings.model_dump())


@router.patch("")
def patch_settings(input_data: SettingsPatchInput, authorization: str | None = Header(default=None)) -> object:
    if denied := authorize_user(input_data.user_id, authorization): return denied
    settings = update_settings(input_data)
    if settings is None:
        return JSONResponse(
            status_code=404,
            content=error("NOT_FOUND", "Demo user not found.", {"user_id": input_data.user_id})
        )
    return ok(settings.model_dump())
