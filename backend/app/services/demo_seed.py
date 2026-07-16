from datetime import UTC, datetime

from backend.app.data.demo_data import DEMO_USER_ID, NOW
from backend.app.models.domain import AgentAdvice, UserProfile


INITIAL_PROFILE = UserProfile(
    profile_id="profile-demo-user-945",
    user_id=DEMO_USER_ID,
    age=29,
    gender="optional",
    height_cm=175,
    weight_kg=76,
    goal="body_recomposition",
    experience_level="novice",
    training_days_per_week=4,
    training_duration_minutes=60,
    equipment=["dumbbells", "gym"],
    dietary_preferences=["high_protein"],
    allergies=[],
    constraints=["busy_weekdays"],
    updated_at=NOW
)

INITIAL_WEEKLY_ADVICE = AgentAdvice(
    advice_id="advice-weekly-001",
    user_id=DEMO_USER_ID,
    date="2026-07-11",
    type="weekly_summary",
    title="本周执行稳定，但恢复信号偏疲劳",
    content="你完成了大部分训练计划，饮食蛋白质基本达标。建议下周保留力量训练频率，但降低一次高强度腿部训练量。",
    reason="训练完成率较好，但疲劳和酸痛评分连续两天偏高。",
    related_data=["weekly_workouts_completed", "fatigue_level", "soreness_level"],
    recommended_actions=["下周腿部训练减少 2 组", "保持每日蛋白质目标", "睡眠低于 7 小时时降低训练强度"],
    risk_level="medium",
    accepted_status="pending",
    created_at="2026-07-11T09:00:00.000Z"
)


def timestamp() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")
