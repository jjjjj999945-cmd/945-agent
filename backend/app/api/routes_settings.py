from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend.app.api.responses import error, ok
from backend.app.data.demo_data import DEMO_USER_ID
from backend.app.models.domain import SettingsPatchInput
from backend.app.services.export_service import export_user_data
from backend.app.services.demo_store import get_settings, update_settings


router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/export")
def export_data(user_id: str = DEMO_USER_ID) -> object:
    data = export_user_data(user_id)
    if data is None:
        return JSONResponse(status_code=404, content=error("NOT_FOUND", "Demo user not found.", {"user_id": user_id}))
    return ok(data)


@router.get("")
def read_settings(user_id: str = DEMO_USER_ID) -> object:
    settings = get_settings(user_id)
    if settings is None:
        return JSONResponse(
            status_code=404,
            content=error("NOT_FOUND", "Demo user not found.", {"user_id": user_id})
        )
    return ok(settings.model_dump())


@router.patch("")
def patch_settings(input_data: SettingsPatchInput) -> object:
    settings = update_settings(input_data)
    if settings is None:
        return JSONResponse(
            status_code=404,
            content=error("NOT_FOUND", "Demo user not found.", {"user_id": input_data.user_id})
        )
    return ok(settings.model_dump())
