import type { Locale } from "../types/domain";

export type MessageKey =
  | "nav.today"
  | "nav.workout"
  | "nav.diet"
  | "nav.body"
  | "nav.advice"
  | "nav.agent"
  | "nav.settings"
  | "today.title"
  | "today.subtitle"
  | "today.summary"
  | "today.workout"
  | "today.diet"
  | "today.checkin"
  | "today.advice"
  | "today.weeklyProgress"
  | "metrics.goal"
  | "metrics.workouts"
  | "metrics.calories"
  | "metrics.protein"
  | "metrics.weightTrend"
  | "metrics.recovery"
  | "actions.save"
  | "actions.confirm"
  | "actions.cancel"
  | "actions.complete"
  | "actions.partial"
  | "actions.skip"
  | "actions.send"
  | "actions.viewReason"
  | "actions.adjustToday"
  | "empty.noPlan"
  | "empty.noWorkout"
  | "empty.noMeals"
  | "empty.noAdvice"
  | "status.loading"
  | "status.saving"
  | "status.saved"
  | "status.error"
  | "safety.nonMedical"
  | "safety.highRisk";

export type Messages = Record<MessageKey, string>;

export type I18nBundle = {
  locale: Locale;
  messages: Messages;
};
