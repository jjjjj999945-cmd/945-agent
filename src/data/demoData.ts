import type {
  AgentAdvice,
  BodyMetric,
  Plan,
  TodayResponseData,
  User,
  UserProfile
} from "../types/domain";

// HTTP mode replaces this with the authenticated user's ID after a full session reload.
export const DEMO_USER_ID = window.localStorage.getItem("945.auth.user_id") ?? "demo-user-945";
export const TODAY_DATE = "2026-07-11";

const now = "2026-07-11T00:00:00.000Z";

export const demoUser: User = {
  user_id: DEMO_USER_ID,
  display_name: "Alex",
  locale: "zh-CN",
  unit_system: "metric",
  created_at: now,
  updated_at: now
};

export const demoProfile: UserProfile = {
  profile_id: "profile-demo-user-945",
  user_id: DEMO_USER_ID,
  age: 29,
  gender: "optional",
  height_cm: 175,
  weight_kg: 76,
  goal: "body_recomposition",
  experience_level: "novice",
  training_days_per_week: 4,
  training_duration_minutes: 60,
  equipment: ["dumbbells", "gym"],
  dietary_preferences: ["high_protein"],
  allergies: [],
  constraints: ["busy_weekdays"],
  updated_at: now
};

export const demoPlan: Plan = {
  plan_id: "plan-2026-07-11-demo",
  user_id: DEMO_USER_ID,
  goal: "body_recomposition",
  status: "active",
  start_date: "2026-07-11",
  end_date: "2026-07-17",
  generated_by: "mock",
  created_at: now,
  updated_at: now,
  workout_plan: {
    days: [
      {
        date: TODAY_DATE,
        name: "上肢力量",
        focus: "chest_back_shoulders",
        duration_minutes: 55,
        exercises: [
          {
            exercise_id: "ex-db-press",
            name: "哑铃卧推",
            target_muscles: ["胸部", "肱三头肌"],
            sets: 4,
            reps: "8-10",
            target_weight: "moderate",
            rest_seconds: 90
          },
          {
            exercise_id: "ex-row",
            name: "坐姿绳索划船",
            target_muscles: ["背部"],
            sets: 4,
            reps: "10-12",
            target_weight: "moderate",
            rest_seconds: 90
          },
          {
            exercise_id: "ex-db-shoulder-press",
            name: "哑铃推肩",
            target_muscles: ["肩部", "肱三头肌"],
            sets: 3,
            reps: "8-10",
            target_weight: "moderate",
            rest_seconds: 90
          }
        ]
      },
      {
        date: "2026-07-13",
        name: "下肢力量",
        focus: "legs_glutes",
        duration_minutes: 60,
        exercises: [
          {
            exercise_id: "ex-squat",
            name: "杠铃深蹲",
            target_muscles: ["股四头肌", "臀部"],
            sets: 4,
            reps: "6-8",
            target_weight: "moderate_heavy",
            rest_seconds: 120
          }
        ]
      }
    ]
  },
  meal_plan: {
    daily_targets: {
      calories: 2300,
      protein_g: 160,
      carbs_g: 240,
      fat_g: 70
    },
    days: [
      {
        date: TODAY_DATE,
        meals: [
          {
            meal_id: "meal-breakfast-1",
            name: "早餐",
            foods: [
              {
                name: "希腊酸奶",
                portion: "250g",
                calories: 180,
                protein_g: 24,
                carbs_g: 12,
                fat_g: 4
              },
              {
                name: "蓝莓",
                portion: "100g",
                calories: 57,
                protein_g: 1,
                carbs_g: 14,
                fat_g: 0
              },
              {
                name: "燕麦片",
                portion: "40g",
                calories: 150,
                protein_g: 5,
                carbs_g: 27,
                fat_g: 3
              }
            ],
            total_macros: {
              calories: 387,
              protein_g: 30,
              carbs_g: 53,
              fat_g: 7
            }
          },
          {
            meal_id: "meal-lunch-1",
            name: "午餐",
            foods: [
              {
                name: "鸡胸肉饭碗",
                portion: "1 bowl",
                calories: 620,
                protein_g: 42,
                carbs_g: 78,
                fat_g: 16
              }
            ],
            total_macros: {
              calories: 620,
              protein_g: 42,
              carbs_g: 78,
              fat_g: 16
            }
          },
          {
            meal_id: "meal-dinner-1",
            name: "晚餐",
            foods: [
              {
                name: "三文鱼",
                portion: "160g",
                calories: 330,
                protein_g: 36,
                carbs_g: 0,
                fat_g: 20
              },
              {
                name: "红薯",
                portion: "220g",
                calories: 190,
                protein_g: 4,
                carbs_g: 44,
                fat_g: 0
              },
              {
                name: "混合蔬菜",
                portion: "200g",
                calories: 90,
                protein_g: 5,
                carbs_g: 16,
                fat_g: 1
              }
            ],
            total_macros: {
              calories: 610,
              protein_g: 45,
              carbs_g: 60,
              fat_g: 21
            }
          }
        ]
      }
    ]
  }
};

