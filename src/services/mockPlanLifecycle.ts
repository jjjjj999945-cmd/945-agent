import type { CurrentPlanData, DietPageData, Plan, WorkoutPageData } from "../types/domain";
import { fail, ok, type ApiResponse } from "./apiTypes";

function unavailablePlan<T>(planState: CurrentPlanData): ApiResponse<T> {
  return fail("PLAN_UNAVAILABLE", "Current plan does not cover today.", {
    coverage_status: planState.coverage_status
  });
}

export function getMockWorkoutPageData(
  planState: CurrentPlanData,
  build: (plan: Plan) => WorkoutPageData = () => {
    throw new Error("A current plan is required to build workout data.");
  }
): ApiResponse<WorkoutPageData> {
  return planState.plan ? ok(build(planState.plan)) : unavailablePlan<WorkoutPageData>(planState);
}

export function getMockDietPageData(
  planState: CurrentPlanData,
  build: (plan: Plan) => DietPageData = () => {
    throw new Error("A current plan is required to build diet data.");
  }
): ApiResponse<DietPageData> {
  return planState.plan ? ok(build(planState.plan)) : unavailablePlan<DietPageData>(planState);
}
