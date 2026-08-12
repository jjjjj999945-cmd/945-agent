from fastapi import APIRouter, Header
from fastapi.responses import JSONResponse

from backend.app.api.responses import error, ok
from backend.app.api.auth import authorize_user
from backend.app.data.demo_data import DEMO_USER_ID
from backend.app.models.domain import PlanAcceptInput, PlanAdjustmentInput, PlanGenerateInput
from backend.app.services.plan_service import ProfileIncompleteError, accept_plan, adjust_plan, generate_plan, get_current_plan_response


router = APIRouter(prefix="/api/plans", tags=["plans"])


@router.get("/current")
def current_plan(user_id: str = DEMO_USER_ID, authorization: str | None = Header(default=None)) -> object:
    if denied := authorize_user(user_id, authorization): return denied
    response = get_current_plan_response(user_id=user_id)
    if response is None:
        return JSONResponse(
            status_code=404,
            content=error("NOT_FOUND", "No active plan found. Generate and accept a plan first.", {"user_id": user_id})
        )
    return ok(response.model_dump())


@router.post("/generate")
def generate(input_data: PlanGenerateInput, authorization: str | None = Header(default=None)) -> object:
    if denied := authorize_user(input_data.user_id, authorization): return denied
    try:
        plan = generate_plan(input_data)
    except ProfileIncompleteError as exc:
        return JSONResponse(
            status_code=409,
            content=error("PROFILE_INCOMPLETE", "Profile is incomplete.", {"missing_fields": exc.missing_fields}),
        )
    if plan is None:
        return JSONResponse(status_code=404, content=error("NOT_FOUND", "Demo user not found.", {"user_id": input_data.user_id}))
    return ok(plan.model_dump())


@router.post("/{plan_id}/accept")
def accept(plan_id: str, input_data: PlanAcceptInput, authorization: str | None = Header(default=None)) -> object:
    if denied := authorize_user(input_data.user_id, authorization): return denied
    plan = accept_plan(input_data.user_id, plan_id)
    if plan is None:
        return JSONResponse(status_code=404, content=error("NOT_FOUND", "Draft plan not found.", {"plan_id": plan_id}))
    return ok(plan.model_dump())


@router.post("/{plan_id}/adjust")
def adjust(plan_id: str, input_data: PlanAdjustmentInput, authorization: str | None = Header(default=None)) -> object:
    if denied := authorize_user(input_data.user_id, authorization): return denied
    plan = adjust_plan(plan_id, input_data)
    if plan is None:
        return JSONResponse(status_code=404, content=error("NOT_FOUND", "Active plan not found.", {"plan_id": plan_id}))
    return ok(plan.model_dump())
