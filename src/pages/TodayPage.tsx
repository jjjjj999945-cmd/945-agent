import { useEffect, useMemo, useState } from "react";
import { ConfirmDialog } from "../components/business/ConfirmDialog";
import { MetricCard } from "../components/business/MetricCard";
import { ProgressBar } from "../components/business/ProgressBar";
import { demoPlan, DEMO_USER_ID, TODAY_DATE } from "../data/demoData";
import { createTranslator } from "../i18n";
import { api } from "../services/mockApi";
import type { DailyCheckin, Locale, PlannedMeal, RecordDraft, TodayResponseData } from "../types/domain";

type TodayPageProps = {
  locale: Locale;
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

export function TodayPage({ locale }: TodayPageProps) {
  const t = createTranslator(locale);
  const [today, setToday] = useState<TodayResponseData | null>(null);
  const [checkin, setCheckin] = useState<CheckinForm>(initialCheckinForm);
  const [agentMessage, setAgentMessage] = useState("");
  const [agentReply, setAgentReply] = useState("");
  const [recordDraft, setRecordDraft] = useState<RecordDraft | null>(null);
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState("");

  useEffect(() => {
    void loadToday();
  }, []);

  async function loadToday() {
    const response = await api.getToday({ user_id: DEMO_USER_ID, date: TODAY_DATE });
    if (response.error) {
      setNotice(response.error.message);
      return;
    }
    setToday(response.data);
  }

  const workout = today?.today_workout;
  const meals = today?.today_meals ?? [];
  const summary = today?.status_summary;

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

  async function confirmMeal(meal: PlannedMeal) {
    setSaving(true);
    const response = await api.confirmPlannedMeal({
      user_id: DEMO_USER_ID,
      plan_id: demoPlan.plan_id,
      date: TODAY_DATE,
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
      date: TODAY_DATE,
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

  async function sendAgentMessage() {
    if (!agentMessage.trim()) return;

    const response = await api.sendAgentMessage({
      user_id: DEMO_USER_ID,
      locale,
      message: agentMessage,
      context: {
        current_page: "today",
        date: TODAY_DATE
      }
    });

    if (response.error) {
      setNotice(response.error.message);
      return;
    }

    setAgentReply(response.data.content);
    setRecordDraft(response.data.record_draft ?? null);
    setAgentMessage("");
  }

  function confirmRecordDraft() {
    if (!recordDraft) return;
    setNotice(`${recordDraft.type} ${t("status.saved")}`);
    setRecordDraft(null);
  }

  if (!today || !summary) {
    return <div className="business-placeholder">{t("status.loading")}</div>;
  }

  return (
    <div className="today-page">
      <header className="today-header">
        <div>
          <p>945</p>
          <h1>{t("today.title")}</h1>
          <span>{t("today.subtitle")}</span>
        </div>
        <a className="prototype-link" href="/">
          Stitch prototype
        </a>
      </header>

      {notice ? <div className="business-notice">{notice}</div> : null}

      <section className="metric-grid" aria-label={t("today.summary")}>
        <MetricCard label={t("metrics.goal")} value={today.user.goal.replace(/_/g, " ")} />
        <MetricCard
          label={t("metrics.workouts")}
          value={`${summary.weekly_workouts_completed}/${summary.weekly_workouts_planned}`}
          detail={t("today.weeklyProgress")}
        />
        <MetricCard label={t("metrics.weightTrend")} value={`${summary.weight_7_day_delta_kg}kg`} detail="7 days" />
        <MetricCard label={t("metrics.recovery")} value={summary.recovery_status} />
      </section>

      <section className="today-layout">
        <article className="business-card primary-card">
          <div className="section-heading">
            <span>{t("today.workout")}</span>
            <strong>{workout?.duration_minutes ?? 0} min</strong>
          </div>
          {workout ? (
            <>
              <h2>{workout.name}</h2>
              <p>{workout.focus.replace(/_/g, " ")}</p>
              <div className="exercise-list">
                {workout.exercises.map((exercise) => (
                  <div className="exercise-row" key={exercise.exercise_id}>
                    <div>
                      <strong>{exercise.name}</strong>
                      <span>{exercise.target_muscles.join(", ")}</span>
                    </div>
                    <span>
                      {exercise.sets} x {exercise.reps}
                    </span>
                  </div>
                ))}
              </div>
              <div className="button-row">
                <button>{t("actions.complete")}</button>
                <button className="ghost">{t("actions.partial")}</button>
                <button className="ghost">{t("actions.skip")}</button>
              </div>
            </>
          ) : (
            <p>{t("empty.noWorkout")}</p>
          )}
        </article>

        <article className="business-card">
          <div className="section-heading">
            <span>{t("today.diet")}</span>
            <strong>{mealTotal.calories} kcal planned</strong>
          </div>
          <ProgressBar label={t("metrics.calories")} value={summary.calories_logged} max={summary.calories_target} />
          <ProgressBar label={t("metrics.protein")} value={summary.protein_logged_g} max={summary.protein_target_g} suffix="g" />
          <div className="meal-list">
            {meals.map((meal) => (
              <div className="meal-row" key={meal.meal_id}>
                <div>
                  <strong>{meal.name}</strong>
                  <span>
                    {meal.total_macros.calories} kcal · {meal.total_macros.protein_g}g protein
                  </span>
                </div>
                <button disabled={saving} onClick={() => void confirmMeal(meal)}>
                  {t("actions.confirm")}
                </button>
              </div>
            ))}
          </div>
        </article>

        <article className="business-card">
          <div className="section-heading">
            <span>{t("today.checkin")}</span>
            <strong>{today.daily_checkin ? t("status.saved") : ""}</strong>
          </div>
          <div className="checkin-grid">
            <label>
              Weight kg
              <input
                value={checkin.weight_kg}
                onChange={(event) => setCheckin((value) => ({ ...value, weight_kg: event.target.value }))}
                placeholder="75.6"
                type="number"
              />
            </label>
            <label>
              Sleep h
              <input
                value={checkin.sleep_hours}
                onChange={(event) => setCheckin((value) => ({ ...value, sleep_hours: event.target.value }))}
                placeholder="7.5"
                type="number"
              />
            </label>
            <label>
              Fatigue
              <input
                max="5"
                min="1"
                value={checkin.fatigue_level}
                onChange={(event) => setCheckin((value) => ({ ...value, fatigue_level: event.target.value }))}
                type="range"
              />
            </label>
            <label>
              Soreness
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
            placeholder="Notes"
          />
          <button disabled={saving} onClick={() => void saveCheckin()}>
            {saving ? t("status.saving") : t("actions.save")}
          </button>
        </article>

        <article className="business-card advice-card">
          <div className="section-heading">
            <span>{t("today.advice")}</span>
            <strong>{today.latest_advice?.risk_level}</strong>
          </div>
          {today.latest_advice ? (
            <>
              <h2>{today.latest_advice.title}</h2>
              <p>{today.latest_advice.content}</p>
              <small>{today.latest_advice.reason}</small>
              <div className="button-row">
                <button>{t("actions.viewReason")}</button>
                <button className="ghost">{t("actions.adjustToday")}</button>
              </div>
            </>
          ) : (
            <p>{t("empty.noAdvice")}</p>
          )}
        </article>

        <article className="business-card agent-card">
          <div className="section-heading">
            <span>{t("nav.agent")}</span>
            <strong>{t("safety.nonMedical")}</strong>
          </div>
          <p>Ask about today's plan or type a workout or meal note.</p>
          {agentReply ? <div className="agent-reply">{agentReply}</div> : null}
          <div className="agent-input-row">
            <input
              value={agentMessage}
              onChange={(event) => setAgentMessage(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") void sendAgentMessage();
              }}
              placeholder="今天深蹲做了 4 组，每组 8 次，80kg，感觉很累。"
            />
            <button onClick={() => void sendAgentMessage()}>{t("actions.send")}</button>
          </div>
        </article>
      </section>

      <ConfirmDialog
        cancelLabel={t("actions.cancel")}
        confirmLabel={t("actions.confirm")}
        onCancel={() => setRecordDraft(null)}
        onConfirm={confirmRecordDraft}
        open={Boolean(recordDraft)}
        title="Confirm Agent Draft"
      >
        <p>Agent prepared a structured record draft. Confirm before saving.</p>
        <pre>{JSON.stringify(recordDraft?.payload ?? {}, null, 2)}</pre>
      </ConfirmDialog>
    </div>
  );
}
