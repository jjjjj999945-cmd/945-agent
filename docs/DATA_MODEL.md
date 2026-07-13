# 945 数据模型

版本：v0.1  
日期：2026-07-11  
状态：MVP 数据模型草案  

## 1. 目标

本文档定义 945 MVP 的数据模型。MVP 可以使用前端 mock、本地 JSON、MongoDB 或后端内存存储，但字段命名应尽量保持一致。

## 2. 命名约定

- ID 字段使用 snake_case，例如 `user_id`。
- API JSON 使用 snake_case。
- 前端 TypeScript 可以直接使用 snake_case，避免接口转换层过早复杂化。
- 日期使用 `YYYY-MM-DD`。
- 时间戳使用 ISO 8601。
- 单位字段显式写出单位，例如 `weight_kg`、`height_cm`。

## 3. 数据集合 / 存储

MVP 需要这些数据集合：

- `users`
- `user_profiles`
- `plans`
- `daily_checkins`
- `body_metrics`
- `workout_logs`
- `meal_logs`
- `agent_advice`
- `agent_messages`

## 4. `users`

```ts
type User = {
  user_id: string;
  display_name: string;
  locale: "zh-CN" | "en-US";
  unit_system: "metric" | "imperial";
  created_at: string;
  updated_at: string;
};
```

MVP demo 用户：

```json
{
  "user_id": "demo-user-945",
  "display_name": "Demo User",
  "locale": "zh-CN",
  "unit_system": "metric",
  "created_at": "2026-07-11T00:00:00.000Z",
  "updated_at": "2026-07-11T00:00:00.000Z"
}
```

## 5. `user_profiles`

```ts
type UserProfile = {
  profile_id: string;
  user_id: string;
  age: number;
  gender?: string;
  height_cm: number;
  weight_kg: number;
  goal: Goal;
  experience_level: ExperienceLevel;
  training_days_per_week: number;
  training_duration_minutes: number;
  equipment: string[];
  dietary_preferences: string[];
  allergies: string[];
  constraints: string[];
  updated_at: string;
};
```

## 6. `plans`

```ts
type Plan = {
  plan_id: string;
  user_id: string;
  goal: Goal;
  status: "draft" | "active" | "archived";
  start_date: string;
  end_date: string;
  workout_plan: WorkoutPlan;
  meal_plan: MealPlan;
  generated_by: "agent" | "mock";
  created_at: string;
  updated_at: string;
};
```

```ts
type WorkoutPlan = {
  days: WorkoutPlanDay[];
};

type WorkoutPlanDay = {
  date: string;
  name: string;
  focus: string;
  duration_minutes: number;
  exercises: PlannedExercise[];
};

type PlannedExercise = {
  exercise_id: string;
  name: string;
  target_muscles: string[];
  sets: number;
  reps: string;
  target_weight?: string;
  rest_seconds: number;
  notes?: string;
};
```

```ts
type MealPlan = {
  daily_targets: MacroTargets;
  days: MealPlanDay[];
};

type MacroTargets = {
  calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
};

type MealPlanDay = {
  date: string;
  meals: PlannedMeal[];
};

type PlannedMeal = {
  meal_id: string;
  name: string;
  foods: PlannedFood[];
  total_macros: MacroTargets;
};

type PlannedFood = {
  name: string;
  portion: string;
  calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
};
```

## 7. `daily_checkins`

```ts
type DailyCheckin = {
  checkin_id: string;
  user_id: string;
  date: string;
  weight_kg?: number;
  sleep_hours?: number;
  sleep_quality?: 1 | 2 | 3 | 4 | 5;
  fatigue_level?: 1 | 2 | 3 | 4 | 5;
  soreness_level?: 1 | 2 | 3 | 4 | 5;
  stress_level?: 1 | 2 | 3 | 4 | 5;
  mood?: "low" | "normal" | "good";
  notes?: string;
  created_at: string;
  updated_at: string;
};
```

## 8. `body_metrics`

```ts
type BodyMetric = {
  metric_id: string;
  user_id: string;
  date: string;
  weight_kg: number;
  body_fat_percentage?: number;
  waist_cm?: number;
  chest_cm?: number;
  hip_cm?: number;
  arm_cm?: number;
  bmi?: number;
  notes?: string;
  created_at: string;
};
```

## 9. `workout_logs`

```ts
type WorkoutLog = {
  workout_log_id: string;
  user_id: string;
  plan_id?: string;
  date: string;
  status: CompletionStatus;
  duration_minutes?: number;
  exercises: ExerciseLog[];
  rpe?: number;
  notes?: string;
  created_at: string;
  updated_at: string;
};

type ExerciseLog = {
  exercise_id?: string;
  name: string;
  sets: ExerciseSetLog[];
};

type ExerciseSetLog = {
  reps: number;
  weight_kg?: number;
  completed?: boolean;
};
```

## 10. `meal_logs`

```ts
type MealLog = {
  meal_log_id: string;
  user_id: string;
  plan_id?: string;
  date: string;
  meal_id?: string;
  meal_name: string;
  source: "planned_meal_confirmation" | "manual_entry";
  foods: FoodLog[];
  calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  notes?: string;
  created_at: string;
  updated_at: string;
};

type FoodLog = {
  name: string;
  portion: string;
  calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
};
```

## 11. `agent_advice`

```ts
type AgentAdvice = {
  advice_id: string;
  user_id: string;
  date: string;
  type: AdviceType;
  title: string;
  content: string;
  reason: string;
  related_data: string[];
  recommended_actions: string[];
  risk_level: "low" | "medium" | "high";
  accepted_status: "pending" | "accepted" | "dismissed";
  created_at: string;
};
```

## 12. `agent_messages`

```ts
type AgentMessage = {
  message_id: string;
  user_id: string;
  role: "user" | "agent";
  content: string;
  locale: "zh-CN" | "en-US";
  record_draft?: RecordDraft;
  created_at: string;
};

type RecordDraft = {
  type: "workout_log" | "meal_log" | "daily_checkin" | "plan_adjustment";
  requires_confirmation: true;
  payload: Record<string, unknown>;
};
```
