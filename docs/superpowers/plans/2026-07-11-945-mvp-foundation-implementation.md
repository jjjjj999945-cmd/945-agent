# 945 MVP Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the current Stitch HTML prototype into a maintainable 945 MVP foundation with typed domain data, mock API, i18n, and the first business-backed Today page.

**Architecture:** Keep the existing Stitch wrapper as reference while adding a parallel business implementation path. Introduce typed domain models, local mock stores, API-shaped service functions, and i18n dictionaries before replacing screens one at a time.

**Tech Stack:** Vite, React 19, TypeScript 5.8, CSS, local mock data, future FastAPI contract from `docs/API_CONTRACT.md`.

## Global Constraints

- `PRD.md` is the product source of truth.
- `docs/FRONTEND_REQUIREMENTS.md` is the front-end detail source unless it conflicts with `PRD.md`.
- Current Stitch reference screens are visual references, not the long-term app implementation.
- Product name is `945`.
- MVP uses local demo user `demo-user-945`; no login or registration.
- Frontend must preserve `zh-CN` and `en-US` i18n structure.
- Agent Chat final placement remains undecided; implement it as a movable module.
- Diet MVP supports planned meal confirmation and manual entry only.
- No food image recognition, wearables, payments, community, leaderboard, medical diagnosis, or rehab prescription.
- Do not silently write Agent changes; record drafts and plan adjustments require confirmation.

---

## File Structure

Create these files during implementation:

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

Modify these files:

```text
src/App.tsx
src/styles.css
```

Testing commands:

```text
npm run build
```

Current repo note:

`D:\Codex\945` currently contains a `.git` directory but `git status` reports `not a git repository`. Do not rely on commit steps until the repository metadata is repaired or reinitialized.

---

### Task 1: Domain Types

**Files:**
- Create: `src/types/domain.ts`

**Interfaces:**
- Produces: `User`, `UserProfile`, `Plan`, `TodayResponseData`, `WorkoutLog`, `MealLog`, `DailyCheckin`, `BodyMetric`, `AgentAdvice`, `AgentMessage`, `RecordDraft`

- [ ] **Step 1: Create domain type file**

Create `src/types/domain.ts`:

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

- [ ] **Step 2: Run type build**

Run: `npm run build`  
Expected: PASS.

---

### Task 2: Demo Data

**Files:**
- Create: `src/data/demoData.ts`

**Interfaces:**
- Consumes: domain types from `src/types/domain.ts`
- Produces: `demoUser`, `demoProfile`, `demoPlan`, `demoAdvice`, `createInitialTodayData`

- [ ] **Step 1: Create demo data**

Create `src/data/demoData.ts` with values from `docs/MOCK_DATA_SPEC.md`.

- [ ] **Step 2: Run build**

Run: `npm run build`  
Expected: PASS.

---

### Task 3: i18n Foundation

**Files:**
- Create: `src/i18n/types.ts`
- Create: `src/i18n/zh-CN.ts`
- Create: `src/i18n/en-US.ts`
- Create: `src/i18n/index.ts`

**Interfaces:**
- Produces: `useI18n(locale)`, `messages`, `MessageKey`

- [ ] **Step 1: Create message schema**

Create a flat key schema for navigation, Today page labels, actions, empty states, and safety copy.

- [ ] **Step 2: Add Chinese messages**

Include keys for: `nav.today`, `nav.workout`, `nav.diet`, `nav.body`, `nav.advice`, `nav.agent`, `nav.settings`, `today.title`, `today.workout`, `today.diet`, `today.checkin`, `actions.save`, `actions.confirm`, `actions.cancel`.

- [ ] **Step 3: Add English messages**

Use matching keys with English values.

- [ ] **Step 4: Run build**

Run: `npm run build`  
Expected: PASS.

---

### Task 4: Mock API

**Files:**
- Create: `src/services/apiTypes.ts`
- Create: `src/services/mockApi.ts`

**Interfaces:**
- Consumes: domain types and demo data
- Produces: `api.getDemoUser()`, `api.getToday()`, `api.saveDailyCheckin()`, `api.confirmPlannedMeal()`, `api.saveWorkoutLog()`, `api.sendAgentMessage()`

