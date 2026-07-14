import { useEffect, useState } from "react";
import { demoPlan, DEMO_USER_ID, TODAY_DATE } from "../data/demoData";
import { createTranslator } from "../i18n";
import { api } from "../services/mockApi";
import type { Locale, WorkoutPageData } from "../types/domain";

export function WorkoutPage({ locale }: { locale: Locale }) {
  const t = createTranslator(locale);
  const isChinese = locale === "zh-CN";
  const [data, setData] = useState<WorkoutPageData | null>(null);
  const [notice, setNotice] = useState("");
  const [completedSets, setCompletedSets] = useState<Record<string, boolean>>({});

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

    const response = await api.saveWorkoutLog({
      user_id: DEMO_USER_ID,
      plan_id: demoPlan.plan_id,
      date: TODAY_DATE,
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

  if (!data) return <div className="business-placeholder">{t("status.loading")}</div>;

  return (
    <div className="business-page workout-detail-page">
      <header className="workout-hero business-panel">
        <div>
          <h1>{isChinese ? "上肢力量训练" : "Upper Body Power"}</h1>
          <span className="status-dot">{isChinese ? "训练进行中 · 已开始 15 分钟" : "Active Session · Started 15m ago"}</span>
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
            <span>{data.selected_day.exercises[0]?.name}</span>
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
            <span>{data.selected_day.exercises[1]?.name}</span>
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
    </div>
  );
}
