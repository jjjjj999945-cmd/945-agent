from fastapi import APIRouter, Header
from fastapi.responses import JSONResponse

from backend.app.api.responses import error, ok
from backend.app.api.auth import authorize_user
from backend.app.data.demo_data import DEMO_USER_ID
from backend.app.models.domain import AdviceStatusInput
from backend.app.services.demo_store import get_advice, is_demo_user, update_advice_status


router = APIRouter(prefix="/api/advice", tags=["advice"])


@router.get("")
def read_advice(user_id: str = DEMO_USER_ID, authorization: str | None = Header(default=None)) -> object:
    if denied := authorize_user(user_id, authorization):
        return denied
    advice = get_advice(user_id)
    if advice is None:
        return JSONResponse(
            status_code=404,
            content=error("NOT_FOUND", "Demo user not found.", {"user_id": user_id})
        )
    return ok(advice.model_dump())


@router.patch("/{advice_id}/status")
def patch_advice_status(advice_id: str, input_data: AdviceStatusInput, authorization: str | None = Header(default=None)) -> object:
    if denied := authorize_user(input_data.user_id, authorization):
        return denied
    if not is_demo_user(input_data.user_id):
        return JSONResponse(
            status_code=404,
            content=error("NOT_FOUND", "Demo user not found.", {"user_id": input_data.user_id})
        )

    advice = update_advice_status(input_data.user_id, advice_id, input_data.accepted_status)
    if advice is None:
        return JSONResponse(
            status_code=404,
            content=error("NOT_FOUND", "Advice not found.", {"user_id": input_data.user_id, "advice_id": advice_id})
        )
    return ok(advice.model_dump())
