# 945 API 接口契约

版本：v0.1  
日期：2026-07-11  
状态：MVP 接口草案  

## 0. 当前实现状态

截至当前后端 MVP demo，FastAPI 已实现这些接口：

- `GET /health`
- `GET /api/demo-user`
- `GET /api/today`
- `GET /api/plans/current`
- `GET /api/profile/{user_id}`
- `POST /api/profile`
- `PATCH /api/profile/{user_id}`
- `GET /api/settings`
- `PATCH /api/settings`
- `GET /api/workout-logs`
- `POST /api/workout-logs`
- `GET /api/meal-logs`
- `POST /api/meal-logs`
- `POST /api/meal-logs/confirm-planned-meal`
- `GET /api/body-metrics`
- `POST /api/body-metrics`
- `POST /api/daily-checkins`
- `GET /api/advice`
- `PATCH /api/advice/{advice_id}/status`
- `POST /api/agent/chat`
- `GET /api/agent/messages`

当前默认实现使用进程内 demo store 和 deterministic LLM Provider；前端默认使用 mock adapter，也可通过 `VITE_945_API_MODE=http` 调用这些 FastAPI 接口。`npm run qa:http` 固定使用 demo store 和 deterministic Provider，不需要 MongoDB 或 API Key。已具备 MongoDB repository 边界、本地 RAG、异步 Agent 编排、Provider Router 和可选 OpenAI Responses Provider。后续生产化阶段会继续实现计划生成、计划接受、更多历史查询、向量库、鉴权和云部署。

## 1. 目标

本文档定义 945 MVP 的前后端接口边界。当前前端可以先使用 mock adapter 实现同样的接口形状，后端接入后不应大改页面数据结构。

## 2. 通用约定

基础路径：

```text
/api
```

响应格式：

```json
{
  "data": {},
  "error": null
}
```

错误格式：

```json
{
  "data": null,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "请检查必填项。",
    "details": {}
  }
}
```

Agent/LLM 相关稳定错误码：

| code | HTTP | 含义 |
| --- | --- | --- |
| `LLM_CONFIG_ERROR` | `503` | 生产 OpenAI 模式缺少 API Key、模型 ID 或其他必要配置 |
| `LLM_TIMEOUT` | `503` | 模型 Provider 超时 |
| `LLM_RATE_LIMITED` | `503` | 模型 Provider 限流 |
| `LLM_PROVIDER_ERROR` | `503` | 模型 Provider 连接失败、5xx 或其他 SDK 错误 |
| `LLM_OUTPUT_INVALID` | `502` | 模型返回了未知工具、非法参数、第二轮工具调用等不可信输出 |

开发环境可降级到 deterministic Provider；生产环境不会自动降级保存消息，失败轮次不会产生半截对话历史。

MVP 使用本地 demo 用户：

```text
demo-user-945
```

## 3. 枚举

### 3.1 Goal

```ts
type Goal =
  | "fat_loss"
  | "muscle_gain"
  | "body_recomposition"
  | "strength"
  | "conditioning"
  | "maintenance";
```

### 3.2 ExperienceLevel

```ts
type ExperienceLevel = "beginner" | "novice" | "intermediate" | "advanced";
```

### 3.3 CompletionStatus

```ts
type CompletionStatus = "planned" | "completed" | "partially_completed" | "skipped";
```

### 3.4 AdviceType

```ts
type AdviceType = "daily_advice" | "weekly_summary" | "plan_adjustment" | "safety_warning";
```

## 4. 用户与资料

### GET `/api/demo-user`

返回当前本地 demo 用户。

响应：

```json
{
  "data": {
    "user_id": "demo-user-945",
    "display_name": "Demo User",
    "locale": "zh-CN",
    "unit_system": "metric"
  },
  "error": null
}
```

### POST `/api/profile`

创建或覆盖 demo 用户资料。

请求：

```json
{
  "user_id": "demo-user-945",
  "display_name": "Alex",
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
  "locale": "zh-CN",
  "unit_system": "metric"
}
```

