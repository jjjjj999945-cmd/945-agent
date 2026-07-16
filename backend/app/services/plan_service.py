from backend.app.data.demo_data import DEMO_PLAN, DEMO_USER_ID
from backend.app.models.domain import Plan
from backend.app.services.demo_store import _active_repository_store


def get_current_plan(user_id: str = DEMO_USER_ID) -> Plan | None:
    store = _active_repository_store()
    if store:
        return store.get_current_plan(user_id)
    if user_id != DEMO_USER_ID:
        return None
    return DEMO_PLAN
