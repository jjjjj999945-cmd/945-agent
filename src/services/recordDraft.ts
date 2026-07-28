import type { MealLog, Plan, RecordDraft, WorkoutLog } from "../types/domain";
import { api } from "./apiClient";
import { fail, type ApiResponse } from "./apiTypes";

type DraftContext = { user_id: string; date: string; plan_id?: string };

const MAX_DRAFT_SETS = 100;

function positiveIntegerField(payload: Record<string, unknown>, key: string, maximum?: number) {
  const value = payload[key];
  if (typeof value !== "number" || !Number.isInteger(value) || value <= 0) return null;
  if (maximum !== undefined && value > maximum) return null;
  return value;
}

function optionalWeight(payload: Record<string, unknown>) {
  const value = payload.weight_kg;
  if (value === undefined || value === null) {
    return { valid: true, value: undefined } as const;
  }
  if (typeof value !== "number" || !Number.isFinite(value) || value < 0) {
    return { valid: false, value: undefined } as const;
  }
  return { valid: true, value } as const;
}

export async function saveRecordDraft(
  draft: RecordDraft,
  context: DraftContext
): Promise<ApiResponse<WorkoutLog | MealLog | Plan>> {
  const payload = draft.payload;
  if (draft.type === "workout_log") {
    const exerciseName = typeof payload.exercise_name === "string" ? payload.exercise_name.trim() : "";
    const sets = positiveIntegerField(payload, "sets", MAX_DRAFT_SETS);
    const reps = positiveIntegerField(payload, "reps");
    const weight = optionalWeight(payload);
    if (!exerciseName || sets === null || reps === null || !weight.valid) {
      return fail("INVALID_DRAFT", "Workout draft is invalid.");
    }
    return api.saveWorkoutLog({
      user_id: context.user_id,
      plan_id: context.plan_id,
      date: context.date,
      status: "completed",
      exercises: [{
        name: exerciseName,
        sets: Array.from({ length: sets }, () => ({
          reps,
          weight_kg: weight.value,
          completed: true
        }))
      }],
      notes: typeof payload.effort_note === "string" ? payload.effort_note : undefined
    });
  }

  if (draft.type === "meal_log") {
    const mealName = typeof payload.meal_name === "string" ? payload.meal_name.trim() : "";
    if (!mealName) return fail("INVALID_DRAFT", "Meal draft is missing a meal name.");
    return api.saveManualMeal({
      user_id: context.user_id,
      plan_id: context.plan_id,
      date: context.date,
      meal_name: mealName,
      foods: [],
      notes: typeof payload.note === "string" ? payload.note : undefined
    });
  }

  if (draft.type === "plan_adjustment") {
    const adjustmentType = typeof payload.adjustment_type === "string" ? payload.adjustment_type : "";
    const reason = typeof payload.reason === "string" ? payload.reason.trim() : "";
    if (!adjustmentType || !reason) return fail("INVALID_DRAFT", "Plan adjustment draft is invalid.");
    if (!context.plan_id) return fail("PLAN_UNAVAILABLE", "Current plan does not cover today.");
    return api.adjustPlan({
      user_id: context.user_id,
      plan_id: context.plan_id,
      adjustment_type: adjustmentType,
      reason,
      target_date: typeof payload.target_date === "string" ? payload.target_date : context.date,
      target_exercise_id: typeof payload.target_exercise_id === "string" ? payload.target_exercise_id : undefined,
      target_meal_id: typeof payload.target_meal_id === "string" ? payload.target_meal_id : undefined,
      replacement_name: typeof payload.replacement_name === "string" ? payload.replacement_name : undefined
    });
  }

  return fail("DRAFT_TYPE_UNSUPPORTED", "This draft type cannot be saved yet.", { type: draft.type });
}
