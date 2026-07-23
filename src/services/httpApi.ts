import {
  DEMO_USER_ID,
  TODAY_DATE,
  demoBodyMetrics,
  demoPlan,
  demoProfile
} from "../data/demoData";
import type {
  AdvicePageData,
  AgentAdvice,
  AgentMessage,
  BodyMetric,
  BodyPageData,
  DailyCheckin,
  DietPageData,
  FoodLog,
  MealLog,
  Plan,
  SettingsData,
  TodayResponseData,
  User,
  UserProfile,
  WorkoutPageData,
  WorkoutLog
} from "../types/domain";
import { fail, type ApiResponse } from "./apiTypes";

type DailyCheckinInput = Omit<DailyCheckin, "checkin_id" | "created_at" | "updated_at">;
type WorkoutLogInput = Omit<WorkoutLog, "workout_log_id" | "created_at" | "updated_at">;
type ManualMealLogInput = Omit<
  MealLog,
  "meal_log_id" | "source" | "calories" | "protein_g" | "carbs_g" | "fat_g" | "created_at" | "updated_at"
> & {
  foods: FoodLog[];
};

const API_BASE_URL = import.meta.env.VITE_945_API_BASE_URL ?? "http://127.0.0.1:8000";

function isApiResponse<T>(value: unknown): value is ApiResponse<T> {
  if (!value || typeof value !== "object") return false;
  const candidate = value as { data?: unknown; error?: unknown };
  if (!("data" in candidate) || !("error" in candidate)) return false;
  if (candidate.error === null) return candidate.data !== null;
  if (candidate.data !== null || !candidate.error || typeof candidate.error !== "object") return false;
  const errorValue = candidate.error as { code?: unknown; message?: unknown };
  return typeof errorValue.code === "string" && typeof errorValue.message === "string";
}

function hasValidationDetail(value: unknown): value is { detail: unknown[] } {
  return (
    !!value &&
    typeof value === "object" &&
    "detail" in value &&
    Array.isArray((value as { detail?: unknown }).detail)
  );
}

async function request<T>(path: string, init?: RequestInit): Promise<ApiResponse<T>> {
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...init?.headers
      }
    });
    let body: unknown;
    try {
      body = await response.json();
    } catch {
      return fail("HTTP_ERROR", "945 backend returned an invalid response.", {
        status: response.status,
        path
      });
    }

    if (isApiResponse<T>(body)) return body;
    if (response.status === 422 && hasValidationDetail(body)) {
      return fail("VALIDATION_ERROR", "Request validation failed.", {
        status: response.status,
        detail: body.detail
      });
    }
    return fail("HTTP_ERROR", "945 backend returned an invalid response.", {
      status: response.status,
      path
    });
  } catch (error) {
    return fail("NETWORK_ERROR", "Unable to reach 945 backend.", {
      base_url: API_BASE_URL,
      message: error instanceof Error ? error.message : String(error)
    });
  }
}

function withQuery(path: string, params: Record<string, string | undefined>) {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined) query.set(key, value);
  }
  const queryString = query.toString();
  return queryString ? `${path}?${queryString}` : path;
}

function post<T>(path: string, body: unknown) {
  return request<T>(path, {
    method: "POST",
    body: JSON.stringify(body)
  });
}

function patch<T>(path: string, body: unknown) {
  return request<T>(path, {
    method: "PATCH",
    body: JSON.stringify(body)
  });
}

async function getCurrentPlan(user_id = DEMO_USER_ID) {
  return request<typeof demoPlan>(withQuery("/api/plans/current", { user_id }));
}

async function getWorkoutLogs(user_id = DEMO_USER_ID) {
  return request<WorkoutLog[]>(withQuery("/api/workout-logs", { user_id }));
}

async function getMealLogs(user_id = DEMO_USER_ID) {
  return request<MealLog[]>(withQuery("/api/meal-logs", { user_id }));
}

function getLatestMetric(metrics: BodyMetric[]) {
  const sorted = [...metrics].sort((a, b) => a.date.localeCompare(b.date));
  return sorted[sorted.length - 1];
}

