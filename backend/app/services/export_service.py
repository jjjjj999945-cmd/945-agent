from backend.app.services.demo_seed import timestamp
from backend.app.services.demo_store import (
    get_advice,
    get_current_user,
    get_profile,
    list_agent_messages,
    list_body_metrics,
    list_daily_checkins,
    list_meal_logs,
    list_plans,
    list_workout_logs,
)


def export_user_data(user_id: str) -> dict | None:
    profile = get_profile(user_id)
    if profile is None:
        return None
    return {
        "schema_version": "1.0",
        "exported_at": timestamp(),
        "user": get_current_user().model_dump(mode="json"),
        "profile": profile.model_dump(mode="json"),
        "plans": [item.model_dump(mode="json") for item in list_plans(user_id) or []],
        "workout_logs": [item.model_dump(mode="json") for item in list_workout_logs(user_id) or []],
        "meal_logs": [item.model_dump(mode="json") for item in list_meal_logs(user_id) or []],
        "body_metrics": [item.model_dump(mode="json") for item in list_body_metrics(user_id) or []],
        "daily_checkins": [item.model_dump(mode="json") for item in list_daily_checkins(user_id) or []],
        "advice": (get_advice(user_id).model_dump(mode="json") if get_advice(user_id) else None),
        "agent_messages": [item.model_dump(mode="json") for item in list_agent_messages(user_id) or []],
    }