- [ ] **Step 1: Create API response types**

Define:

```ts
export type ApiError = { code: string; message: string; details?: Record<string, unknown> };
export type ApiResponse<T> = { data: T; error: null } | { data: null; error: ApiError };
```

- [ ] **Step 2: Implement in-memory mock API**

Use module-level variables initialized from `demoData.ts`.

- [ ] **Step 3: Implement mock state changes**

Required behavior:

- `confirmPlannedMeal(meal_id)` adds a meal log and increases nutrition totals.
- `saveDailyCheckin(input)` stores today's check-in.
- `saveWorkoutLog(input)` stores a workout log and marks completion.
- `sendAgentMessage(message)` returns a `record_draft` for obvious workout or meal messages.

- [ ] **Step 4: Run build**

Run: `npm run build`  
Expected: PASS.

---

### Task 5: Business App Shell

**Files:**
- Create: `src/components/business/AppShell.tsx`
- Modify: `src/App.tsx`

**Interfaces:**
- Consumes: `useI18n`, navigation message keys
- Produces: route mode that can show either current Stitch prototype or new business Today page

- [ ] **Step 1: Preserve prototype route**

Move current Stitch loading logic from `src/App.tsx` to `src/pages/PrototypeRouter.tsx` without behavior changes.

- [ ] **Step 2: Add AppShell**

Create a shell with nav items and language selector.

- [ ] **Step 3: Add mode switch**

Make `/app` render business Today page and `/prototype` or existing routes render Stitch prototype.

- [ ] **Step 4: Run build**

Run: `npm run build`  
Expected: PASS.

---

### Task 6: Business Today Page

**Files:**
- Create: `src/pages/TodayPage.tsx`
- Create: `src/components/business/MetricCard.tsx`
- Create: `src/components/business/ProgressBar.tsx`
- Modify: `src/styles.css`

**Interfaces:**
- Consumes: `api.getToday()`, `api.saveDailyCheckin()`, `api.confirmPlannedMeal()`
- Produces: first business-backed page using mock data

- [ ] **Step 1: Load today data**

Use `useEffect` to call `api.getToday({ user_id: "demo-user-945" })`.

- [ ] **Step 2: Render summary**

Show goal, workout completion, calories, protein, weight delta, recovery status.

- [ ] **Step 3: Render workout card**

Show today's workout and exercise list.

- [ ] **Step 4: Render meal card**

Show today's meals and confirm planned meal buttons.

- [ ] **Step 5: Render check-in form**

Support weight, sleep, fatigue, soreness, notes.

- [ ] **Step 6: Run build**

Run: `npm run build`  
Expected: PASS.

---

### Task 7: Confirmation Dialog And Agent Drafts

**Files:**
- Create: `src/components/business/ConfirmDialog.tsx`
- Modify: `src/pages/TodayPage.tsx`

**Interfaces:**
- Consumes: `api.sendAgentMessage()`
- Produces: confirmation flow for record drafts

- [ ] **Step 1: Add generic confirm dialog**

Props: `open`, `title`, `children`, `confirmLabel`, `cancelLabel`, `onConfirm`, `onCancel`.

- [ ] **Step 2: Add small Agent input on Today page**

Send message through mock API.

- [ ] **Step 3: Show draft confirmation**

If response includes `record_draft.requires_confirmation`, show dialog before writing data.

- [ ] **Step 4: Run build**

Run: `npm run build`  
Expected: PASS.

---

### Task 8: Verification

**Files:**
- Modify: `design-qa.md`

**Interfaces:**
- Consumes: all previous tasks
- Produces: verification notes

- [ ] **Step 1: Run build**

Run: `npm run build`  
Expected: PASS.

- [ ] **Step 2: Start dev server**

Run: `npm run dev`  
Expected: Vite serves the app.

- [ ] **Step 3: Browser check**

Open `/app` and verify:

- Today data renders.
- Meal confirmation changes nutrition totals.
- Daily check-in saves visible state.
- Agent draft asks for confirmation.
- Language switch changes labels.

- [ ] **Step 4: Update QA notes**

Append the checked routes and results to `design-qa.md`.

