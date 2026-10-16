import { useEffect, useMemo, useState } from "react";
import { MetricCard } from "../components/business/MetricCard";
import { PageLoadState } from "../components/business/PageLoadState";
import { ProgressBar } from "../components/business/ProgressBar";
import { DEMO_USER_ID } from "../data/demoData";
import { appToday } from "../services/dateContext";
import { usePlanContext } from "../contexts/PlanContext";
import { createTranslator } from "../i18n";
import { api } from "../services/apiClient";
import type { DailyCheckin, Locale, PlannedMeal, TodayResponseData } from "../types/domain";

type TodayPageProps = {
  locale: Locale;
  onNavigate?: (path: string) => void;
};

type CheckinForm = {
  weight_kg: string;
  sleep_hours: string;
  fatigue_level: string;
  soreness_level: string;
  notes: string;
};

const initialCheckinForm: CheckinForm = {
  weight_kg: "",
  sleep_hours: "",
  fatigue_level: "3",
  soreness_level: "2",
  notes: ""
};

export function TodayPage({ locale, onNavigate }: TodayPageProps) {
  const t = createTranslator(locale);
  const { currentPlan } = usePlanContext();
  const [today, setToday] = useState<TodayResponseData | null>(null);
  const [checkin, setCheckin] = useState<CheckinForm>(initialCheckinForm);
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState("");

  useEffect(() => {
    void loadToday();
  }, []);

  async function loadToday() {
    const response = await api.getToday({ user_id: DEMO_USER_ID, date: appToday });
    if (response.error) {
      setNotice(response.error.message);
      return;
    }
    setToday(response.data);
  }

  const workout = today?.today_workout;
  const meals = today?.today_meals ?? [];
  const summary = today?.status_summary;
  const planNeedsRenewal = !workout && meals.length === 0;
  const isChinese = locale === "zh-CN";
  const coachCopy = {
    eyebrow: isChinese ? "945 今日状态" : "945 Readiness",
    start: isChinese ? "开始今日计划" : "Start today",
    review: isChinese ? "查看调整" : "Review adjustment",
    insight: isChinese ? "智能教练" : "Coach Agent",
    protein: isChinese ? "蛋白质" : "Protein",
    workouts: isChinese ? "训练" : "Workouts",
    calories: isChinese ? "热量" : "Calories",
    recovery: isChinese ? "恢复" : "Recovery",
  };
  const goalLabel = isChinese && today?.user.goal === "body_recomposition" ? "身体重组" : (today?.user.goal.replace(/_/g, " ") ?? "");
  const recoveryLabel = isChinese && summary?.recovery_status === "normal" ? "正常" : (summary?.recovery_status ?? "");
  const focusLabel = workout?.focus.replace(/_/g, " ");
  const riskLabel = isChinese && today?.latest_advice?.risk_level === "low" ? "低风险" : today?.latest_advice?.risk_level;
  const headline = today?.user.display_name
    ? (isChinese ? `你好，${today.user.display_name}。` : `Hello, ${today.user.display_name}.`)
    : (isChinese ? "今日安排" : "Today");
  const intro = today?.latest_advice?.content
    ?? (workout
      ? (isChinese ? "已为你准备今日训练与饮食计划。" : "Your training and meal plan are ready.")
      : (isChinese ? "暂时没有今日安排。" : "There is no plan for today."));

  const mealTotal = useMemo(
    () =>
      meals.reduce(
        (total, meal) => ({
          calories: total.calories + meal.total_macros.calories,
          protein_g: total.protein_g + meal.total_macros.protein_g
        }),
        { calories: 0, protein_g: 0 }
      ),
    [meals]
  );

  function getActivePlanId() {
    if (!currentPlan) {
      setNotice("当前计划没有覆盖今天。");
      return null;
    }
    return currentPlan.plan_id;
  }

  async function confirmMeal(meal: PlannedMeal) {
    setSaving(true);
    const planId = getActivePlanId();
    if (!planId) {
      setSaving(false);
      return;
    }
    const response = await api.confirmPlannedMeal({
      user_id: DEMO_USER_ID,
      plan_id: planId,
      date: appToday,
      meal_id: meal.meal_id
    });
    setSaving(false);

    if (response.error) {
      setNotice(response.error.message);
      return;
    }

    setNotice(`${meal.name} ${t("status.saved")}`);
    await loadToday();
  }

  async function saveCheckin() {
    setSaving(true);
    const payload: Omit<DailyCheckin, "checkin_id" | "created_at" | "updated_at"> = {
      user_id: DEMO_USER_ID,
      date: appToday,
      weight_kg: checkin.weight_kg ? Number(checkin.weight_kg) : undefined,
      sleep_hours: checkin.sleep_hours ? Number(checkin.sleep_hours) : undefined,
      fatigue_level: Number(checkin.fatigue_level) as DailyCheckin["fatigue_level"],
      soreness_level: Number(checkin.soreness_level) as DailyCheckin["soreness_level"],
      notes: checkin.notes
    };
    const response = await api.saveDailyCheckin(payload);
    setSaving(false);

    if (response.error) {
      setNotice(response.error.message);
      return;
    }

    setNotice(t("status.saved"));
    await loadToday();
  }

  if (!today || !summary) {
    return <PageLoadState message={notice || t("status.loading")} />;
  }

  return (
    <div className="today-page stitch-dashboard">
      <header className="today-header today-hero-panel">
        <div className="today-hero-copy">
          <p>{coachCopy.eyebrow}</p>
          <h1>{headline}</h1>
          <span>{intro}</span>
          <div className="hero-action-row">
            <button onClick={() => onNavigate?.("/workout")} type="button">
              {coachCopy.start}
            </button>
            <button className="ghost" onClick={() => onNavigate?.("/advice")} type="button">
              {coachCopy.review}
            </button>
          </div>
        </div>
        <div className="readiness-lens" aria-label={isChinese ? "今日准备度" : "Today readiness"}>
          <div className="lens-orbit">
            <span />
            <strong>{recoveryLabel}</strong>
            <small>{coachCopy.recovery}</small>
          </div>
          <div className="lens-stats">
            <span>
              <b>{summary.weekly_workouts_completed}/{summary.weekly_workouts_planned}</b>
              {coachCopy.workouts}
            </span>
            <span>
              <b>{summary.calories_logged}/{summary.calories_target}</b>
              {coachCopy.calories}
            </span>
            <span>
              <b>{summary.protein_logged_g}g</b>
              {coachCopy.protein}
            </span>
          </div>
        </div>
      </header>

      {notice ? <div className="business-notice">{notice}</div> : null}

      {planNeedsRenewal ? (
        <section className="business-panel compact plan-renewal-panel">
          <h2>{isChinese ? "当前计划没有覆盖今天" : "Your current plan does not cover today"}</h2>
          <p>{isChinese ? "生成新的计划草稿并确认后，今日训练和饮食内容会在这里显示。" : "Generate and accept a new plan draft to populate today's workout and meals."}</p>
          <button onClick={() => onNavigate?.("/plan")} type="button">{isChinese ? "生成新计划" : "Generate a new plan"}</button>
        </section>
      ) : null}

      <section className="metric-grid compact-metrics" aria-label={t("today.summary")}>
        <MetricCard label={t("metrics.goal")} value={goalLabel} />
        <MetricCard
          label={t("metrics.workouts")}
          value={`${summary.weekly_workouts_completed}/${summary.weekly_workouts_planned}`}
          detail={t("today.weeklyProgress")}
        />
        <MetricCard label={t("metrics.weightTrend")} value={`${summary.weight_7_day_delta_kg}kg`} detail={t("metrics.days7")} />
        <MetricCard label={t("metrics.recovery")} value={recoveryLabel} />
      </section>

      <section className="today-layout">
        <div className="today-content-stack">
        <div className="today-primary-grid">
        <article className="business-card primary-card workout-summary-card">
          <div className="section-heading">
            <span>{t("today.workout")}</span>
            <strong>{workout?.duration_minutes ?? 0} {t("metrics.durationMinutes")}</strong>
          </div>
          {workout ? (
            <>
              <h2>{workout.name}</h2>
              <p>{focusLabel}</p>
              <div className="exercise-list">
                {workout.exercises.map((exercise) => (
                  <div className="exercise-row" key={exercise.exercise_id}>
                    <div>
                      <strong>{exercise.name}</strong>
                      <span>{exercise.target_muscles.join(", ")}</span>
                    </div>
                    <span>
                      {isChinese ? `${exercise.sets} 组 × ${exercise.reps} 次` : `${exercise.sets} x ${exercise.reps}`}
                    </span>
                  </div>
                ))}
              </div>
              <div className="button-row">
                <button onClick={() => onNavigate?.("/workout")} type="button">
                  {isChinese ? "记录训练" : "Log workout"}
                </button>
              </div>
            </>
          ) : (
            <p>{t("empty.noWorkout")}</p>
          )}
        </article>

        <article className="business-card nutrition-card">
          <div className="section-heading">
            <span>{t("today.diet")}</span>
            <strong>{mealTotal.calories} {t("metrics.kcalPlanned")}</strong>
          </div>
          <ProgressBar label={t("metrics.calories")} value={summary.calories_logged} max={summary.calories_target} />
          <ProgressBar label={t("metrics.protein")} value={summary.protein_logged_g} max={summary.protein_target_g} suffix="g" />
          <div className="meal-list">
            {meals.map((meal) => (
              <div className="meal-row" key={meal.meal_id}>
                <div>
                  <strong>{meal.name}</strong>
                  <span>
                    {meal.total_macros.calories} {t("metrics.kcal")} · {meal.total_macros.protein_g}{t("metrics.proteinGrams")}
                  </span>
                </div>
                <button disabled={saving} onClick={() => void confirmMeal(meal)}>
                  {t("actions.confirm")}
                </button>
              </div>
            ))}
          </div>
        </article>
        </div>

        <article className="business-card checkin-card">
          <div className="section-heading">
            <span>{t("today.checkin")}</span>
            <strong>{today.daily_checkin ? t("status.saved") : ""}</strong>
          </div>
          <div className="checkin-grid">
            <label>
              {t("form.weightKg")}
              <input
                value={checkin.weight_kg}
                onChange={(event) => setCheckin((value) => ({ ...value, weight_kg: event.target.value }))}
                placeholder="75.6"
                type="number"
              />
            </label>
            <label>
              {t("form.sleepHours")}
              <input
                value={checkin.sleep_hours}
                onChange={(event) => setCheckin((value) => ({ ...value, sleep_hours: event.target.value }))}
                placeholder="7.5"
                type="number"
              />
            </label>
            <label>
              {t("form.fatigue")}
              <input
                max="5"
                min="1"
                value={checkin.fatigue_level}
                onChange={(event) => setCheckin((value) => ({ ...value, fatigue_level: event.target.value }))}
                type="range"
              />
            </label>
            <label>
              {t("form.soreness")}
              <input
                max="5"
                min="1"
                value={checkin.soreness_level}
                onChange={(event) => setCheckin((value) => ({ ...value, soreness_level: event.target.value }))}
                type="range"
              />
            </label>
          </div>
          <textarea
            value={checkin.notes}
            onChange={(event) => setCheckin((value) => ({ ...value, notes: event.target.value }))}
            placeholder={t("form.notes")}
          />
          <button disabled={saving} onClick={() => void saveCheckin()}>
            {saving ? t("status.saving") : t("actions.save")}
          </button>
        </article>
        </div>

        <aside className="business-card advice-card agent-insight-panel">
          <div className="section-heading">
            <span>{coachCopy.insight}</span>
            <strong>{riskLabel}</strong>
          </div>
          {today.latest_advice ? (
            <>
              <h2>{today.latest_advice.title}</h2>
              <p>{today.latest_advice.content}</p>
              <small>{today.latest_advice.reason}</small>
              <div className="button-row">
                <button onClick={() => setNotice(t("status.reasonVisible"))} type="button">{t("actions.viewReason")}</button>
                <button
                  className="ghost"
                  onClick={() => {
                    setNotice(t("status.adjustmentOpened"));
                    onNavigate?.("/agent");
                  }}
                  type="button"
                >
                  {t("actions.adjustToday")}
                </button>
              </div>
            </>
          ) : (
            <p>{t("empty.noAdvice")}</p>
          )}
        </aside>
      </section>
    </div>
  );
}
