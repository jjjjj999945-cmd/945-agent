from backend.app.data.demo_data import DEMO_USER, DEMO_USER_ID, TODAY_DATE
from backend.app.models.domain import TodayResponseData, User
from backend.app.services.demo_store import build_today_response


def get_demo_user() -> User:
    return DEMO_USER


def get_today(user_id: str = DEMO_USER_ID, date: str = TODAY_DATE) -> TodayResponseData | None:
    return build_today_response(user_id=user_id, date=date)
