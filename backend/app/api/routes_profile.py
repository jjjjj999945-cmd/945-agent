from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend.app.api.responses import error, ok
from backend.app.models.domain import ProfileCreateInput, ProfilePatchInput
from backend.app.services.demo_store import get_profile, save_profile, update_profile


router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.post("")
def create_profile(input_data: ProfileCreateInput) -> object:
    profile = save_profile(input_data)
    if profile is None:
        return JSONResponse(
            status_code=404,
            content=error("NOT_FOUND", "Demo user not found.", {"user_id": input_data.user_id})
        )
    return ok(profile.model_dump())


@router.get("/{user_id}")
def read_profile(user_id: str) -> object:
    profile = get_profile(user_id)
    if profile is None:
        return JSONResponse(
            status_code=404,
            content=error("NOT_FOUND", "Demo user not found.", {"user_id": user_id})
        )
    return ok(profile.model_dump())


@router.patch("/{user_id}")
def patch_profile(user_id: str, input_data: ProfilePatchInput) -> object:
    profile = update_profile(user_id, input_data)
    if profile is None:
        return JSONResponse(
            status_code=404,
            content=error("NOT_FOUND", "Demo user not found.", {"user_id": user_id})
        )
    return ok(profile.model_dump())
