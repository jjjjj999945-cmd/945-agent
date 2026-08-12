import { demoPlan, TODAY_DATE } from "../data/demoData";
import { api } from "./apiClient";
import { fail, type ApiResponse } from "./apiTypes";
import type { MealLog, RecordDraft, WorkoutLog } from "../types/domain";

type DraftContext = {
  user_id: string;
  date?: string;
};

export async function saveRecordDraft(
  draft: RecordDraft,
  context: DraftContext
): Promise<ApiResponse<WorkoutLog | MealLog>> {
  const date = context.date ?? TODAY_DATE;

  if (draft.type === "workout_log") {
    const exercise_name = typeof draft.payload.exercise_name === "string" ? draft.payload.exercise_name : "";
    const sets = Number(draft.payload.sets);
    const reps = Number(draft.payload.reps);
    const weight_kg = Number(draft.payload.weight_kg);
    if (!exercise_name || !Number.isInteger(sets) || !Number.isInteger(reps) || sets < 1 || reps < 1) {
      return fail("DRAFT_PAYLOAD_INVALID", "Workout draft is missing required exercise details.");
    }

    return api.saveWorkoutLog({
      user_id: context.user_id,
      plan_id: demoPlan.plan_id,
      date,
      status: "completed",
      exercises: [{
        name: exercise_name,
        sets: Array.from({ length: sets }, () => ({
          reps,
          weight_kg: Number.isFinite(weight_kg) ? weight_kg : undefined,
          completed: true
        }))
      }],
      notes: typeof draft.payload.effort_note === "string" ? draft.payload.effort_note : undefined
    });
  }

  return fail(
    "DRAFT_TYPE_UNSUPPORTED",
    "This draft needs additional structured details before it can be saved."
  );
}
