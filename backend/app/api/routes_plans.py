from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend.app.api.responses import error, ok
from backend.app.data.demo_data import DEMO_USER_ID
from backend.app.services.plan_service import get_current_plan


router = APIRouter(prefix="/api/plans", tags=["plans"])


@router.get("/current")
def current_plan(user_id: str = DEMO_USER_ID) -> object:
    plan = get_current_plan(user_id=user_id)
    if plan is None:
        return JSONResponse(
            status_code=404,
            content=error("NOT_FOUND", "Demo user not found.", {"user_id": user_id})
        )
    return ok(plan.model_dump())
