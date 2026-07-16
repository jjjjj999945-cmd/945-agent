from datetime import UTC, datetime

from backend.app.data.demo_data import DEMO_USER_ID
from backend.app.models.domain import WorkoutLog, WorkoutLogInput


workout_logs: list[WorkoutLog] = []


def timestamp() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def is_demo_user(user_id: str) -> bool:
    return user_id == DEMO_USER_ID


def create_workout_log(input_data: WorkoutLogInput) -> WorkoutLog | None:
    if not is_demo_user(input_data.user_id):
        return None

    now = timestamp()
    saved = WorkoutLog(
        **input_data.model_dump(),
        workout_log_id=f"workout-{input_data.date}-{len(workout_logs) + 1}",
        created_at=now,
        updated_at=now
    )
    workout_logs.append(saved)
    return saved


def list_workout_logs(user_id: str) -> list[WorkoutLog] | None:
    if not is_demo_user(user_id):
        return None

    return [log for log in workout_logs if log.user_id == user_id]
