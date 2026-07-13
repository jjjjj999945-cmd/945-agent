# 945 MVP 基础层实现计划

> **给 agentic worker：** 必须使用子技能：推荐 `superpowers:subagent-driven-development`，或使用 `superpowers:executing-plans`，按任务逐步执行本计划。步骤使用 checkbox（`- [ ]`）语法跟踪。

**目标：** 将当前 Stitch HTML 原型转换为可维护的 945 MVP 基础层，包括带类型的领域数据、mock API、i18n，以及第一个由业务数据驱动的今日页面。

**架构：** 保留现有 Stitch 包装层作为参考，同时增加一条并行的业务实现路径。先引入带类型的领域模型、本地 mock store、API 形状的 service function 和 i18n 字典，再逐页替换 screen。

**技术栈：** Vite、React 19、TypeScript 5.8、CSS、本地 mock 数据，以及未来对齐 `docs/API_CONTRACT.md` 的 FastAPI 契约。

## 全局约束

- `PRD.md` 是产品事实来源。
- `docs/FRONTEND_REQUIREMENTS.md` 是前端细节来源；若与 `PRD.md` 冲突，以 `PRD.md` 为准。
- 当前 Stitch reference screens 是视觉参考，不是长期 app 实现。
- 产品名称为 `945`。
- MVP 使用本地 demo 用户 `demo-user-945`；不做登录或注册。
- 前端必须保留 `zh-CN` 和 `en-US` i18n 结构。
- Agent Chat 最终位置仍未确定；先实现为可移动模块。
- 饮食 MVP 只支持计划餐确认和手动录入。
- 不实现食物图片识别、穿戴设备、支付、社区、排行榜、医疗诊断或康复处方。
- Agent 变更不能静默写入；记录草稿和计划调整必须要求确认。

---

## 文件结构

实现期间创建这些文件：

```text
src/types/domain.ts
src/data/demoData.ts
src/i18n/types.ts
src/i18n/zh-CN.ts
src/i18n/en-US.ts
src/i18n/index.ts
src/services/apiTypes.ts
src/services/mockApi.ts
src/components/business/AppShell.tsx
src/components/business/MetricCard.tsx
src/components/business/ProgressBar.tsx
src/components/business/ConfirmDialog.tsx
src/pages/TodayPage.tsx
src/pages/PrototypeRouter.tsx
```

修改这些文件：

```text
src/App.tsx
src/styles.css
```

测试命令：

```text
npm run build
```

当前仓库说明：

`D:\Codex\945` 当前包含 `.git` 目录，但 `git status` 报告 `not a git repository`。在仓库元数据修复或重新初始化前，不要依赖提交步骤。

---

### 任务 1：领域类型

**文件：**
- 创建：`src/types/domain.ts`

**接口：**
- 产出：`User`、`UserProfile`、`Plan`、`TodayResponseData`、`WorkoutLog`、`MealLog`、`DailyCheckin`、`BodyMetric`、`AgentAdvice`、`AgentMessage`、`RecordDraft`

- [ ] **步骤 1：创建领域类型文件**

创建 `src/types/domain.ts`：

