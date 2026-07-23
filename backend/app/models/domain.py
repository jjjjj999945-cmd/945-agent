from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


Locale = Literal["zh-CN", "en-US"]
UnitSystem = Literal["metric", "imperial"]
Goal = Literal["fat_loss", "muscle_gain", "body_recomposition", "strength", "conditioning", "maintenance"]
ExperienceLevel = Literal["beginner", "novice", "intermediate", "advanced"]
RecoveryStatus = Literal["good", "normal", "fatigued"]
AdviceType = Literal["daily_advice", "weekly_summary", "plan_adjustment", "safety_warning"]
RiskLevel = Literal["low", "medium", "high"]
AdviceStatus = Literal["pending", "accepted", "dismissed", "deferred"]
PlanStatus = Literal["draft", "active", "archived"]
PlanGenerator = Literal["agent", "mock"]
CompletionStatus = Literal["planned", "completed", "partially_completed", "skipped"]
MealLogSource = Literal["planned_meal_confirmation", "manual_entry"]
Mood = Literal["low", "normal", "good"]


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class User(ApiModel):
    user_id: str
    display_name: str
    locale: Locale
    unit_system: UnitSystem
    created_at: str
    updated_at: str


class UserProfile(ApiModel):
    profile_id: str
    user_id: str
    age: int
    gender: str | None = None
    height_cm: float
    weight_kg: float
    goal: Goal
    experience_level: ExperienceLevel
    training_days_per_week: int
    training_duration_minutes: int
    equipment: list[str]
    dietary_preferences: list[str]
    allergies: list[str]
    constraints: list[str]
    updated_at: str


class ProfileCreateInput(ApiModel):
    user_id: str
    display_name: str
    age: int
    gender: str | None = None
    height_cm: float
    weight_kg: float
    goal: Goal
    experience_level: ExperienceLevel
    training_days_per_week: int
    training_duration_minutes: int
    equipment: list[str]
    dietary_preferences: list[str]
    allergies: list[str]
    constraints: list[str]
    locale: Locale
    unit_system: UnitSystem


class ProfilePatchInput(ApiModel):
    age: int | None = None
    gender: str | None = None
    height_cm: float | None = None
    weight_kg: float | None = None
    goal: Goal | None = None
    experience_level: ExperienceLevel | None = None
    training_days_per_week: int | None = None
    training_duration_minutes: int | None = None
    equipment: list[str] | None = None
    dietary_preferences: list[str] | None = None
    allergies: list[str] | None = None
    constraints: list[str] | None = None


class SettingsData(ApiModel):
    user: User
    profile: UserProfile
    language: Locale
    unit_system: UnitSystem


class SettingsPatchInput(ApiModel):
    user_id: str
    language: Locale | None = None
    unit_system: UnitSystem | None = None
    profile: ProfilePatchInput | None = None


class TodayUser(ApiModel):
    user_id: str
    display_name: str
    goal: Goal


class StatusSummary(ApiModel):
    weekly_workouts_completed: int
    weekly_workouts_planned: int
    calories_target: int
    calories_logged: int
    protein_target_g: int
    protein_logged_g: int
    weight_7_day_delta_kg: float
    recovery_status: RecoveryStatus


class PlannedExercise(ApiModel):
    exercise_id: str
    name: str
    target_muscles: list[str]
    sets: int
    reps: str
    target_weight: str | None = None
    rest_seconds: int
    notes: str | None = None


class WorkoutPlanDay(ApiModel):
    date: str
    name: str
    focus: str
    duration_minutes: int
    exercises: list[PlannedExercise]


class WorkoutPlan(ApiModel):
    days: list[WorkoutPlanDay]


class MacroTargets(ApiModel):
    calories: int
    protein_g: int
    carbs_g: int
    fat_g: int


class PlannedFood(ApiModel):
    name: str
    portion: str
    calories: int
    protein_g: int
    carbs_g: int
    fat_g: int


class PlannedMeal(ApiModel):
    meal_id: str
    name: str
    foods: list[PlannedFood]
    total_macros: MacroTargets


class MealPlanDay(ApiModel):
    date: str
    meals: list[PlannedMeal]


class MealPlan(ApiModel):
    daily_targets: MacroTargets
    days: list[MealPlanDay]


class Plan(ApiModel):
    plan_id: str
    user_id: str
    goal: Goal
    status: PlanStatus
    start_date: str
    end_date: str
    workout_plan: WorkoutPlan
    meal_plan: MealPlan
    generated_by: PlanGenerator
    created_at: str
    updated_at: str


class AuthCredential(ApiModel):
    email: str
    user_id: str
    password_hash: str
    password_salt: str
    created_at: str


class RegisterInput(ApiModel):
    display_name: str
    email: str
    password: str


class LoginInput(ApiModel):
    email: str
    password: str


