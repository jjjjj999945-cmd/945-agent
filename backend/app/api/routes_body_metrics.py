from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend.app.api.responses import error, ok
from backend.app.data.demo_data import DEMO_USER_ID
from backend.app.models.domain import BodyMetricInput
from backend.app.services.demo_store import list_body_metrics, save_body_metric


router = APIRouter(prefix="/api/body-metrics", tags=["body_metrics"])


@router.post("")
def create_metric(input_data: BodyMetricInput) -> object:
    saved = save_body_metric(input_data)
    if saved is None:
        return JSONResponse(
            status_code=404,
            content=error("NOT_FOUND", "Demo user not found.", {"user_id": input_data.user_id})
        )
    return ok(saved.model_dump())


@router.get("")
def list_metrics(user_id: str = DEMO_USER_ID) -> object:
    metrics = list_body_metrics(user_id)
    if metrics is None:
        return JSONResponse(
            status_code=404,
            content=error("NOT_FOUND", "Demo user not found.", {"user_id": user_id})
        )
    return ok([metric.model_dump() for metric in metrics])
