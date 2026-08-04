from fastapi import APIRouter, Header
from fastapi.responses import JSONResponse

from backend.app.api.responses import error, ok
from backend.app.api.auth import authorize_user
from backend.app.models.domain import DailyCheckinInput
from backend.app.services.demo_store import save_daily_checkin


router = APIRouter(prefix="/api/daily-checkins", tags=["daily_checkins"])


@router.post("")
def create_checkin(input_data: DailyCheckinInput, authorization: str | None = Header(default=None)) -> object:
    if denied := authorize_user(input_data.user_id, authorization): return denied
    saved = save_daily_checkin(input_data)
    if saved is None:
        return JSONResponse(
            status_code=404,
            content=error("NOT_FOUND", "Demo user not found.", {"user_id": input_data.user_id})
        )
    return ok(saved.model_dump())
