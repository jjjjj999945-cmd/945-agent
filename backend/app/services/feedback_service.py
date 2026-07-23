from backend.app.models.domain import AgentAdvice, FeedbackGenerateInput
from backend.app.services.demo_seed import timestamp
from backend.app.services.demo_store import (
    get_daily_checkin,
    list_meal_logs,
    list_workout_logs,
    save_advice,
)
from backend.app.services.plan_service import get_current_plan


def generate_feedback(input_data: FeedbackGenerateInput) -> list[AgentAdvice] | None:
    plan = get_current_plan(input_data.user_id)
    workouts = list_workout_logs(input_data.user_id)
    meals = list_meal_logs(input_data.user_id)
    if plan is None or workouts is None or meals is None:
        return None

    checkin = get_daily_checkin(input_data.user_id, input_data.date)
    targets = plan.meal_plan.daily_targets
    today_meals = [meal for meal in meals if meal.date == input_data.date]
    protein = sum(meal.protein_g for meal in today_meals)
    completed = len([item for item in workouts if item.status in ("completed", "partially_completed")])
    planned = len(plan.workout_plan.days)
    fatigued = checkin is not None and (
        (checkin.fatigue_level or 0) >= 4
        or (checkin.soreness_level or 0) >= 4
        or (checkin.sleep_hours is not None and checkin.sleep_hours < 7)
    )
    now = timestamp()

    if fatigued:
        daily = AgentAdvice(
            advice_id=f"advice-daily-{input_data.date}", user_id=input_data.user_id, date=input_data.date,
            type="daily_advice", title="恢复优先，今天降低训练强度",
            content="你记录的疲劳、酸痛或睡眠信号偏高。今天优先恢复，避免力竭训练。",
            reason="每日打卡出现高疲劳、高酸痛或睡眠不足。",
            related_data=["daily_checkins"], recommended_actions=["降低训练强度", "保留 2 次余力", "优先补充睡眠"],
            risk_level="medium", accepted_status="pending", created_at=now,
        )
    elif protein < targets.protein_g * 0.7:
        daily = AgentAdvice(
            advice_id=f"advice-daily-{input_data.date}", user_id=input_data.user_id, date=input_data.date,
            type="daily_advice", title="今天的蛋白质记录仍有缺口",
            content=f"当前已记录 {protein}g 蛋白质，目标为 {targets.protein_g}g。可在后续餐次补充高蛋白食物。",
            reason="当天已记录饮食的蛋白质低于目标的 70%。",
            related_data=["meal_logs", "meal_plan"], recommended_actions=["确认计划餐", "补充高蛋白食物"],
            risk_level="low", accepted_status="pending", created_at=now,
        )
    else:
        daily = AgentAdvice(
            advice_id=f"advice-daily-{input_data.date}", user_id=input_data.user_id, date=input_data.date,
            type="daily_advice", title="今天按当前计划继续执行",
            content="当前记录没有发现需要立即调整的恢复或饮食风险信号。",
            reason="训练、饮食与每日打卡未触发调整阈值。",
            related_data=["workout_logs", "meal_logs", "daily_checkins"], recommended_actions=["完成计划训练", "继续记录餐食"],
            risk_level="low", accepted_status="pending", created_at=now,
        )

    weekly = AgentAdvice(
        advice_id=f"advice-weekly-{input_data.date}", user_id=input_data.user_id, date=input_data.date,
        type="weekly_summary", title="本周执行反馈",
        content=f"已记录 {completed} 次完成或部分完成训练，当前计划包含 {planned} 个训练日。",
        reason="基于训练记录与当前 active plan 的训练日数量计算。",
        related_data=["workout_logs", "plans"], recommended_actions=["保持训练记录完整", "每周复盘完成率"],
        risk_level="low", accepted_status="pending", created_at=now,
    )
    results = [daily, weekly]
    if fatigued:
        results.append(AgentAdvice(
            advice_id=f"advice-adjustment-{input_data.date}", user_id=input_data.user_id, date=input_data.date,
            type="plan_adjustment", title="建议将今天训练降低一个强度等级",
            content="该调整会先生成草稿，只有你在 Agent 中确认后才会应用到计划。",
            reason="恢复信号偏低，避免在疲劳状态下继续堆叠训练负荷。",
            related_data=["daily_checkins", "workout_plan"], recommended_actions=["生成降低强度草稿"],
            risk_level="medium", accepted_status="pending", created_at=now,
        ))
    for advice in results:
        save_advice(advice)
    return results
