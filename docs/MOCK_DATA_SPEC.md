# 945 Mock Data Spec

版本：v0.1  
日期：2026-07-11  
状态：前端和后端联调前使用  

## 1. 目标

Mock 数据用于让前端在后端接入前完成页面、交互、i18n 和验收流程。Mock 数据必须遵守 `docs/API_CONTRACT.md` 和 `docs/DATA_MODEL.md` 的字段形状。

## 2. 文件建议

前端业务化实现时建议创建：

```text
src/data/demoData.ts
src/data/i18n/zh-CN.ts
src/data/i18n/en-US.ts
src/services/api.ts
src/services/mockApi.ts
```

当前 Stitch HTML 包装型原型可以先不改这些文件；这些文件用于下一阶段业务化实现。

## 3. Demo 用户

```json
{
  "user_id": "demo-user-945",
  "display_name": "Alex",
  "locale": "zh-CN",
  "unit_system": "metric"
}
```

## 4. Demo Profile

```json
{
  "profile_id": "profile-demo-user-945",
  "user_id": "demo-user-945",
  "age": 29,
  "gender": "optional",
  "height_cm": 175,
  "weight_kg": 76,
  "goal": "body_recomposition",
  "experience_level": "novice",
  "training_days_per_week": 4,
  "training_duration_minutes": 60,
  "equipment": ["dumbbells", "gym"],
  "dietary_preferences": ["high_protein"],
  "allergies": [],
  "constraints": ["busy_weekdays"],
  "updated_at": "2026-07-11T00:00:00.000Z"
}
```

## 5. Today Summary

```json
{
  "date": "2026-07-11",
  "status_summary": {
    "weekly_workouts_completed": 3,
    "weekly_workouts_planned": 4,
    "calories_target": 2300,
    "calories_logged": 1480,
    "protein_target_g": 160,
    "protein_logged_g": 102,
    "weight_7_day_delta_kg": -0.4,
    "recovery_status": "normal"
  }
}
```

## 6. Today Workout

```json
{
  "date": "2026-07-11",
  "name": "Upper Strength",
  "focus": "chest_back_shoulders",
  "duration_minutes": 55,
  "exercises": [
    {
      "exercise_id": "ex-db-press",
      "name": "Dumbbell Bench Press",
      "target_muscles": ["chest", "triceps"],
      "sets": 4,
      "reps": "8-10",
      "target_weight": "moderate",
      "rest_seconds": 90
    },
    {
      "exercise_id": "ex-row",
      "name": "Seated Cable Row",
      "target_muscles": ["back"],
      "sets": 4,
      "reps": "10-12",
      "target_weight": "moderate",
      "rest_seconds": 90
    }
  ]
}
```

## 7. Today Meals

```json
[
  {
    "meal_id": "meal-breakfast-1",
    "name": "Breakfast",
    "foods": [
      {
        "name": "Greek yogurt",
        "portion": "250g",
        "calories": 180,
        "protein_g": 24,
        "carbs_g": 12,
        "fat_g": 4
      },
      {
        "name": "Blueberries",
        "portion": "100g",
        "calories": 57,
        "protein_g": 1,
        "carbs_g": 14,
        "fat_g": 0
      }
    ],
    "total_macros": {
      "calories": 237,
      "protein_g": 25,
      "carbs_g": 26,
      "fat_g": 4
    }
  },
  {
    "meal_id": "meal-lunch-1",
    "name": "Lunch",
    "foods": [
      {
        "name": "Chicken rice bowl",
        "portion": "1 bowl",
        "calories": 620,
        "protein_g": 42,
        "carbs_g": 78,
        "fat_g": 16
      }
    ],
    "total_macros": {
      "calories": 620,
      "protein_g": 42,
      "carbs_g": 78,
      "fat_g": 16
    }
  }
]
```

## 8. Advice

```json
{
  "advice_id": "advice-2026-07-11-1",
  "user_id": "demo-user-945",
  "date": "2026-07-11",
  "type": "daily_advice",
  "title": "今天保持计划，但降低最后一组强度",
  "content": "你最近训练完成率稳定，但疲劳评分略高。今天可以按计划训练，最后一个复合动作保留 2 次余力。",
  "reason": "最近 3 天睡眠良好，但昨天 RPE 为 9。",
  "related_data": ["workout_logs", "daily_checkins"],
  "recommended_actions": ["按计划训练", "最后一组不要力竭"],
  "risk_level": "low",
  "accepted_status": "pending"
}
```

## 9. Mock Interaction Requirements

Mock API 必须支持这些状态变化：

- 确认计划餐后，今日热量和蛋白质进度增加。
- 保存训练记录后，训练状态变为 `completed` 或 `partially_completed`。
- 保存每日打卡后，今日 Dashboard 显示已打卡。
- Agent Chat 发送训练或饮食自然语言后，返回 `record_draft`。
- 用户确认 `record_draft` 后，写入对应 mock store。
- 切换语言后，导航、按钮、表单标签和空状态文案变化。

