from typing import Literal

from pydantic import BaseModel, ConfigDict


Locale = Literal["zh-CN", "en-US"]
UnitSystem = Literal["metric", "imperial"]
Goal = Literal["fat_loss", "muscle_gain", "body_recomposition", "strength", "conditioning", "maintenance"]
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