class AuthSession(ApiModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    user: User


class PlanGenerateInput(ApiModel):
    user_id: str
    goal: Goal | None = None
    days: int = 7
    generate_workout_plan: bool = True
    generate_meal_plan: bool = True


class PlanAcceptInput(ApiModel):
    user_id: str


class PlanAdjustmentInput(ApiModel):
    user_id: str
    adjustment_type: Literal["reduce_intensity", "increase_intensity", "change_schedule", "swap_exercise", "skip_workout", "swap_meal", "adjust_nutrition"]
    reason: str
    confirmed: Literal[True]
    target_date: str | None = None
    target_exercise_id: str | None = None
    target_meal_id: str | None = None
    replacement_name: str | None = None


class DailyCheckin(ApiModel):
    checkin_id: str
    user_id: str
    date: str
    weight_kg: float | None = None
    sleep_hours: float | None = None
    sleep_quality: int | None = None
    fatigue_level: int | None = None
    soreness_level: int | None = None
    stress_level: int | None = None
    mood: Mood | None = None
    notes: str | None = None
    created_at: str
    updated_at: str


class DailyCheckinInput(ApiModel):
    user_id: str
    date: str
    weight_kg: float | None = None
    sleep_hours: float | None = None
    sleep_quality: int | None = None
    fatigue_level: int | None = None
    soreness_level: int | None = None
    stress_level: int | None = None
    mood: Mood | None = None
    notes: str | None = None


class BodyMetricInput(ApiModel):
    user_id: str
    date: str
    weight_kg: float
    body_fat_percentage: float | None = None
    waist_cm: float | None = None
    chest_cm: float | None = None
    hip_cm: float | None = None
    arm_cm: float | None = None
    bmi: float | None = None
    notes: str | None = None


class BodyMetric(BodyMetricInput):
    metric_id: str
    created_at: str


class AgentAdvice(ApiModel):
    advice_id: str
    user_id: str
    date: str
    type: AdviceType
    title: str
    content: str
    reason: str
    related_data: list[str]
    recommended_actions: list[str]
    risk_level: RiskLevel
    accepted_status: AdviceStatus
    created_at: str


class AdvicePageData(ApiModel):
    daily: AgentAdvice | None
    weekly: AgentAdvice | None
    adjustments: list[AgentAdvice]


class AdviceStatusInput(ApiModel):
    user_id: str
    accepted_status: AdviceStatus


class FeedbackGenerateInput(ApiModel):
    user_id: str
    date: str


class RecordDraft(ApiModel):
    type: Literal["workout_log", "meal_log", "daily_checkin", "plan_adjustment"]
    requires_confirmation: Literal[True]
    payload: dict[str, Any]


class AgentMessage(ApiModel):
    message_id: str
    user_id: str
    role: Literal["user", "agent"]
    content: str
    locale: Locale
    record_draft: RecordDraft | None = None
    created_at: str


class UserMemorySummary(ApiModel):
    summary_id: str
    user_id: str
    week_start: str
    week_end: str
    content: str
    metadata: dict[str, str]
    created_at: str


class AgentChatInput(ApiModel):
    user_id: str
    locale: Locale
    message: str
    context: dict[str, Any] | None = None


class ExerciseSetLog(ApiModel):
    reps: int
    weight_kg: float | None = None
    completed: bool | None = None


class ExerciseLog(ApiModel):
    exercise_id: str | None = None
    name: str
    sets: list[ExerciseSetLog]


class WorkoutLogInput(ApiModel):
    user_id: str
    plan_id: str | None = None
    date: str
    status: CompletionStatus
    duration_minutes: int | None = None
    exercises: list[ExerciseLog]
    rpe: int | None = None
    notes: str | None = None


class WorkoutLog(WorkoutLogInput):
    workout_log_id: str
    created_at: str
    updated_at: str


class FoodLog(PlannedFood):
    pass


class ConfirmPlannedMealInput(ApiModel):
    user_id: str
    plan_id: str
    date: str
    meal_id: str


class ManualMealLogInput(ApiModel):
    user_id: str
    plan_id: str | None = None
    date: str
    meal_id: str | None = None
    meal_name: str
    foods: list[FoodLog]
    notes: str | None = None


class MealLog(ApiModel):
    meal_log_id: str
    user_id: str
    plan_id: str | None = None
    date: str
    meal_id: str | None = None
    meal_name: str
    source: MealLogSource
    foods: list[FoodLog]
    calories: int
    protein_g: int
    carbs_g: int
    fat_g: int
    notes: str | None = None
    created_at: str
    updated_at: str


class TodayResponseData(ApiModel):
    date: str
    user: TodayUser
    status_summary: StatusSummary
    today_workout: WorkoutPlanDay | None
    today_meals: list[PlannedMeal]
    daily_checkin: DailyCheckin | None
    latest_advice: AgentAdvice | None