export const httpApi = {
  async getCurrentPlan(user_id = DEMO_USER_ID): Promise<ApiResponse<Plan>> {
    return getCurrentPlan(user_id);
  },

  async generatePlan(input: { user_id: string; goal?: Plan["goal"] }): Promise<ApiResponse<Plan>> {
    return post<Plan>("/api/plans/generate", input);
  },

  async acceptPlan(input: { user_id: string; plan_id: string }): Promise<ApiResponse<Plan>> {
    return post<Plan>(`/api/plans/${input.plan_id}/accept`, { user_id: input.user_id });
  },

  async adjustPlan(input: { user_id: string; plan_id: string; adjustment_type: string; reason: string; target_date?: string; target_exercise_id?: string; target_meal_id?: string; replacement_name?: string }): Promise<ApiResponse<Plan>> {
    return post<Plan>(`/api/plans/${input.plan_id}/adjust`, {
      user_id: input.user_id,
      adjustment_type: input.adjustment_type,
      reason: input.reason,
      target_date: input.target_date,
      target_exercise_id: input.target_exercise_id,
      target_meal_id: input.target_meal_id,
      replacement_name: input.replacement_name,
      confirmed: true
    });
  },
  async getDemoUser(): Promise<ApiResponse<User>> {
    return request<User>("/api/demo-user");
  },

  async getProfile(user_id = DEMO_USER_ID): Promise<ApiResponse<UserProfile>> {
    return request<UserProfile>(`/api/profile/${user_id}`);
  },

  async updateProfile(input: Partial<UserProfile> & { user_id: string }): Promise<ApiResponse<UserProfile>> {
    return patch<UserProfile>(`/api/profile/${input.user_id}`, input);
  },

  async getToday(input: { user_id?: string; date?: string } = {}): Promise<ApiResponse<TodayResponseData>> {
    return request<TodayResponseData>(
      withQuery("/api/today", {
        user_id: input.user_id ?? DEMO_USER_ID,
        date: input.date ?? TODAY_DATE
      })
    );
  },

  async getWorkout(user_id = DEMO_USER_ID): Promise<ApiResponse<WorkoutPageData>> {
    const [planResponse, logsResponse, todayResponse] = await Promise.all([
      getCurrentPlan(user_id),
      getWorkoutLogs(user_id),
      this.getToday({ user_id, date: TODAY_DATE })
    ]);
    if (planResponse.error) return planResponse;
    if (logsResponse.error) return logsResponse;
    if (todayResponse.error) return todayResponse;

    const plannedSets = planResponse.data.workout_plan.days.reduce(
      (sum, day) => sum + day.exercises.reduce((inner, exercise) => inner + exercise.sets, 0),
      0
    );

    return {
      data: {
        plan: planResponse.data,
        selected_day: planResponse.data.workout_plan.days[0],
        logs: logsResponse.data,
        completion_rate:
          todayResponse.data.status_summary.weekly_workouts_completed /
          todayResponse.data.status_summary.weekly_workouts_planned,
        weekly_volume_sets: plannedSets
      },
      error: null
    };
  },

  async getDiet(user_id = DEMO_USER_ID): Promise<ApiResponse<DietPageData>> {
    const [planResponse, logsResponse] = await Promise.all([getCurrentPlan(user_id), getMealLogs(user_id)]);
    if (planResponse.error) return planResponse;
    if (logsResponse.error) return logsResponse;

    return {
      data: {
        plan: planResponse.data,
        selected_day: planResponse.data.meal_plan.days[0],
        logs: logsResponse.data,
        targets: planResponse.data.meal_plan.daily_targets
      },
      error: null
    };
  },

  async getBodyMetrics(user_id = DEMO_USER_ID): Promise<ApiResponse<BodyPageData>> {
    const [profileResponse, metricsResponse] = await Promise.all([
      this.getProfile(user_id),
      request<BodyMetric[]>(withQuery("/api/body-metrics", { user_id }))
    ]);
    if (profileResponse.error) return profileResponse;
    if (metricsResponse.error) return metricsResponse;

    const metrics = metricsResponse.data.length ? metricsResponse.data : demoBodyMetrics;
    const latest = getLatestMetric(metrics) ?? demoBodyMetrics[demoBodyMetrics.length - 1];
    const first = metrics[0] ?? latest;

    return {
      data: {
        profile: profileResponse.data ?? demoProfile,
        metrics,
        latest_metric: latest,
        trend_7_day_kg: latest.weight_kg - first.weight_kg,
        trend_30_day_kg: latest.weight_kg - first.weight_kg,
        trend_90_day_kg: latest.weight_kg - first.weight_kg
      },
      error: null
    };
  },

  async saveBodyMetric(input: Omit<BodyMetric, "metric_id" | "created_at">): Promise<ApiResponse<BodyMetric>> {
    return post<BodyMetric>("/api/body-metrics", input);
  },

  async getAdvice(user_id = DEMO_USER_ID): Promise<ApiResponse<AdvicePageData>> {
    return request<AdvicePageData>(withQuery("/api/advice", { user_id }));
  },

  async generateAdvice(input: { user_id: string; date: string }): Promise<ApiResponse<AgentAdvice[]>> {
    return post<AgentAdvice[]>("/api/advice/generate", input);
  },

  async updateAdviceStatus(input: {
    user_id: string;
    advice_id: string;
    accepted_status: AgentAdvice["accepted_status"];
  }): Promise<ApiResponse<AgentAdvice>> {
    return patch<AgentAdvice>(`/api/advice/${input.advice_id}/status`, {
      user_id: input.user_id,
      accepted_status: input.accepted_status
    });
  },

  async getSettings(user_id = DEMO_USER_ID): Promise<ApiResponse<SettingsData>> {
    return request<SettingsData>(withQuery("/api/settings", { user_id }));
  },

  async exportData(user_id = DEMO_USER_ID): Promise<ApiResponse<Record<string, unknown>>> {
    return request<Record<string, unknown>>(withQuery("/api/settings/export", { user_id }));
  },

  async saveSettings(input: Partial<SettingsData> & { user_id: string }): Promise<ApiResponse<SettingsData>> {
    const profile = input.profile
      ? {
          age: input.profile.age,
          gender: input.profile.gender,
          height_cm: input.profile.height_cm,
          weight_kg: input.profile.weight_kg,
          goal: input.profile.goal,
          experience_level: input.profile.experience_level,
          training_days_per_week: input.profile.training_days_per_week,
          training_duration_minutes: input.profile.training_duration_minutes,
          equipment: input.profile.equipment,
          dietary_preferences: input.profile.dietary_preferences,
          allergies: input.profile.allergies,
          constraints: input.profile.constraints
        }
      : undefined;

    return patch<SettingsData>("/api/settings", {
      user_id: input.user_id,
      language: input.language,
      unit_system: input.unit_system,
      profile
    });
  },

  async saveDailyCheckin(input: DailyCheckinInput): Promise<ApiResponse<DailyCheckin>> {
    return post<DailyCheckin>("/api/daily-checkins", input);
  },

  async saveWorkoutLog(input: WorkoutLogInput): Promise<ApiResponse<WorkoutLog>> {
    return post<WorkoutLog>("/api/workout-logs", input);
  },

  async confirmPlannedMeal(input: {
    user_id: string;
    plan_id: string;
    date: string;
    meal_id: string;
  }): Promise<ApiResponse<MealLog>> {
    return post<MealLog>("/api/meal-logs/confirm-planned-meal", input);
  },

  async saveManualMeal(input: ManualMealLogInput): Promise<ApiResponse<MealLog>> {
    return post<MealLog>("/api/meal-logs", input);
  },

  async sendAgentMessage(input: {
    user_id: string;
    locale: "zh-CN" | "en-US";
    message: string;
    context?: Record<string, unknown>;
  }): Promise<ApiResponse<AgentMessage>> {
    return post<AgentMessage>("/api/agent/chat", input);
  },

  async getAgentMessages(user_id = DEMO_USER_ID): Promise<ApiResponse<AgentMessage[]>> {
    return request<AgentMessage[]>(withQuery("/api/agent/messages", { user_id }));
  }
};
