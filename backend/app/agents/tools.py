import re

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
    sets_match = re.search(r"(\d+)\s*(?:组|sets?)", normalized)
    reps_match = re.search(r"(\d+)\s*(?:次|reps?)", normalized)
    weight_match = re.search(r"(\d+(?:\.\d+)?)\s*kg", normalized)
    return build_workout_log_draft(
        exercise_name="深蹲" if "深蹲" in normalized else "Squat",
        sets=int(sets_match.group(1)) if sets_match else 4,
        reps=int(reps_match.group(1)) if reps_match else 8,
        weight_kg=float(weight_match.group(1)) if weight_match else None,
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


def build_plan_adjustment_draft(
    adjustment_type: str,
    reason: str,
    target_date: str | None = None,
    target_exercise_id: str | None = None,
    target_meal_id: str | None = None,
    replacement_name: str | None = None,
) -> RecordDraft:
    payload = {"adjustment_type": adjustment_type, "reason": reason}
    for key, value in {
        "target_date": target_date,
        "target_exercise_id": target_exercise_id,
        "target_meal_id": target_meal_id,
        "replacement_name": replacement_name,
    }.items():
        if value is not None:
            payload[key] = value
    return RecordDraft(
        type="plan_adjustment",
        requires_confirmation=True,
        payload=payload,
    )


def create_plan_adjustment_draft(
    message: str,
    target_date: str | None = None,
    *,
    reason: str | None = None,
) -> RecordDraft | None:
    normalized = message.lower()
    adjustment_terms = ("调整", "adjust", "跳过", "skip", "换餐", "替换餐", "swap meal", "换动作", "替换动作", "swap exercise")
    if not any(term in normalized for term in adjustment_terms):
        return None
    if "跳过" in normalized or "skip" in normalized:
        adjustment_type = "skip_workout"
    elif "换餐" in normalized or "替换餐" in normalized or "swap meal" in normalized:
        adjustment_type = "swap_meal"
    elif "换动作" in normalized or "替换动作" in normalized or "swap exercise" in normalized:
        adjustment_type = "swap_exercise"
    elif "增加强度" in normalized or "increase intensity" in normalized:
        adjustment_type = "increase_intensity"
    elif "调整成" in normalized or "改成" in normalized or "为主" in normalized or "change schedule" in normalized:
        adjustment_type = "change_schedule"
    else:
        adjustment_type = "reduce_intensity"
    return build_plan_adjustment_draft(
        adjustment_type,
        reason or message,
        target_date=target_date or TODAY_DATE,
    )


def accept_advice(user_id: str, advice_id: str, accepted_status: AdviceStatus = "accepted") -> AgentAdvice | None:
    return update_advice_status(user_id, advice_id, accepted_status)


def get_advice_context(user_id: str = DEMO_USER_ID):
    return get_advice(user_id)