响应：

```json
{
  "data": {
    "profile_id": "profile-demo-user-945",
    "user_id": "demo-user-945",
    "goal": "body_recomposition",
    "updated_at": "2026-07-11T00:00:00.000Z"
  },
  "error": null
}
```

### GET `/api/profile/{user_id}`

返回用户资料。

### PATCH `/api/profile/{user_id}`

局部更新用户资料。请求体字段与 `POST /api/profile` 相同，全部可选。

## 5. 计划

### POST `/api/plans/generate`

生成训练计划和饮食计划。

请求：

```json
{
  "user_id": "demo-user-945",
  "goal": "body_recomposition",
  "days": 7,
  "generate_workout_plan": true,
  "generate_meal_plan": true
}
```

响应：

```json
{
  "data": {
    "plan_id": "plan-2026-07-11-demo",
    "user_id": "demo-user-945",
    "status": "draft",
    "start_date": "2026-07-11",
    "end_date": "2026-07-17",
    "workout_plan": {
      "days": [
        {
          "date": "2026-07-11",
          "name": "Upper Strength",
          "duration_minutes": 55,
          "exercises": [
            {
              "exercise_id": "ex-db-press",
              "name": "Dumbbell Bench Press",
              "sets": 4,
              "reps": "8-10",
              "target_weight": "moderate",
              "rest_seconds": 90
            }
          ]
        }
      ]
    },
    "meal_plan": {
      "daily_targets": {
        "calories": 2300,
        "protein_g": 160,
        "carbs_g": 240,
        "fat_g": 70
      },
      "days": [
        {
          "date": "2026-07-11",
          "meals": [
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
                }
              ]
            }
          ]
        }
      ]
    },
    "created_at": "2026-07-11T00:00:00.000Z"
  },
  "error": null
}
```

### GET `/api/plans/current?user_id=demo-user-945`

返回当前执行中的计划。

### GET `/api/plans/{plan_id}`

返回指定计划。

### POST `/api/plans/{plan_id}/accept`

将计划状态改为 `active`。

### POST `/api/plans/{plan_id}/adjust`

用户确认后调整计划。

请求：

```json
{
  "user_id": "demo-user-945",
  "advice_id": "advice-2026-07-11-1",
  "adjustment_type": "reduce_volume",
  "confirmed": true
}
```

## 6. 今日聚合

### GET `/api/today?user_id=demo-user-945&date=2026-07-11`

返回今日页面所需聚合数据。

响应：

```json
{
  "data": {
    "date": "2026-07-11",
    "user": {
      "user_id": "demo-user-945",
      "display_name": "Alex",
      "goal": "body_recomposition"
    },
    "status_summary": {
      "weekly_workouts_completed": 3,
      "weekly_workouts_planned": 4,
      "calories_target": 2300,
      "calories_logged": 1480,
      "protein_target_g": 160,
      "protein_logged_g": 102,
      "weight_7_day_delta_kg": -0.4,
      "recovery_status": "normal"
    },
    "today_workout": {},
    "today_meals": [],
    "daily_checkin": null,
    "latest_advice": null
  },
  "error": null
}
```

## 7. 训练记录

### POST `/api/workout-logs`

请求：

```json
{
  "user_id": "demo-user-945",
  "plan_id": "plan-2026-07-11-demo",
  "date": "2026-07-11",
  "status": "completed",
  "duration_minutes": 58,
  "rpe": 8,
  "exercises": [
    {
      "exercise_id": "ex-db-press",
      "name": "Dumbbell Bench Press",
      "sets": [
        { "reps": 10, "weight_kg": 28 },
        { "reps": 9, "weight_kg": 28 }
      ]
    }
  ],
  "notes": "最后两组比较吃力。"
}
```

### GET `/api/workout-logs?user_id=demo-user-945`

返回训练记录列表。

### PATCH `/api/workout-logs/{log_id}`

局部更新训练记录。

## 8. 饮食记录

### POST `/api/meal-logs/confirm-planned-meal`

确认计划餐完成。

请求：

