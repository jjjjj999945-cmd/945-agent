from backend.app.data.demo_data import DEMO_USER, DEMO_USER_ID, TODAY_DATE, create_today_response
from backend.app.models.domain import TodayResponseData, User


def get_demo_user() -> User:
    return DEMO_USER


def get_today(user_id: str = DEMO_USER_ID, date: str = TODAY_DATE) -> TodayResponseData | None:
    if user_id != DEMO_USER_ID:
        return None
    return create_today_response(date)
