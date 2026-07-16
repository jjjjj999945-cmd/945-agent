from backend.app.data.demo_data import DEMO_USER_ID, TODAY_DATE
from backend.app.models.domain import TodayResponseData, User
from backend.app.services.demo_store import build_today_response, get_current_user


def get_demo_user() -> User:
    return get_current_user()


def get_today(user_id: str = DEMO_USER_ID, date: str = TODAY_DATE) -> TodayResponseData | None:
    return build_today_response(user_id=user_id, date=date)
