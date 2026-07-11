import {
  DEMO_USER_ID,
  TODAY_DATE,
  createInitialTodayData,
  demoAdvice,
  demoPlan,
  demoProfile,
  demoUser
} from "../data/demoData";
import type {
  AgentMessage,
  DailyCheckin,
  FoodLog,
  MealLog,
  TodayResponseData,
  User,
  UserProfile,
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
                meal_name: "Manual entry",
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
        ? "我可以帮你整理成记录草稿。保存前请先确认。"
        : "我已读取你的问题。当前 demo 会优先基于今日计划、记录和建议回答。",
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
