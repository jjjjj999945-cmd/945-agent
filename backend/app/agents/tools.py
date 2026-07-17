from backend.app.data.demo_data import DEMO_USER_ID, TODAY_DATE
from backend.app.models.domain import AdviceStatus, AgentAdvice, MealLog, RecordDraft, TodayResponseData, UserProfile, WorkoutLog
from backend.app.services.demo_store import (
    get_advice,
    get_profile,
    list_meal_logs,
    list_workout_logs,
    update_advice_status,
)
from backend.app.services.plan_service import get_current_plan
from backend.app.services.today_service import get_today


def get_profile_tool(user_id: str = DEMO_USER_ID) -> UserProfile | None:
    return get_profile(user_id)


def get_today_context(user_id: str = DEMO_USER_ID, date: str = TODAY_DATE) -> TodayResponseData | None:
    return get_today(user_id=user_id, date=date)


def get_current_plan_tool(user_id: str = DEMO_USER_ID):
    return get_current_plan(user_id=user_id)


def list_recent_workout_logs(user_id: str = DEMO_USER_ID, limit: int = 10) -> list[WorkoutLog] | None:
    logs = list_workout_logs(user_id)
    if logs is None:
        return None
    return logs[-limit:]


def list_recent_meal_logs(user_id: str = DEMO_USER_ID, limit: int = 10) -> list[MealLog] | None:
    logs = list_meal_logs(user_id)
    if logs is None:
        return None
    return logs[-limit:]


def build_workout_log_draft(
    exercise_name: str,
    sets: int,
    reps: int,
    weight_kg: float | None,
    effort_note: str,
) -> RecordDraft:
    return RecordDraft(
        type="workout_log",
        requires_confirmation=True,
        payload={
            "exercise_name": exercise_name,
            "sets": sets,
            "reps": reps,
            "weight_kg": weight_kg,
            "effort_note": effort_note,
        },
    )


def create_workout_log_draft(message: str) -> RecordDraft | None:
    normalized = message.lower()
    if "深蹲" not in normalized and "squat" not in normalized:
        return None
    return build_workout_log_draft(
        exercise_name="深蹲" if "深蹲" in normalized else "Squat",
        sets=4,
        reps=8,
        weight_kg=80,
        effort_note=message,
    )


def build_meal_log_draft(meal_name: str, note: str) -> RecordDraft:
    return RecordDraft(
        type="meal_log",
        requires_confirmation=True,
        payload={"meal_name": meal_name, "note": note},
    )


def create_meal_log_draft(message: str, locale: str = "zh-CN") -> RecordDraft | None:
    normalized = message.lower()
    if "吃" not in normalized and "meal" not in normalized and "food" not in normalized:
        return None
    return build_meal_log_draft(
        meal_name="手动记录" if locale == "zh-CN" else "Manual entry",
        note=message,
    )


def build_plan_adjustment_draft(adjustment_type: str, reason: str) -> RecordDraft:
    return RecordDraft(
        type="plan_adjustment",
        requires_confirmation=True,
        payload={"adjustment_type": adjustment_type, "reason": reason},
    )


def create_plan_adjustment_draft(message: str) -> RecordDraft | None:
    normalized = message.lower()
    if "调整" not in normalized and "adjust" not in normalized:
        return None
    return build_plan_adjustment_draft("reduce_intensity", message)


def accept_advice(user_id: str, advice_id: str, accepted_status: AdviceStatus = "accepted") -> AgentAdvice | None:
    return update_advice_status(user_id, advice_id, accepted_status)


def get_advice_context(user_id: str = DEMO_USER_ID):
    return get_advice(user_id)
