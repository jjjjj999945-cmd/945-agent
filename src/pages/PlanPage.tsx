import { demoPlan, demoProfile } from "../data/demoData";
import { createTranslator } from "../i18n";
import { useState } from "react";
import type { Locale } from "../types/domain";

export function PlanPage({ locale, onNavigate }: { locale: Locale; onNavigate: (path: string) => void }) {
  const t = createTranslator(locale);
  const [notice, setNotice] = useState("");
  const firstWorkout = demoPlan.workout_plan.days[0];
  const firstMealDay = demoPlan.meal_plan.days[0];

  return (
    <div className="business-page">
      <header className="page-header">
        <p>945</p>
        <h1>{t("page.plan.title")}</h1>
        <span>{t("page.plan.description")}</span>
      </header>
      {notice ? <div className="business-notice">{notice}</div> : null}
      <section className="page-grid">
        <article className="business-panel">
          <div className="section-heading">
            <span>{t("labels.userGoal")}</span>
            <strong>{demoProfile.goal.replace(/_/g, " ")}</strong>
          </div>
          <p>{t("labels.trainingExperience")}: {demoProfile.experience_level}</p>
          <p>{t("labels.trainingFrequency")}: {demoProfile.training_days_per_week} {t("labels.daysPerWeek")}</p>
          <p>{t("labels.dietPreference")}: {demoProfile.dietary_preferences.join(", ")}</p>
        </article>
        <article className="business-panel">
          <h2>{firstWorkout.name}</h2>
          <p>{firstWorkout.duration_minutes} min · {firstWorkout.focus.replace(/_/g, " ")}</p>
          <p>{firstWorkout.exercises.map((exercise) => exercise.name).join(" / ")}</p>
        </article>
        <article className="business-panel">
          <h2>{t("labels.mealPlanPreview")}</h2>
          <p>{demoPlan.meal_plan.daily_targets.calories} kcal · {demoPlan.meal_plan.daily_targets.protein_g}g protein</p>
          <p>{firstMealDay.meals.map((meal) => meal.name).join(" / ")}</p>
          <div className="button-row">
            <button onClick={() => setNotice(t("status.planGenerated"))} type="button">{t("actions.generate")}</button>
            <button onClick={() => onNavigate("/")} type="button">{t("actions.accept")}</button>
            <button className="ghost" onClick={() => onNavigate("/agent")} type="button">{t("actions.askAgent")}</button>
          </div>
        </article>
      </section>
    </div>
  );
}
