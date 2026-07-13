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
  accepted_status: "pending" | "accepted" | "dismissed" | "deferred";
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

export type WorkoutPageData = {
  plan: Plan;
  selected_day: WorkoutPlanDay;
  logs: WorkoutLog[];
  completion_rate: number;
  weekly_volume_sets: number;
};

export type DietPageData = {
  plan: Plan;
  selected_day: MealPlanDay;
  logs: MealLog[];
  targets: MacroTargets;
};

export type BodyPageData = {
  profile: UserProfile;
  metrics: BodyMetric[];
  latest_metric: BodyMetric;
  trend_7_day_kg: number;
  trend_30_day_kg: number;
  trend_90_day_kg: number;
};

export type AdvicePageData = {
  daily: AgentAdvice | null;
  weekly: AgentAdvice | null;
  adjustments: AgentAdvice[];
};

export type SettingsData = {
  user: User;
  profile: UserProfile;
  language: Locale;
  unit_system: UnitSystem;
};
