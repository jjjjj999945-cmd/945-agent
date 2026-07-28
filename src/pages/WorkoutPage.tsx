import { useEffect, useState } from "react";
import { PageLoadState } from "../components/business/PageLoadState";
import { DEMO_USER_ID } from "../data/demoData";
import { appToday } from "../services/dateContext";
import { usePlanContext } from "../contexts/PlanContext";
import { createTranslator } from "../i18n";
import { api } from "../services/apiClient";
import type { Locale, WorkoutPageData } from "../types/domain";

export function WorkoutPage({ locale }: { locale: Locale }) {
  const t = createTranslator(locale);
  const { currentPlan } = usePlanContext();
  const isChinese = locale === "zh-CN";
  const [data, setData] = useState<WorkoutPageData | null>(null);
  const [notice, setNotice] = useState("");
  const [completedSets, setCompletedSets] = useState<Record<string, boolean>>({});
  const dayStatusLabels = isChinese
    ? ["今日", "计划中", "恢复", "力量"]
    : ["Today", "Planned", "Recovery", "Strength"];
  const recentLogs = isChinese
    ? [
        { title: "腿部容量训练", detail: "昨天 · 52 分钟 · RPE 8" },
        { title: "2 区恢复骑行", detail: "周一 · 45 分钟 · 低强度" }
      ]
    : [
        { title: "Lower Body Volume", detail: "Yesterday · 52 min · RPE 8" },
        { title: "Zone 2 Recovery Ride", detail: "Monday · 45 min · Low intensity" }
      ];

  useEffect(() => {
    void loadWorkout();
  }, []);

  async function loadWorkout() {
    const response = await api.getWorkout(DEMO_USER_ID);
    if (response.error) {
      setNotice(response.error.message);
      return;
    }
    setData(response.data);
  }

  async function saveWorkoutLog() {
    const day = data?.selected_day;
    if (!day) return;

    if (!currentPlan) {
      setNotice("当前计划没有覆盖今天。");
      return;
    }

    const response = await api.saveWorkoutLog({
      user_id: DEMO_USER_ID,
      plan_id: currentPlan.plan_id,
      date: appToday,
      status: "completed",
      duration_minutes: day.duration_minutes,
      exercises: day.exercises.map((exercise) => ({
        exercise_id: exercise.exercise_id,
        name: exercise.name,
        sets: Array.from({ length: exercise.sets }, () => ({ reps: Number.parseInt(exercise.reps, 10) || 8, completed: true }))
      })),
      rpe: 7,
      notes: "Saved from PRD workout page skeleton."
    });

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
  const completedCount = Math.round(data.completion_rate * weeklyPlan.length);

  return (
    <div className="business-page workout-detail-page">
      <header className="workout-hero business-panel">
        <div>
          <p>{isChinese ? "桌面客户端训练工作区" : "Desktop training workspace"}</p>
          <h1>{isChinese ? "训练计划中心" : "Training Plan Center"}</h1>
          <span className="status-dot">{isChinese ? `${selectedDay.name} · 训练进行中 · 已开始 15 分钟` : `${selectedDay.name} · Active Session · Started 15m ago`}</span>
        </div>
        <div className="workout-hero-status">
          <span>45:32<br /><small>{isChinese ? "已用时" : "Elapsed"}</small></span>
          <strong>{Math.round(data.completion_rate * 100)}%</strong>
          <button onClick={() => void saveWorkoutLog()} type="button">{isChinese ? "完成训练" : "Finish"}</button>
        </div>
      </header>
      {notice ? <div className="business-notice">{notice}</div> : null}

      <section className="workout-grid">
        <article className="business-panel accent-success">
          <div className="section-heading">
            <span>{selectedDay.exercises[0]?.name}</span>
            <strong>{isChinese ? "已完成" : "Done"}</strong>
          </div>
          <span className="exercise-meta">{isChinese ? "胸部、肱三头肌 · 4 组" : "Chest, Triceps · 4 Sets"}</span>
          <div className="set-table">
            <span>1</span><input defaultValue="60" /><small>kg</small><input defaultValue="10" /><small>{isChinese ? "次" : "reps"}</small><b>✓</b>
            <span>2</span><input defaultValue="70" /><small>kg</small><input defaultValue="8" /><small>{isChinese ? "次" : "reps"}</small><b>✓</b>
          </div>
        </article>

        <article className="business-panel accent-primary">
          <div className="section-heading">
            <span>{selectedDay.exercises[1]?.name}</span>
            <strong>{isChinese ? "进行中" : "Active"}</strong>
          </div>
          <span className="exercise-meta">{isChinese ? "上胸 · 3 组" : "Upper Chest · 3 Sets"}</span>
          <div className="set-table active-set">
            <span>1</span><input defaultValue="30" /><small>kg</small><input defaultValue="10" /><small>{isChinese ? "次" : "reps"}</small><b>✓</b>
            <span>2</span><input defaultValue="32" /><small>kg</small><input defaultValue="8" /><small>{isChinese ? "次" : "reps"}</small><b>✓</b>
            <span>3</span><input placeholder="-" /><small>kg</small><input placeholder="-" /><small>{isChinese ? "次" : "reps"}</small><b />
          </div>
        </article>

        <article className="business-panel pullup-card">
          <div className="section-heading">
            <span>{isChinese ? "引体向上" : "Pull-ups"}</span>
            <strong>{isChinese ? "下一项" : "Up next"}</strong>
          </div>
          <span className="exercise-meta">{isChinese ? "背部、肱二头肌 · 3 组" : "Back, Biceps · 3 Sets"}</span>
          <button className="ghost start-exercise" onClick={() => setCompletedSets((value) => ({ ...value, pullups: !value.pullups }))} type="button">
            {isChinese ? "开始动作" : "Start Exercise"}
          </button>
        </article>
      </section>

      <section className="workout-center-grid">
        <article className="business-panel workout-plan-card">
          <div className="section-heading">
            <h2>{isChinese ? "本周训练计划" : "Weekly Training Plan"}</h2>
            <strong>{completedCount}/{weeklyPlan.length}</strong>
          </div>
          <div className="weekly-plan-list">
            {weeklyPlan.map((day, index) => (
              <div className={day.date === selectedDay.date ? "weekly-plan-row active" : "weekly-plan-row"} key={day.date}>
                <div>
                  <span>{dayStatusLabels[index] ?? (isChinese ? "计划中" : "Planned")}</span>
                  <strong>{day.name}</strong>
                </div>
                <small>{day.duration_minutes} {t("metrics.durationMinutes")} · {day.exercises.length} {isChinese ? "个动作" : "exercises"}</small>
              </div>
            ))}
          </div>
        </article>

        <article className="business-panel workout-history-card">
          <div className="section-heading">
            <h2>{isChinese ? "最近训练记录" : "Recent Workout Logs"}</h2>
            <strong>{isChinese ? "已同步" : "Synced"}</strong>
          </div>
          <div className="history-list">
            {recentLogs.map((log) => (
              <div className="history-row" key={log.title}>
                <strong>{log.title}</strong>
                <span>{log.detail}</span>
              </div>
            ))}
            {data.logs.slice(-2).map((log) => (
              <div className="history-row" key={log.workout_log_id}>
                <strong>{selectedDay.name}</strong>
                <span>{log.date} · {log.duration_minutes ?? selectedDay.duration_minutes} {t("metrics.durationMinutes")} · RPE {log.rpe ?? 7}</span>
              </div>
            ))}
          </div>
        </article>

        <article className="business-panel workout-summary-card">
          <h2>{isChinese ? "训练量摘要" : "Training Volume Summary"}</h2>
          <div className="workout-summary-strip">
            <span><b>{Math.round(data.completion_rate * 100)}%</b>{isChinese ? "本周完成率" : "Weekly completion"}</span>
            <span><b>{data.weekly_volume_sets}</b>{isChinese ? "计划组数" : "Planned sets"}</span>
            <span><b>{selectedDay.duration_minutes}</b>{isChinese ? "今日分钟" : "Today minutes"}</span>
          </div>
          <p>{isChinese ? "当前页面同时保留今日训练执行、整周安排和训练历史，方便后续接入真实计划调整。" : "This page keeps today's execution, weekly schedule, and history in one desktop workspace for later real plan adjustments."}</p>
        </article>
      </section>
    </div>
  );
}
