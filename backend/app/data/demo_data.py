from datetime import date, timedelta

from backend.app.core.dates import app_date
from backend.app.models.domain import AgentAdvice, Plan, PlannedMeal, TodayResponseData, User, WorkoutPlanDay


DEMO_USER_ID = "demo-user-945"
TODAY_DATE = app_date()
NOW = f"{TODAY_DATE}T00:00:00.000Z"

DEMO_USER = User(
    user_id=DEMO_USER_ID,
    display_name="Alex",
    locale="zh-CN",
    unit_system="metric",
    created_at=NOW,
    updated_at=NOW
)

DEMO_GOAL = "body_recomposition"

TODAY_WORKOUT = WorkoutPlanDay(
    date=TODAY_DATE,
    name="上肢力量",
    focus="chest_back_shoulders",
    duration_minutes=55,
    exercises=[
        {
            "exercise_id": "ex-db-press",
            "name": "哑铃卧推",
            "target_muscles": ["胸部", "肱三头肌"],
            "sets": 4,
            "reps": "8-10",
            "target_weight": "moderate",
            "rest_seconds": 90
        },
        {
            "exercise_id": "ex-row",
            "name": "坐姿绳索划船",
            "target_muscles": ["背部"],
            "sets": 4,
            "reps": "10-12",
            "target_weight": "moderate",
            "rest_seconds": 90
        },
        {
            "exercise_id": "ex-db-shoulder-press",
            "name": "哑铃推肩",
            "target_muscles": ["肩部", "肱三头肌"],
            "sets": 3,
            "reps": "8-10",
            "target_weight": "moderate",
            "rest_seconds": 90
        }
    ]
)

LOWER_BODY_WORKOUT = WorkoutPlanDay(
    date=(date.fromisoformat(TODAY_DATE) + timedelta(days=2)).isoformat(),
    name="下肢力量",
    focus="legs_glutes",
    duration_minutes=60,
    exercises=[
        {
            "exercise_id": "ex-squat",
            "name": "杠铃深蹲",
            "target_muscles": ["股四头肌", "臀部"],
            "sets": 4,
            "reps": "6-8",
            "target_weight": "moderate_heavy",
            "rest_seconds": 120
        }
    ]
)

TODAY_MEALS = [
    PlannedMeal(
        meal_id="meal-breakfast-1",
        name="早餐",
        foods=[
            {"name": "希腊酸奶", "portion": "250g", "calories": 180, "protein_g": 24, "carbs_g": 12, "fat_g": 4},
            {"name": "蓝莓", "portion": "100g", "calories": 57, "protein_g": 1, "carbs_g": 14, "fat_g": 0},
            {"name": "燕麦片", "portion": "40g", "calories": 150, "protein_g": 5, "carbs_g": 27, "fat_g": 3}
        ],
        total_macros={"calories": 387, "protein_g": 30, "carbs_g": 53, "fat_g": 7}
    ),
    PlannedMeal(
        meal_id="meal-lunch-1",
        name="午餐",
        foods=[
            {"name": "鸡胸肉饭碗", "portion": "1 bowl", "calories": 620, "protein_g": 42, "carbs_g": 78, "fat_g": 16}
        ],
        total_macros={"calories": 620, "protein_g": 42, "carbs_g": 78, "fat_g": 16}
    ),
    PlannedMeal(
        meal_id="meal-dinner-1",
        name="晚餐",
        foods=[
            {"name": "三文鱼", "portion": "160g", "calories": 330, "protein_g": 36, "carbs_g": 0, "fat_g": 20},
            {"name": "红薯", "portion": "220g", "calories": 190, "protein_g": 4, "carbs_g": 44, "fat_g": 0},
            {"name": "混合蔬菜", "portion": "200g", "calories": 90, "protein_g": 5, "carbs_g": 16, "fat_g": 1}
        ],
        total_macros={"calories": 610, "protein_g": 45, "carbs_g": 60, "fat_g": 21}
    )
]

DEMO_PLAN = Plan(
    plan_id=f"plan-{TODAY_DATE}-demo",
    user_id=DEMO_USER_ID,
    goal=DEMO_GOAL,
    status="active",
    start_date=TODAY_DATE,
    end_date=(date.fromisoformat(TODAY_DATE) + timedelta(days=6)).isoformat(),
    generated_by="mock",
    created_at=NOW,
    updated_at=NOW,
    workout_plan={
        "days": [
            TODAY_WORKOUT,
            LOWER_BODY_WORKOUT
        ]
    },
    meal_plan={
        "daily_targets": {
            "calories": 2300,
            "protein_g": 160,
            "carbs_g": 240,
            "fat_g": 70
        },
        "days": [
            {
                "date": TODAY_DATE,
                "meals": TODAY_MEALS
            }
        ]
    }
)

DEMO_ADVICE = AgentAdvice(
    advice_id=f"advice-{TODAY_DATE}-1",
    user_id=DEMO_USER_ID,
    date=TODAY_DATE,
    type="daily_advice",
    title="今天保持计划，但降低最后一组强度",
    content="你最近训练完成率稳定，但疲劳评分略高。今天可以按计划训练，最后一个复合动作保留 2 次余力。",
    reason="最近 3 天睡眠良好，但昨天主观强度为 9。",
    related_data=["workout_logs", "daily_checkins"],
    recommended_actions=["按计划训练", "最后一组不要力竭"],
    risk_level="low",
    accepted_status="pending",
    created_at=NOW
)


def create_today_response(date: str = TODAY_DATE) -> TodayResponseData:
    return TodayResponseData(
        date=date,
        user={
            "user_id": DEMO_USER.user_id,
            "display_name": DEMO_USER.display_name,
            "goal": DEMO_GOAL
        },
        status_summary={
            "weekly_workouts_completed": 3,
            "weekly_workouts_planned": 4,
            "calories_target": DEMO_PLAN.meal_plan.daily_targets.calories,
            "calories_logged": 1480,
            "protein_target_g": DEMO_PLAN.meal_plan.daily_targets.protein_g,
            "protein_logged_g": 102,
            "weight_7_day_delta_kg": -0.4,
            "recovery_status": "normal"
        },
        today_workout=TODAY_WORKOUT if date == TODAY_DATE else None,
        today_meals=TODAY_MEALS if date == TODAY_DATE else [],
        daily_checkin=None,
        latest_advice=DEMO_ADVICE if date == TODAY_DATE else None
    )
