from fastapi import APIRouter, Header
from fastapi.responses import JSONResponse

from backend.app.api.responses import error, ok
from backend.app.api.auth import authorize_user
from backend.app.data.demo_data import DEMO_USER_ID, TODAY_DATE
from backend.app.services.today_service import get_demo_user, get_today


router = APIRouter(prefix="/api", tags=["demo"])


@router.get("/demo-user")
def demo_user() -> dict[str, object]:
    return ok(get_demo_user().model_dump())


@router.get("/today")
def today(user_id: str = DEMO_USER_ID, date: str = TODAY_DATE, authorization: str | None = Header(default=None)) -> object:
    if denied := authorize_user(user_id, authorization): return denied
    today_data = get_today(user_id=user_id, date=date)
    if today_data is None:
        return JSONResponse(
            status_code=404,
            content=error("NOT_FOUND", "Demo user not found.", {"user_id": user_id})
        )
    return ok(today_data.model_dump())