export const demoAdvice: AgentAdvice = {
  advice_id: "advice-2026-07-11-1",
  user_id: DEMO_USER_ID,
  date: TODAY_DATE,
  type: "daily_advice",
  title: "今天保持计划，但降低最后一组强度",
  content:
    "你最近训练完成率稳定，但疲劳评分略高。今天可以按计划训练，最后一个复合动作保留 2 次余力。",
  reason: "最近 3 天睡眠良好，但昨天主观强度为 9。",
  related_data: ["workout_logs", "daily_checkins"],
  recommended_actions: ["按计划训练", "最后一组不要力竭"],
  risk_level: "low",
  accepted_status: "pending",
  created_at: now
};

export const demoWeeklyAdvice: AgentAdvice = {
  advice_id: "advice-weekly-001",
  user_id: DEMO_USER_ID,
  date: TODAY_DATE,
  type: "weekly_summary",
  title: "本周执行稳定，但恢复信号偏疲劳",
  content: "你完成了大部分训练计划，饮食蛋白质基本达标。建议下周保留力量训练频率，但降低一次高强度腿部训练量。",
  reason: "训练完成率较好，但疲劳和酸痛评分连续两天偏高。",
  related_data: ["weekly_workouts_completed", "fatigue_level", "soreness_level"],
  recommended_actions: ["下周腿部训练减少 2 组", "保持每日蛋白质目标", "睡眠低于 7 小时时降低训练强度"],
  risk_level: "medium",
  accepted_status: "pending",
  created_at: "2026-07-11T09:00:00.000Z"
};

export const demoBodyMetrics: BodyMetric[] = [
  {
    metric_id: "metric-2026-07-05",
    user_id: DEMO_USER_ID,
    date: "2026-07-05",
    weight_kg: 76.0,
    body_fat_percentage: 18.8,
    waist_cm: 84,
    bmi: 24.8,
    created_at: "2026-07-05T00:00:00.000Z"
  },
  {
    metric_id: "metric-2026-07-11",
    user_id: DEMO_USER_ID,
    date: TODAY_DATE,
    weight_kg: 75.6,
    body_fat_percentage: 18.5,
    waist_cm: 83,
    bmi: 24.7,
    created_at: now
  }
];

export function createInitialTodayData(): TodayResponseData {
  const todayWorkout = demoPlan.workout_plan.days.find((day) => day.date === TODAY_DATE) ?? null;
  const todayMealPlan = demoPlan.meal_plan.days.find((day) => day.date === TODAY_DATE);

  return {
    date: TODAY_DATE,
    user: {
      user_id: demoUser.user_id,
      display_name: demoUser.display_name,
      goal: demoProfile.goal
    },
    status_summary: {
      weekly_workouts_completed: 3,
      weekly_workouts_planned: 4,
      calories_target: demoPlan.meal_plan.daily_targets.calories,
      calories_logged: 1480,
      protein_target_g: demoPlan.meal_plan.daily_targets.protein_g,
      protein_logged_g: 102,
      weight_7_day_delta_kg: -0.4,
      recovery_status: "normal"
    },
    today_workout: todayWorkout,
    today_meals: todayMealPlan?.meals ?? [],
    daily_checkin: null,
    latest_advice: demoAdvice
  };
}