```json
{
  "user_id": "demo-user-945",
  "plan_id": "plan-2026-07-11-demo",
  "date": "2026-07-11",
  "meal_id": "meal-breakfast-1"
}
```

### POST `/api/meal-logs`

手动记录饮食。

请求：

```json
{
  "user_id": "demo-user-945",
  "date": "2026-07-11",
  "meal_name": "Lunch",
  "source": "manual_entry",
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
  "notes": "外食估算。"
}
```

## 9. 身体数据与打卡

### POST `/api/body-metrics`

请求：

```json
{
  "user_id": "demo-user-945",
  "date": "2026-07-11",
  "weight_kg": 75.6,
  "body_fat_percentage": 18.5,
  "waist_cm": 83,
  "notes": ""
}
```

### POST `/api/daily-checkins`

请求：

```json
{
  "user_id": "demo-user-945",
  "date": "2026-07-11",
  "sleep_hours": 7.5,
  "sleep_quality": 4,
  "fatigue_level": 3,
  "soreness_level": 2,
  "stress_level": 3,
  "mood": "normal",
  "notes": "今天状态还可以。"
}
```

## 10. 建议与 Agent

### POST `/api/advice/daily`

根据近期记录生成每日建议。

请求：

```json
{
  "user_id": "demo-user-945",
  "date": "2026-07-11"
}
```

响应：

```json
{
  "data": {
    "advice_id": "advice-2026-07-11-1",
    "type": "daily_advice",
    "title": "今天保持计划，但降低最后一组强度",
    "content": "你最近训练完成率稳定，但疲劳评分略高。今天可以按计划训练，最后一个复合动作保留 2 次余力。",
    "reason": "最近 3 天睡眠良好，但昨天 RPE 为 9。",
    "related_data": ["workout_logs", "daily_checkins"],
    "recommended_actions": ["按计划训练", "最后一组不要力竭"],
    "risk_level": "low",
    "accepted_status": "pending"
  },
  "error": null
}
```

### POST `/api/agent/chat`

Agent 对话。

请求：

```json
{
  "user_id": "demo-user-945",
  "locale": "zh-CN",
  "message": "今天深蹲做了 4 组，每组 8 次，80kg，感觉很累。",
  "context": {
    "current_page": "today",
    "date": "2026-07-11"
  }
}
```

响应：

```json
{
  "data": {
    "message_id": "msg-1",
    "reply": "我可以帮你记录这次训练。保存前请确认下面的草稿。",
    "record_draft": {
      "type": "workout_log",
      "requires_confirmation": true,
      "payload": {
        "exercise_name": "深蹲",
        "sets": 4,
        "reps": 8,
        "weight_kg": 80,
        "effort_note": "感觉很累"
      }
    }
  },
  "error": null
}
```

当前响应体中的 Agent 消息仍使用 `AgentMessage` 形状，关键字段如下：

```json
{
  "data": {
    "message_id": "msg-agent-...",
    "user_id": "demo-user-945",
    "role": "agent",
    "content": "我可以帮你整理成记录草稿。保存前请先确认。",
    "locale": "zh-CN",
    "record_draft": {
      "type": "workout_log",
      "requires_confirmation": true,
      "payload": {
        "exercise_name": "深蹲",
        "sets": 4,
        "reps": 8,
        "weight_kg": 80,
        "effort_note": "今天深蹲做了 4 组，每组 8 次，80kg，感觉很累。"
      }
    },
    "created_at": "2026-07-11T00:00:00.000Z"
  },
  "error": null
}
```

重要边界：

- `record_draft` 只是预览草稿，不会自动保存。
- 训练草稿必须由用户确认后调用 `POST /api/workout-logs`。
- 饮食草稿必须由用户确认后调用 `POST /api/meal-logs`；计划餐确认使用 `POST /api/meal-logs/confirm-planned-meal`。
- 计划调整草稿不会改写计划；当前 MVP 尚未实现计划调整结构化 API。
- 高风险输入优先返回安全提醒，不调用 OpenAI Provider。
