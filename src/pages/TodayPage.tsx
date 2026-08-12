import { useEffect, useMemo, useState } from "react";
import { ConfirmDialog } from "../components/business/ConfirmDialog";
import { MetricCard } from "../components/business/MetricCard";
import { PageLoadState } from "../components/business/PageLoadState";
import { ProgressBar } from "../components/business/ProgressBar";
import { demoPlan, DEMO_USER_ID, TODAY_DATE } from "../data/demoData";
import { createTranslator } from "../i18n";
import { api } from "../services/apiClient";
import { saveRecordDraft } from "../services/recordDraft";
import type { DailyCheckin, Locale, PlannedMeal, RecordDraft, TodayResponseData } from "../types/domain";

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
  const isChinese = locale === "zh-CN";
  const coachCopy = {
    eyebrow: isChinese ? "945 今日状态" : "945 Readiness",
    headline: isChinese ? "早上好，Alex。" : "Good morning, Alex.",
    intro: isChinese
      ? "今天更适合恢复驱动训练。智能教练建议保留主计划，但降低最后一组强度，并优先补足蛋白质。"
      : "Your body is primed for recovery today. The Agent suggests keeping the plan, lowering the final set, and prioritizing protein.",
    start: isChinese ? "开始今日计划" : "Start today",
    review: isChinese ? "查看调整" : "Review adjustment",
    insight: isChinese ? "智能教练" : "Coach Agent",
    loadDelta: isChinese ? "负荷变化" : "Load delta",
    effort: isChinese ? "目标强度" : "Target effort",
    recoveryWindow: isChinese ? "恢复窗口" : "Recovery window",
    mobility: isChinese ? "灵活性" : "Mobility",
    strength: isChinese ? "上肢力量" : "Upper strength",
    protein: isChinese ? "蛋白质" : "Protein",
    workouts: isChinese ? "训练" : "Workouts",
    calories: isChinese ? "热量" : "Calories",
    recovery: isChinese ? "恢复" : "Recovery",
    ask: isChinese ? "问智能教练：今天训练、饮食或恢复怎么调？" : "Ask Agent about training, diet, or recovery..."
  };
  const goalLabel = isChinese && today?.user.goal === "body_recomposition" ? "身体重组" : (today?.user.goal.replace(/_/g, " ") ?? "");
  const recoveryLabel = isChinese && summary?.recovery_status === "normal" ? "正常" : (summary?.recovery_status ?? "");
  const focusLabel = isChinese && workout?.focus === "chest_back_shoulders" ? "胸部、背部、肩部" : workout?.focus.replace(/_/g, " ");
  const riskLabel = isChinese && today?.latest_advice?.risk_level === "low" ? "低风险" : today?.latest_advice?.risk_level;
  const draftTypeLabels: Record<RecordDraft["type"], string> = {
    workout_log: isChinese ? "训练记录" : "workout log",
    meal_log: isChinese ? "饮食记录" : "meal log",
    daily_checkin: isChinese ? "每日打卡" : "daily check-in",
    plan_adjustment: isChinese ? "计划调整" : "plan adjustment"
  };
  const workoutStatusLabels: Record<"completed" | "partial" | "skipped", string> = {
    completed: isChinese ? "已完成" : "completed",
    partial: isChinese ? "部分完成" : "partial",
    skipped: isChinese ? "已跳过" : "skipped"
  };

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

  async function confirmRecordDraft() {
    if (!recordDraft) return;
    const response = await saveRecordDraft(recordDraft, { user_id: DEMO_USER_ID, date: TODAY_DATE });
    if (response.error) {
      setNotice(response.error.message);
      return;
    }
    setNotice(`${draftTypeLabels[recordDraft.type]} ${t("status.saved")}`);
    setRecordDraft(null);
    await loadToday();
  }

  function updateWorkoutStatus(status: "completed" | "partial" | "skipped") {
    setNotice(`${t("status.workoutStatusUpdated")}: ${workoutStatusLabels[status]}`);
  }

  function formatRecordDraft(draft: RecordDraft | null) {
    if (!draft) return "";
    if (!isChinese) return JSON.stringify(draft.payload, null, 2);
    const payload = draft.payload;
    const rows = [
      ["草稿类型", draftTypeLabels[draft.type]],
      ["动作名称", payload.exercise_name],
      ["组数", payload.sets],
      ["次数", payload.reps],
      ["重量", payload.weight_kg ? `${payload.weight_kg} kg` : undefined],
      ["餐食名称", payload.meal_name],
      ["备注", payload.effort_note ?? payload.note]
    ].filter(([, value]) => value !== undefined && value !== "");
    return rows.map(([label, value]) => `${label}: ${value}`).join("\n");
  }

  if (!today || !summary) {
    return <PageLoadState message={notice || t("status.loading")} />;
  }

  return (
    <div className="today-page stitch-dashboard">
      <header className="today-header today-hero-panel">
        <div className="today-hero-copy">
          <p>{coachCopy.eyebrow}</p>
          <h1>{coachCopy.headline}</h1>
          <span>{coachCopy.intro}</span>
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
                <button onClick={() => updateWorkoutStatus("completed")} type="button">{t("actions.complete")}</button>
                <button className="ghost" onClick={() => updateWorkoutStatus("partial")} type="button">{t("actions.partial")}</button>
                <button className="ghost" onClick={() => updateWorkoutStatus("skipped")} type="button">{t("actions.skip")}</button>
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
              <div className="agent-signal-grid" aria-label={isChinese ? "智能教练上下文信号" : "Agent context signals"}>
                <span>
                  <b>-18%</b>
                  {coachCopy.loadDelta}
                </span>
                <span>
                  <b>{isChinese ? "强度 7" : "RPE 7"}</b>
                  {coachCopy.effort}
                </span>
                <span>
                  <b>{isChinese ? "2 天" : "2 days"}</b>
                  {coachCopy.recoveryWindow}
                </span>
              </div>
              <div className="agent-timeline" aria-label={isChinese ? "今日计划时间线" : "Today plan timeline"}>
                <span style={{ width: "28%" }}>{coachCopy.mobility}</span>
                <span style={{ width: "42%" }}>{coachCopy.strength}</span>
                <span style={{ width: "30%" }}>{coachCopy.protein}</span>
              </div>
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
          <div className="agent-mini-input">
            <input placeholder={coachCopy.ask} aria-label={isChinese ? "询问智能教练" : "Ask Agent"} />
            <button onClick={() => onNavigate?.("/agent")} type="button">
              <span className="material-symbols-outlined">arrow_upward</span>
            </button>
          </div>
        </aside>

        <article className="business-card agent-card">
          <div className="section-heading">
            <span>{t("nav.agent")}</span>
            <strong>{t("safety.nonMedical")}</strong>
          </div>
          <p>{t("agent.todayPrompt")}</p>
          {agentReply ? <div className="agent-reply">{agentReply}</div> : null}
          <div className="agent-input-row">
            <input
              value={agentMessage}
              onChange={(event) => setAgentMessage(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") void sendAgentMessage();
              }}
              placeholder={t("agent.inputPlaceholder")}
            />
            <button onClick={() => void sendAgentMessage()}>{t("actions.send")}</button>
          </div>
        </article>
      </section>

      <ConfirmDialog
        cancelLabel={t("actions.cancel")}
        confirmLabel={t("actions.confirm")}
        onCancel={() => setRecordDraft(null)}
        onConfirm={() => void confirmRecordDraft()}
        open={Boolean(recordDraft)}
        title={t("agent.confirmDraftTitle")}
      >
        <p>{t("agent.confirmDraftBody")}</p>
        <pre>{formatRecordDraft(recordDraft)}</pre>
      </ConfirmDialog>
    </div>
  );
}