```ts
export type Locale = "zh-CN" | "en-US";
export type UnitSystem = "metric" | "imperial";
export type Goal = "fat_loss" | "muscle_gain" | "body_recomposition" | "strength" | "conditioning" | "maintenance";
export type ExperienceLevel = "beginner" | "novice" | "intermediate" | "advanced";
export type CompletionStatus = "planned" | "completed" | "partially_completed" | "skipped";
export type AdviceType = "daily_advice" | "weekly_summary" | "plan_adjustment" | "safety_warning";

export type User = {
  user_id: string;
  display_name: string;
  locale: Locale;
  unit_system: UnitSystem;
  created_at: string;
  updated_at: string;
};

export type UserProfile = {
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

export type MacroTargets = {
  calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
};

export type PlannedExercise = {
  exercise_id: string;
  name: string;
  target_muscles: string[];
  sets: number;
  reps: string;
  target_weight?: string;
  rest_seconds: number;
  notes?: string;
};

export type WorkoutPlanDay = {
  date: string;
  name: string;
  focus: string;
  duration_minutes: number;
  exercises: PlannedExercise[];
};

export type WorkoutPlan = {
  days: WorkoutPlanDay[];
};

export type PlannedFood = {
  name: string;
  portion: string;
  calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
};

export type PlannedMeal = {
  meal_id: string;
  name: string;
  foods: PlannedFood[];
  total_macros: MacroTargets;
};

export type MealPlanDay = {
  date: string;
  meals: PlannedMeal[];
};

export type MealPlan = {
  daily_targets: MacroTargets;
  days: MealPlanDay[];
};

export type Plan = {
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

export type StatusSummary = {
  weekly_workouts_completed: number;
  weekly_workouts_planned: number;
  calories_target: number;
  calories_logged: number;
  protein_target_g: number;
  protein_logged_g: number;
  weight_7_day_delta_kg: number;
  recovery_status: "good" | "normal" | "fatigued";
};

export type DailyCheckin = {
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

export type ExerciseSetLog = {
  reps: number;
  weight_kg?: number;
  completed?: boolean;
};

export type ExerciseLog = {
  exercise_id?: string;
  name: string;
  sets: ExerciseSetLog[];
};

export type WorkoutLog = {
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

export type FoodLog = PlannedFood;

export type MealLog = {
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

export type BodyMetric = {
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

export type AgentAdvice = {
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

export type RecordDraft = {
  type: "workout_log" | "meal_log" | "daily_checkin" | "plan_adjustment";
  requires_confirmation: true;
  payload: Record<string, unknown>;
};

export type AgentMessage = {
  message_id: string;
  user_id: string;
  role: "user" | "agent";
  content: string;
  locale: Locale;
  record_draft?: RecordDraft;
  created_at: string;
};

export type TodayResponseData = {
  date: string;
  user: Pick<User, "user_id" | "display_name"> & { goal: Goal };
  status_summary: StatusSummary;
  today_workout: WorkoutPlanDay | null;
  today_meals: PlannedMeal[];
  daily_checkin: DailyCheckin | null;
  latest_advice: AgentAdvice | null;
};
```

- [ ] **步骤 2：运行类型构建**

运行：`npm run build`  
预期：通过。

---

### 任务 2：Demo 数据

**文件：**
- 创建：`src/data/demoData.ts`

**接口：**
- 消费：来自 `src/types/domain.ts` 的领域类型
- 产出：`demoUser`、`demoProfile`、`demoPlan`、`demoAdvice`、`createInitialTodayData`

- [ ] **步骤 1：创建 demo 数据**

使用 `docs/MOCK_DATA_SPEC.md` 中的值创建 `src/data/demoData.ts`。

- [ ] **步骤 2：运行构建**

运行：`npm run build`  
预期：通过。

---

### 任务 3：i18n 基础层

**文件：**
- 创建：`src/i18n/types.ts`
- 创建：`src/i18n/zh-CN.ts`
- 创建：`src/i18n/en-US.ts`
- 创建：`src/i18n/index.ts`

**接口：**
- 产出：`useI18n(locale)`、`messages`、`MessageKey`

- [ ] **步骤 1：创建文案 schema**

为导航、今日页面标签、动作、空状态和安全提示创建扁平 key schema。

- [ ] **步骤 2：添加中文文案**

包含这些 key：`nav.today`、`nav.workout`、`nav.diet`、`nav.body`、`nav.advice`、`nav.agent`、`nav.settings`、`today.title`、`today.workout`、`today.diet`、`today.checkin`、`actions.save`、`actions.confirm`、`actions.cancel`。

- [ ] **步骤 3：添加英文文案**

使用相同 key，并填入英文值。

- [ ] **步骤 4：运行构建**

运行：`npm run build`  
预期：通过。

---

### 任务 4：Mock API

**文件：**
- 创建：`src/services/apiTypes.ts`
- 创建：`src/services/mockApi.ts`

**接口：**
- 消费：领域类型和 demo 数据
- 产出：`api.getDemoUser()`、`api.getToday()`、`api.saveDailyCheckin()`、`api.confirmPlannedMeal()`、`api.saveWorkoutLog()`、`api.sendAgentMessage()`

- [ ] **步骤 1：创建 API 响应类型**

定义：

```ts
export type ApiError = { code: string; message: string; details?: Record<string, unknown> };
export type ApiResponse<T> = { data: T; error: null } | { data: null; error: ApiError };
```

