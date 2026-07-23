import {
  DEMO_USER_ID,
  TODAY_DATE,
  createInitialTodayData,
  demoAdvice,
  demoBodyMetrics,
  demoPlan,
  demoProfile,
  demoUser,
  demoWeeklyAdvice
} from "../data/demoData";
import type {
  AdvicePageData,
  AgentMessage,
  AgentAdvice,
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
import { fail, ok, type ApiResponse } from "./apiTypes";

type DailyCheckinInput = Omit<DailyCheckin, "checkin_id" | "created_at" | "updated_at">;
type WorkoutLogInput = Omit<WorkoutLog, "workout_log_id" | "created_at" | "updated_at">;
type ManualMealLogInput = Omit<
  MealLog,
  "meal_log_id" | "source" | "calories" | "protein_g" | "carbs_g" | "fat_g" | "created_at" | "updated_at"
> & {
  foods: FoodLog[];
};

let todayData: TodayResponseData = createInitialTodayData();
let currentUser: User = demoUser;
let currentProfile: UserProfile = demoProfile;
let dailyCheckins: DailyCheckin[] = [];
let workoutLogs: WorkoutLog[] = [];
let mealLogs: MealLog[] = [];
let agentMessages: AgentMessage[] = [];
let bodyMetrics: BodyMetric[] = [...demoBodyMetrics];
let adviceItems: AgentAdvice[] = [demoAdvice, demoWeeklyAdvice];
let currentPlan: Plan = demoPlan;

function timestamp() {
  return new Date().toISOString();
}

function ensureDemoUser(user_id: string): ApiResponse<true> {
  if (user_id !== DEMO_USER_ID) {
    return fail("NOT_FOUND", "Demo user not found.", { user_id });
  }
  return ok(true);
}

function sumFoods(foods: FoodLog[]) {
  return foods.reduce(
    (total, food) => ({
      calories: total.calories + food.calories,
      protein_g: total.protein_g + food.protein_g,
      carbs_g: total.carbs_g + food.carbs_g,
      fat_g: total.fat_g + food.fat_g
    }),
    { calories: 0, protein_g: 0, carbs_g: 0, fat_g: 0 }
  );
}

function refreshTodayFromLogs() {
  const todayMealTotals = mealLogs
    .filter((log) => log.date === TODAY_DATE)
    .reduce(
      (total, log) => ({
        calories: total.calories + log.calories,
        protein_g: total.protein_g + log.protein_g
      }),
      { calories: 0, protein_g: 0 }
    );

  const completedWorkouts = workoutLogs.filter(
    (log) => log.status === "completed" || log.status === "partially_completed"
  ).length;

  todayData = {
    ...todayData,
    status_summary: {
      ...todayData.status_summary,
      calories_logged: Math.max(1480, todayMealTotals.calories),
      protein_logged_g: Math.max(102, todayMealTotals.protein_g),
      weekly_workouts_completed: Math.max(3, completedWorkouts)
    },
    daily_checkin: dailyCheckins.find((checkin) => checkin.date === TODAY_DATE) ?? null,
    latest_advice: demoAdvice
  };
}

export const api = {
  async getCurrentPlan(user_id = DEMO_USER_ID): Promise<ApiResponse<Plan>> {
    const user = ensureDemoUser(user_id);
    if (user.error) return user;
    return ok(currentPlan);
  },

  async generatePlan(input: { user_id: string; goal?: Plan["goal"] }): Promise<ApiResponse<Plan>> {
    const user = ensureDemoUser(input.user_id);
    if (user.error) return user;
    return ok({ ...currentPlan, plan_id: `plan-draft-${Date.now()}`, goal: input.goal ?? currentPlan.goal, status: "draft", created_at: timestamp(), updated_at: timestamp() });
  },

  async acceptPlan(input: { user_id: string; plan_id: string }): Promise<ApiResponse<Plan>> {
    const user = ensureDemoUser(input.user_id);
    if (user.error) return user;
    currentPlan = { ...currentPlan, plan_id: input.plan_id, status: "active", updated_at: timestamp() };
    return ok(currentPlan);
  },

  async adjustPlan(input: { user_id: string; plan_id: string; adjustment_type: string; reason: string; target_date?: string; target_exercise_id?: string; target_meal_id?: string; replacement_name?: string }): Promise<ApiResponse<Plan>> {
    const user = ensureDemoUser(input.user_id);
    if (user.error) return user;
    if (input.plan_id !== currentPlan.plan_id) return fail("NOT_FOUND", "Active plan not found.", { plan_id: input.plan_id });
    currentPlan = { ...currentPlan, plan_id: `plan-adjusted-${Date.now()}`, generated_by: "agent", updated_at: timestamp() };
    return ok(currentPlan);
  },
  async getDemoUser(): Promise<ApiResponse<User>> {
    return ok(currentUser);
  },

  async getProfile(user_id = DEMO_USER_ID): Promise<ApiResponse<UserProfile>> {
    const user = ensureDemoUser(user_id);
    if (user.error) return user;
    return ok(currentProfile);
  },

  async updateProfile(input: Partial<UserProfile> & { user_id: string }): Promise<ApiResponse<UserProfile>> {
    const user = ensureDemoUser(input.user_id);
    if (user.error) return user;

    currentProfile = {
      ...currentProfile,
      ...input,
      updated_at: timestamp()
    };

    if (input.user_id === currentUser.user_id && input.user_id) {
      currentUser = {
        ...currentUser,
        updated_at: timestamp()
      };
    }

    return ok(currentProfile);
  },

  async getToday(input: { user_id?: string; date?: string } = {}): Promise<ApiResponse<TodayResponseData>> {
    const user = ensureDemoUser(input.user_id ?? DEMO_USER_ID);
    if (user.error) return user;
    refreshTodayFromLogs();
    return ok({
      ...todayData,
      date: input.date ?? TODAY_DATE
    });
  },

  async getWorkout(user_id = DEMO_USER_ID): Promise<ApiResponse<WorkoutPageData>> {
    const user = ensureDemoUser(user_id);
    if (user.error) return user;

    const plannedSets = demoPlan.workout_plan.days.reduce(
      (sum, day) => sum + day.exercises.reduce((inner, exercise) => inner + exercise.sets, 0),
      0
    );

    return ok({
      plan: demoPlan,
      selected_day: demoPlan.workout_plan.days[0],
      logs: workoutLogs,
      completion_rate: todayData.status_summary.weekly_workouts_completed / todayData.status_summary.weekly_workouts_planned,
      weekly_volume_sets: plannedSets
    });
  },

  async getDiet(user_id = DEMO_USER_ID): Promise<ApiResponse<DietPageData>> {
    const user = ensureDemoUser(user_id);
    if (user.error) return user;

    return ok({
      plan: demoPlan,
      selected_day: demoPlan.meal_plan.days[0],
      logs: mealLogs,
      targets: demoPlan.meal_plan.daily_targets
    });
  },

  async getBodyMetrics(user_id = DEMO_USER_ID): Promise<ApiResponse<BodyPageData>> {
    const user = ensureDemoUser(user_id);
    if (user.error) return user;

    const sorted = [...bodyMetrics].sort((a, b) => a.date.localeCompare(b.date));
    const latest = sorted[sorted.length - 1];
    const first = sorted[0] ?? latest;

    return ok({
      profile: currentProfile,
      metrics: sorted,
      latest_metric: latest,
      trend_7_day_kg: latest.weight_kg - first.weight_kg,
      trend_30_day_kg: latest.weight_kg - first.weight_kg,
      trend_90_day_kg: latest.weight_kg - first.weight_kg
    });
  },

  async saveBodyMetric(input: Omit<BodyMetric, "metric_id" | "created_at">): Promise<ApiResponse<BodyMetric>> {
    const user = ensureDemoUser(input.user_id);
    if (user.error) return user;

    const saved: BodyMetric = {
      ...input,
      metric_id: `metric-${input.date}-${Date.now()}`,
      created_at: timestamp()
    };

    bodyMetrics = [...bodyMetrics.filter((metric) => !(metric.user_id === input.user_id && metric.date === input.date)), saved];
    return ok(saved);
  },

  async getAdvice(user_id = DEMO_USER_ID): Promise<ApiResponse<AdvicePageData>> {
    const user = ensureDemoUser(user_id);
    if (user.error) return user;

    return ok({
      daily: adviceItems.find((item) => item.type === "daily_advice") ?? null,
      weekly: adviceItems.find((item) => item.type === "weekly_summary") ?? null,
      adjustments: adviceItems.filter((item) => item.type === "plan_adjustment")
    });
  },

  async generateAdvice(input: { user_id: string; date: string }): Promise<ApiResponse<AgentAdvice[]>> {
    const user = ensureDemoUser(input.user_id);
    if (user.error) return user;
    return ok(adviceItems);
  },

  async updateAdviceStatus(input: {
    user_id: string;
    advice_id: string;
    accepted_status: AgentAdvice["accepted_status"];
  }): Promise<ApiResponse<AgentAdvice>> {
    const user = ensureDemoUser(input.user_id);
    if (user.error) return user;

    const existing = adviceItems.find((item) => item.advice_id === input.advice_id);
    if (!existing) return fail("NOT_FOUND", "Advice not found.", input);

    const updated = { ...existing, accepted_status: input.accepted_status };
    adviceItems = adviceItems.map((item) => (item.advice_id === input.advice_id ? updated : item));
    return ok(updated);
  },

  async getSettings(user_id = DEMO_USER_ID): Promise<ApiResponse<SettingsData>> {
    const user = ensureDemoUser(user_id);
    if (user.error) return user;

    return ok({
      user: currentUser,
      profile: currentProfile,
      language: currentUser.locale,
      unit_system: currentUser.unit_system
    });
  },

  async exportData(user_id = DEMO_USER_ID): Promise<ApiResponse<Record<string, unknown>>> {
    const user = ensureDemoUser(user_id);
    if (user.error) return user;
    return ok({ schema_version: "1.0", exported_at: timestamp(), user: currentUser, profile: currentProfile, plans: [currentPlan], workout_logs: workoutLogs, meal_logs: mealLogs, body_metrics: bodyMetrics, daily_checkins: dailyCheckins, advice: adviceItems, agent_messages: agentMessages });
  },

  async saveSettings(input: Partial<SettingsData> & { user_id: string }): Promise<ApiResponse<SettingsData>> {
    const user = ensureDemoUser(input.user_id);
    if (user.error) return user;

    currentUser = {
      ...currentUser,
      locale: input.language ?? currentUser.locale,
      unit_system: input.unit_system ?? currentUser.unit_system,
      updated_at: timestamp()
    };

    if (input.profile) {
      currentProfile = {
        ...currentProfile,
        ...input.profile,
        updated_at: timestamp()
      };
    }

    return ok({
      user: currentUser,
      profile: currentProfile,
      language: currentUser.locale,
      unit_system: currentUser.unit_system
    });
  },

  async saveDailyCheckin(input: DailyCheckinInput): Promise<ApiResponse<DailyCheckin>> {
    const user = ensureDemoUser(input.user_id);
    if (user.error) return user;

    const existing = dailyCheckins.find((checkin) => checkin.user_id === input.user_id && checkin.date === input.date);
    const saved: DailyCheckin = {
      ...existing,
      ...input,
      checkin_id: existing?.checkin_id ?? `checkin-${input.date}-${Date.now()}`,
      created_at: existing?.created_at ?? timestamp(),
      updated_at: timestamp()
    };

    dailyCheckins = existing
      ? dailyCheckins.map((checkin) => (checkin.checkin_id === existing.checkin_id ? saved : checkin))
      : [...dailyCheckins, saved];

    refreshTodayFromLogs();
    return ok(saved);
  },

  async saveWorkoutLog(input: WorkoutLogInput): Promise<ApiResponse<WorkoutLog>> {
    const user = ensureDemoUser(input.user_id);
    if (user.error) return user;

    const saved: WorkoutLog = {
      ...input,
      workout_log_id: `workout-${input.date}-${Date.now()}`,
      created_at: timestamp(),
      updated_at: timestamp()
    };

    workoutLogs = [...workoutLogs, saved];
    refreshTodayFromLogs();
    return ok(saved);
  },

  async confirmPlannedMeal(input: {
    user_id: string;
    plan_id: string;
    date: string;
    meal_id: string;
  }): Promise<ApiResponse<MealLog>> {
    const user = ensureDemoUser(input.user_id);
    if (user.error) return user;

    const day = demoPlan.meal_plan.days.find((item) => item.date === input.date);
    const meal = day?.meals.find((item) => item.meal_id === input.meal_id);
    if (!meal) {
      return fail("NOT_FOUND", "Planned meal not found.", input);
    }

    const saved: MealLog = {
      meal_log_id: `meal-log-${input.meal_id}-${Date.now()}`,
      user_id: input.user_id,
      plan_id: input.plan_id,
      date: input.date,
      meal_id: input.meal_id,
      meal_name: meal.name,
      source: "planned_meal_confirmation",
      foods: meal.foods,
      calories: meal.total_macros.calories,
      protein_g: meal.total_macros.protein_g,
      carbs_g: meal.total_macros.carbs_g,
      fat_g: meal.total_macros.fat_g,
      created_at: timestamp(),
      updated_at: timestamp()
    };

    mealLogs = [...mealLogs, saved];
    refreshTodayFromLogs();
    return ok(saved);
  },

  async saveManualMeal(input: ManualMealLogInput): Promise<ApiResponse<MealLog>> {
    const user = ensureDemoUser(input.user_id);
    if (user.error) return user;

    const totals = sumFoods(input.foods);
    const saved: MealLog = {
      ...input,
      meal_log_id: `meal-log-manual-${input.date}-${Date.now()}`,
      source: "manual_entry",
      calories: totals.calories,
      protein_g: totals.protein_g,
      carbs_g: totals.carbs_g,
      fat_g: totals.fat_g,
      created_at: timestamp(),
      updated_at: timestamp()
    };

    mealLogs = [...mealLogs, saved];
    refreshTodayFromLogs();
    return ok(saved);
  },

  async sendAgentMessage(input: {
    user_id: string;
    locale: "zh-CN" | "en-US";
    message: string;
    context?: Record<string, unknown>;
  }): Promise<ApiResponse<AgentMessage>> {
    const user = ensureDemoUser(input.user_id);
    if (user.error) return user;

    const normalized = input.message.toLowerCase();
    const recordDraft =
      normalized.includes("深蹲") || normalized.includes("squat")
        ? {
            type: "workout_log" as const,
            requires_confirmation: true as const,
            payload: {
              exercise_name: normalized.includes("深蹲") ? "深蹲" : "Squat",
              sets: 4,
              reps: 8,
              weight_kg: 80,
              effort_note: input.message
            }
          }
        : normalized.includes("吃") || normalized.includes("meal") || normalized.includes("food")
          ? {
            type: "meal_log" as const,
            requires_confirmation: true as const,
            payload: {
                meal_name: input.locale === "zh-CN" ? "手动记录" : "Manual entry",
                note: input.message
              }
            }
          : undefined;

    const userMessage: AgentMessage = {
      message_id: `msg-user-${Date.now()}`,
      user_id: input.user_id,
      role: "user",
      content: input.message,
      locale: input.locale,
      created_at: timestamp()
    };

    const agentMessage: AgentMessage = {
      message_id: `msg-agent-${Date.now()}`,
      user_id: input.user_id,
      role: "agent",
      content: recordDraft
        ? input.locale === "zh-CN"
          ? "我可以帮你整理成记录草稿。保存前请先确认。"
          : "I can turn that into a record draft. Please confirm before saving."
        : input.locale === "zh-CN"
          ? "我已读取你的问题。当前 demo 会优先基于今日计划、记录和建议回答。"
          : "I read your question. This demo answers from today's plan, logs, and advice first.",
      locale: input.locale,
      record_draft: recordDraft,
      created_at: timestamp()
    };

    agentMessages = [...agentMessages, userMessage, agentMessage];
    return ok(agentMessage);
  },

  async getAgentMessages(user_id = DEMO_USER_ID): Promise<ApiResponse<AgentMessage[]>> {
    const user = ensureDemoUser(user_id);
    if (user.error) return user;
    return ok(agentMessages);
  }
};
