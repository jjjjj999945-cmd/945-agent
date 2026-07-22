from copy import deepcopy

from backend.app.data.demo_data import DEMO_USER_ID, TODAY_DATE
from backend.app.models.domain import Plan, PlanAdjustmentInput, PlanGenerateInput, WorkoutPlan
from backend.app.services.demo_seed import timestamp
from backend.app.services.demo_store import _active_repository_store, get_current_plan as get_demo_current_plan, list_plans, save_plan


def get_current_plan(user_id: str = DEMO_USER_ID) -> Plan | None:
    store = _active_repository_store()
    if store:
        return store.get_current_plan(user_id)
    return get_demo_current_plan(user_id)


def _plan_id(kind: str) -> str:
    return f"plan-{TODAY_DATE}-{kind}-{timestamp().replace(':', '').replace('-', '')[-10:]}"


def generate_plan(input_data: PlanGenerateInput) -> Plan | None:
    current = get_current_plan(input_data.user_id)
    if current is None:
        return None
    now = timestamp()
    draft = deepcopy(current).model_copy(update={
        "plan_id": _plan_id("draft"),
        "goal": input_data.goal or current.goal,
        "status": "draft",
        "generated_by": "mock",
        "created_at": now,
        "updated_at": now,
    })
    store = _active_repository_store()
    return store.save_plan(draft) if store else save_plan(draft)


def accept_plan(user_id: str, plan_id: str) -> Plan | None:
    store = _active_repository_store()
    plans = store.list_plans(user_id) if store else list_plans(user_id)
    candidate = next((plan for plan in plans or [] if plan.plan_id == plan_id and plan.status == "draft"), None)
    if candidate is None:
        return None
    current = get_current_plan(user_id)
    if current:
        (store.save_plan if store else save_plan)(current.model_copy(update={"status": "archived", "updated_at": timestamp()}))
    return (store.save_plan if store else save_plan)(candidate.model_copy(update={"status": "active", "updated_at": timestamp()}))


def adjust_plan(plan_id: str, input_data: PlanAdjustmentInput) -> Plan | None:
    current = get_current_plan(input_data.user_id)
    if current is None or current.plan_id != plan_id:
        return None
    days = deepcopy(current.workout_plan.days)
    if input_data.adjustment_type == "reduce_intensity":
        for day in days:
            for exercise in day.exercises:
                exercise.sets = max(1, exercise.sets - 1)
                exercise.notes = input_data.reason
    now = timestamp()
    adjusted = current.model_copy(update={
        "plan_id": _plan_id("adjusted"),
        "status": "active",
        "workout_plan": WorkoutPlan(days=days),
        "generated_by": "agent",
        "created_at": now,
        "updated_at": now,
    })
    store = _active_repository_store()
    writer = store.save_plan if store else save_plan
    writer(current.model_copy(update={"status": "archived", "updated_at": now}))
    return writer(adjusted)
