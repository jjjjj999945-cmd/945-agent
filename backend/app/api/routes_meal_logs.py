from fastapi import APIRouter, Header
from fastapi.responses import JSONResponse

from backend.app.api.responses import error, ok
from backend.app.api.auth import authorize_user
from backend.app.data.demo_data import DEMO_USER_ID
from backend.app.models.domain import ConfirmPlannedMealInput, ManualMealLogInput
from backend.app.services.demo_store import confirm_planned_meal, create_manual_meal_log, is_demo_user, list_meal_logs


router = APIRouter(prefix="/api/meal-logs", tags=["meal_logs"])


@router.post("/confirm-planned-meal")
def confirm_meal(input_data: ConfirmPlannedMealInput, authorization: str | None = Header(default=None)) -> object:
    if denied := authorize_user(input_data.user_id, authorization):
        return denied
    if not is_demo_user(input_data.user_id):
        return JSONResponse(
            status_code=404,
            content=error("NOT_FOUND", "Demo user not found.", {"user_id": input_data.user_id})
        )

    saved = confirm_planned_meal(input_data)
    if saved is None:
        return JSONResponse(
            status_code=404,
            content=error("NOT_FOUND", "Planned meal not found.", input_data.model_dump())
        )
    return ok(saved.model_dump())


@router.post("")
def create_log(input_data: ManualMealLogInput, authorization: str | None = Header(default=None)) -> object:
    if denied := authorize_user(input_data.user_id, authorization):
        return denied
    saved = create_manual_meal_log(input_data)
    if saved is None:
        return JSONResponse(
            status_code=404,
            content=error("NOT_FOUND", "Demo user not found.", {"user_id": input_data.user_id})
        )
    return ok(saved.model_dump())


@router.get("")
def list_logs(user_id: str = DEMO_USER_ID, authorization: str | None = Header(default=None)) -> object:
    if denied := authorize_user(user_id, authorization):
        return denied
    logs = list_meal_logs(user_id)
    if logs is None:
        return JSONResponse(
            status_code=404,
            content=error("NOT_FOUND", "Demo user not found.", {"user_id": user_id})
        )
    return ok([log.model_dump() for log in logs])
