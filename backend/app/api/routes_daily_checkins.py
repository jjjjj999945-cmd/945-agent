from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend.app.api.responses import error, ok
from backend.app.models.domain import DailyCheckinInput
from backend.app.services.demo_store import save_daily_checkin


router = APIRouter(prefix="/api/daily-checkins", tags=["daily_checkins"])


@router.post("")
def create_checkin(input_data: DailyCheckinInput) -> object:
    saved = save_daily_checkin(input_data)
    if saved is None:
        return JSONResponse(
            status_code=404,
            content=error("NOT_FOUND", "Demo user not found.", {"user_id": input_data.user_id})
        )
    return ok(saved.model_dump())
