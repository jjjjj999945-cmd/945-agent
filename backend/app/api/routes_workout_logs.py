from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend.app.api.responses import error, ok
from backend.app.data.demo_data import DEMO_USER_ID
from backend.app.models.domain import WorkoutLogInput
from backend.app.services.demo_store import create_workout_log, list_workout_logs


router = APIRouter(prefix="/api/workout-logs", tags=["workout_logs"])


@router.post("")
def create_log(input_data: WorkoutLogInput) -> object:
    saved = create_workout_log(input_data)
    if saved is None:
        return JSONResponse(
            status_code=404,
            content=error("NOT_FOUND", "Demo user not found.", {"user_id": input_data.user_id})
        )
    return ok(saved.model_dump())


@router.get("")
def list_logs(user_id: str = DEMO_USER_ID) -> object:
    logs = list_workout_logs(user_id)
    if logs is None:
        return JSONResponse(
            status_code=404,
            content=error("NOT_FOUND", "Demo user not found.", {"user_id": user_id})
        )
    return ok([log.model_dump() for log in logs])
