from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend.app.api.responses import error, ok
from backend.app.data.demo_data import DEMO_USER_ID
from backend.app.models.domain import PlanAcceptInput, PlanAdjustmentInput, PlanGenerateInput
from backend.app.services.plan_service import accept_plan, adjust_plan, generate_plan, get_current_plan


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


@router.post("/generate")
def generate(input_data: PlanGenerateInput) -> object:
    plan = generate_plan(input_data)
    if plan is None:
        return JSONResponse(status_code=404, content=error("NOT_FOUND", "Demo user not found.", {"user_id": input_data.user_id}))
    return ok(plan.model_dump())


@router.post("/{plan_id}/accept")
def accept(plan_id: str, input_data: PlanAcceptInput) -> object:
    plan = accept_plan(input_data.user_id, plan_id)
    if plan is None:
        return JSONResponse(status_code=404, content=error("NOT_FOUND", "Draft plan not found.", {"plan_id": plan_id}))
    return ok(plan.model_dump())


@router.post("/{plan_id}/adjust")
def adjust(plan_id: str, input_data: PlanAdjustmentInput) -> object:
    plan = adjust_plan(plan_id, input_data)
    if plan is None:
        return JSONResponse(status_code=404, content=error("NOT_FOUND", "Active plan not found.", {"plan_id": plan_id}))
    return ok(plan.model_dump())
