import { useEffect, useState } from "react";
import { PageLoadState } from "../components/business/PageLoadState";
import { DEMO_USER_ID } from "../data/demoData";
import { appToday } from "../services/dateContext";
import { usePlanContext } from "../contexts/PlanContext";
import { createTranslator } from "../i18n";
import { api } from "../services/apiClient";
import type { Locale, WorkoutPageData, WorkoutPlanDay } from "../types/domain";

type SetEntry = { reps: string; weight_kg: string; completed: boolean };

function initialSetEntries(day: WorkoutPlanDay): Record<string, SetEntry> {
  return Object.fromEntries(day.exercises.flatMap((exercise) => Array.from({ length: exercise.sets }, (_, index) => [
    `${exercise.exercise_id}-${index}`,
    { reps: String(Number.parseInt(exercise.reps, 10) || ""), weight_kg: "", completed: false }
  ])));
}

export function WorkoutPage({ locale }: { locale: Locale }) {
  const t = createTranslator(locale);
  const { currentPlan } = usePlanContext();
  const isChinese = locale === "zh-CN";
  const [data, setData] = useState<WorkoutPageData | null>(null);
  const [notice, setNotice] = useState("");
  const [setEntries, setSetEntries] = useState<Record<string, SetEntry>>({});
  const [saving, setSaving] = useState(false);

  useEffect(() => { void loadWorkout(); }, []);

  async function loadWorkout() {
    const response = await api.getWorkout(DEMO_USER_ID);
    if (response.error) {
      setNotice(response.error.message);
      return;
    }
    setData(response.data);
    setSetEntries(initialSetEntries(response.data.selected_day));
  }

  async function saveWorkoutLog() {
    const day = data?.selected_day;
    if (!day || !currentPlan) {
      setNotice(isChinese ? "当前计划没有覆盖今天。" : "The current plan does not cover today.");
      return;
    }

    const entries = day.exercises.flatMap((exercise) => Array.from({ length: exercise.sets }, (_, index) => setEntries[`${exercise.exercise_id}-${index}`]));
    const completedCount = entries.filter((entry) => entry?.completed).length;
    if (completedCount === 0) {
      setNotice(isChinese ? "请至少勾选一组已完成训练后再保存。" : "Mark at least one completed set before saving.");
      return;
    }

    setSaving(true);
    const response = await api.saveWorkoutLog({
      user_id: DEMO_USER_ID,
      plan_id: currentPlan.plan_id,
      date: appToday,
      status: completedCount === entries.length ? "completed" : "partially_completed",
      duration_minutes: day.duration_minutes,
      exercises: day.exercises.map((exercise) => ({
        exercise_id: exercise.exercise_id,
        name: exercise.name,
        sets: Array.from({ length: exercise.sets }, (_, index) => {
          const entry = setEntries[`${exercise.exercise_id}-${index}`];
          return { reps: Number(entry?.reps) || 0, weight_kg: entry?.weight_kg ? Number(entry.weight_kg) : undefined, completed: entry?.completed ?? false };
        })
      }))
    });
    setSaving(false);

    if (response.error) {
      setNotice(response.error.message);
      return;
    }
    setNotice(t("status.workoutSaved"));
    await loadWorkout();
  }

  if (!data) return <PageLoadState message={notice || t("status.loading")} />;
  const selectedDay = data.selected_day;
  const weeklyPlan = data.plan.workout_plan.days;
  const completedDays = Math.round(data.completion_rate * weeklyPlan.length);

  return (
    <div className="business-page workout-detail-page">
      <header className="workout-hero business-panel">
        <div>
          <p>{isChinese ? "桌面客户端训练工作区" : "Desktop training workspace"}</p>
          <h1>{isChinese ? "训练计划中心" : "Training Plan Center"}</h1>
          <span className="status-dot">{isChinese ? `${selectedDay.name} · ${selectedDay.duration_minutes} 分钟 · ${selectedDay.exercises.length} 个动作` : `${selectedDay.name} · ${selectedDay.duration_minutes} min · ${selectedDay.exercises.length} exercises`}</span>
        </div>
        <div className="workout-hero-status">
          <span>{selectedDay.duration_minutes}<br /><small>{isChinese ? "计划分钟" : "Planned min"}</small></span>
          <strong>{Math.round(data.completion_rate * 100)}%</strong>
          <button disabled={saving} onClick={() => void saveWorkoutLog()} type="button">{isChinese ? "保存训练记录" : "Save workout log"}</button>
        </div>
      </header>
      {notice ? <div className="business-notice">{notice}</div> : null}

      <section className="workout-grid">
        {selectedDay.exercises.map((exercise, exerciseIndex) => (
          <article className={exerciseIndex % 2 === 0 ? "business-panel accent-success" : "business-panel accent-primary"} key={exercise.exercise_id}>
            <div className="section-heading"><span>{exercise.name}</span><strong>{exercise.sets} {isChinese ? "组" : "sets"}</strong></div>
            <span className="exercise-meta">{exercise.target_muscles.join("、")} · {exercise.reps} {isChinese ? "次" : "reps"}</span>
            <div className="set-table">
              {Array.from({ length: exercise.sets }, (_, index) => {
                const key = `${exercise.exercise_id}-${index}`;
                const entry = setEntries[key] ?? { reps: "", weight_kg: "", completed: false };
                return <div className="workout-set-row" key={key}>
                  <span>{index + 1}</span>
                  <input aria-label={`${exercise.name} ${isChinese ? `第 ${index + 1} 组重量 kg` : `set ${index + 1} weight kg`}`} inputMode="decimal" min="0" onChange={(event) => setSetEntries((value) => ({ ...value, [key]: { ...entry, weight_kg: event.target.value } }))} placeholder="-" type="number" value={entry.weight_kg} />
                  <small>kg</small>
                  <input aria-label={`${exercise.name} ${isChinese ? `第 ${index + 1} 组次数` : `set ${index + 1} reps`}`} inputMode="numeric" min="0" onChange={(event) => setSetEntries((value) => ({ ...value, [key]: { ...entry, reps: event.target.value } }))} type="number" value={entry.reps} />
                  <small>{isChinese ? "次" : "reps"}</small>
                  <label className="set-complete-toggle"><input aria-label={`${exercise.name} ${isChinese ? `第 ${index + 1} 组已完成` : `set ${index + 1} completed`}`} checked={entry.completed} onChange={(event) => setSetEntries((value) => ({ ...value, [key]: { ...entry, completed: event.target.checked } }))} type="checkbox" /><span>✓</span></label>
                </div>;
              })}
            </div>
          </article>
        ))}
      </section>

      <section className="workout-center-grid">
        <article className="business-panel workout-plan-card">
          <div className="section-heading"><h2>{isChinese ? "本周训练计划" : "Weekly Training Plan"}</h2><strong>{completedDays}/{weeklyPlan.length}</strong></div>
          <div className="weekly-plan-list">
            {weeklyPlan.map((day) => <div className={day.date === selectedDay.date ? "weekly-plan-row active" : "weekly-plan-row"} key={day.date}><div><span>{day.date === selectedDay.date ? (isChinese ? "今日" : "Today") : (isChinese ? "计划中" : "Planned")}</span><strong>{day.name}</strong></div><small>{day.duration_minutes} {t("metrics.durationMinutes")} · {day.exercises.length} {isChinese ? "个动作" : "exercises"}</small></div>)}
          </div>
        </article>
        <article className="business-panel workout-history-card">
          <div className="section-heading"><h2>{isChinese ? "最近训练记录" : "Recent Workout Logs"}</h2><strong>{isChinese ? "已同步" : "Synced"}</strong></div>
          <div className="history-list">
            {data.logs.length === 0 ? <p>{isChinese ? "暂无训练记录。" : "No workout logs yet."}</p> : null}
            {data.logs.slice(-5).reverse().map((log) => <div className="history-row" key={log.workout_log_id}><strong>{log.exercises.map((exercise) => exercise.name).join("、")}</strong><span>{log.date} · {log.duration_minutes ?? 0} {t("metrics.durationMinutes")} · {log.status}</span></div>)}
          </div>
        </article>
        <article className="business-panel workout-summary-card">
          <h2>{isChinese ? "训练量摘要" : "Training Volume Summary"}</h2>
          <div className="workout-summary-strip"><span><b>{Math.round(data.completion_rate * 100)}%</b>{isChinese ? "本周完成率" : "Weekly completion"}</span><span><b>{data.weekly_volume_sets}</b>{isChinese ? "计划组数" : "Planned sets"}</span><span><b>{selectedDay.duration_minutes}</b>{isChinese ? "今日分钟" : "Today minutes"}</span></div>
        </article>
      </section>
    </div>
  );
}
