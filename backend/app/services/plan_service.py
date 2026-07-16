from backend.app.data.demo_data import DEMO_PLAN, DEMO_USER_ID
from backend.app.models.domain import Plan


def get_current_plan(user_id: str = DEMO_USER_ID) -> Plan | None:
    if user_id != DEMO_USER_ID:
        return None
    return DEMO_PLAN
