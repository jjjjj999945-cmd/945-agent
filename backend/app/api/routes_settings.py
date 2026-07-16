from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend.app.api.responses import error, ok
from backend.app.data.demo_data import DEMO_USER_ID
from backend.app.models.domain import SettingsPatchInput
from backend.app.services.demo_store import get_settings, update_settings


router = APIRouter(prefix="/api/settings", tags=["settings"])


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