- [ ] **步骤 2：实现内存 mock API**

使用从 `demoData.ts` 初始化的模块级变量。

- [ ] **步骤 3：实现 mock 状态变化**

必需行为：

- `confirmPlannedMeal(meal_id)` 添加 meal log，并增加营养摄入总量。
- `saveDailyCheckin(input)` 保存今日打卡。
- `saveWorkoutLog(input)` 保存训练记录并标记完成。
- `sendAgentMessage(message)` 对明显的训练或饮食消息返回 `record_draft`。

- [ ] **步骤 4：运行构建**

运行：`npm run build`  
预期：通过。

---

### 任务 5：业务 App Shell

**文件：**
- 创建：`src/components/business/AppShell.tsx`
- 修改：`src/App.tsx`

**接口：**
- 消费：`useI18n`、导航文案 key
- 产出：路由模式，可展示当前 Stitch 原型或新的业务今日页面

- [ ] **步骤 1：保留原型路由**

将当前 Stitch 加载逻辑从 `src/App.tsx` 移到 `src/pages/PrototypeRouter.tsx`，不改变行为。

- [ ] **步骤 2：添加 AppShell**

创建包含导航项和语言选择器的 shell。

- [ ] **步骤 3：添加模式切换**

让 `/app` 渲染业务今日页面，让 `/prototype` 或现有路由渲染 Stitch 原型。

- [ ] **步骤 4：运行构建**

运行：`npm run build`  
预期：通过。

---

### 任务 6：业务今日页面

**文件：**
- 创建：`src/pages/TodayPage.tsx`
- 创建：`src/components/business/MetricCard.tsx`
- 创建：`src/components/business/ProgressBar.tsx`
- 修改：`src/styles.css`

**接口：**
- 消费：`api.getToday()`、`api.saveDailyCheckin()`、`api.confirmPlannedMeal()`
- 产出：第一个使用 mock 数据的业务页面

- [ ] **步骤 1：加载今日数据**

使用 `useEffect` 调用 `api.getToday({ user_id: "demo-user-945" })`。

- [ ] **步骤 2：渲染摘要**

展示目标、训练完成情况、热量、蛋白质、体重变化和恢复状态。

- [ ] **步骤 3：渲染训练卡片**

展示今日训练和动作列表。

- [ ] **步骤 4：渲染餐食卡片**

展示今日餐食和计划餐确认按钮。

- [ ] **步骤 5：渲染打卡表单**

支持体重、睡眠、疲劳、酸痛和备注。

- [ ] **步骤 6：运行构建**

运行：`npm run build`  
预期：通过。

---

### 任务 7：确认弹窗和 Agent 草稿

**文件：**
- 创建：`src/components/business/ConfirmDialog.tsx`
- 修改：`src/pages/TodayPage.tsx`

**接口：**
- 消费：`api.sendAgentMessage()`
- 产出：记录草稿的确认流程

- [ ] **步骤 1：添加通用确认弹窗**

Props：`open`、`title`、`children`、`confirmLabel`、`cancelLabel`、`onConfirm`、`onCancel`。

- [ ] **步骤 2：在今日页面添加小型 Agent 输入框**

通过 mock API 发送消息。

- [ ] **步骤 3：展示草稿确认**

如果响应包含 `record_draft.requires_confirmation`，在写入数据前显示确认弹窗。

- [ ] **步骤 4：运行构建**

运行：`npm run build`  
预期：通过。

---

### 任务 8：验证

**文件：**
- 修改：`design-qa.md`

**接口：**
- 消费：前面所有任务
- 产出：验证记录

- [ ] **步骤 1：运行构建**

运行：`npm run build`  
预期：通过。

- [ ] **步骤 2：启动开发服务器**

运行：`npm run dev`  
预期：Vite 可以提供 app 服务。

- [ ] **步骤 3：浏览器检查**

打开 `/app` 并验证：

- 今日数据可以渲染。
- 餐食确认会改变营养总量。
- 每日打卡会保存可见状态。
- Agent 草稿会要求确认。
- 语言切换会改变标签。

- [ ] **步骤 4：更新 QA 记录**

将已检查路由和结果追加到 `design-qa.md`。
