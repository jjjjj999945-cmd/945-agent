import { useEffect, useState } from "react";
import { demoPlan, DEMO_USER_ID, TODAY_DATE } from "../data/demoData";
import { createTranslator } from "../i18n";
import { api } from "../services/mockApi";
import type { Locale, WorkoutPageData } from "../types/domain";

export function WorkoutPage({ locale }: { locale: Locale }) {
  const t = createTranslator(locale);
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
    <div className="business-page">
      <header className="page-header">
        <p>945</p>
        <h1>{t("page.workout.title")}</h1>
        <span>{t("page.workout.description")}</span>
      </header>
      {notice ? <div className="business-notice">{notice}</div> : null}

      <section className="page-grid">
        <article className="business-panel">
          <div className="section-heading">
            <span>{t("labels.weeklyWorkoutPlan")}</span>
            <strong>{Math.round(data.completion_rate * 100)}%</strong>
          </div>
          {data.plan.workout_plan.days.map((day) => (
            <div className="exercise-row" key={day.date}>
              <div>
                <strong>{day.name}</strong>
                <span>{day.focus.replace(/_/g, " ")} · {day.duration_minutes} min</span>
              </div>
              <span>{day.exercises.length} {t("labels.exercises")}</span>
            </div>
          ))}
        </article>

        <article className="business-panel">
          <div className="section-heading">
            <span>{data.selected_day.name}</span>
            <strong>{data.weekly_volume_sets} {t("labels.sets")}</strong>
          </div>
          <div className="exercise-list">
            {data.selected_day.exercises.map((exercise) => (
              <div className="exercise-row" key={exercise.exercise_id}>
                <div>
                  <strong>{exercise.name}</strong>
                  <span>{exercise.target_muscles.join(", ")}</span>
                </div>
                <button
                  className={completedSets[exercise.exercise_id] ? "" : "ghost"}
                  onClick={() => setCompletedSets((value) => ({ ...value, [exercise.exercise_id]: !value[exercise.exercise_id] }))}
                  type="button"
                >
                  {exercise.sets} x {exercise.reps}
                </button>
              </div>
            ))}
          </div>
          <button onClick={() => void saveWorkoutLog()} type="button">{t("actions.saveWorkoutLog")}</button>
        </article>
      </section>
    </div>
  );
}
