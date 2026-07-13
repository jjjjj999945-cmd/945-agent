import { demoPlan, demoProfile } from "../data/demoData";
import { createTranslator } from "../i18n";
import type { Locale } from "../types/domain";

export function PlanPage({ locale, onNavigate }: { locale: Locale; onNavigate: (path: string) => void }) {
  const t = createTranslator(locale);
  const firstWorkout = demoPlan.workout_plan.days[0];
  const firstMealDay = demoPlan.meal_plan.days[0];

  return (
    <div className="business-page">
      <header className="page-header">
        <p>945</p>
        <h1>{t("page.plan.title")}</h1>
        <span>{t("page.plan.description")}</span>
      </header>
      <section className="page-grid">
        <article className="business-panel">
          <div className="section-heading">
            <span>用户目标</span>
            <strong>{demoProfile.goal.replace(/_/g, " ")}</strong>
          </div>
          <p>训练经验：{demoProfile.experience_level}</p>
          <p>训练频率：每周 {demoProfile.training_days_per_week} 天</p>
          <p>饮食偏好：{demoProfile.dietary_preferences.join(", ")}</p>
        </article>
        <article className="business-panel">
          <h2>{firstWorkout.name}</h2>
          <p>{firstWorkout.duration_minutes} min · {firstWorkout.focus.replace(/_/g, " ")}</p>
          <p>{firstWorkout.exercises.map((exercise) => exercise.name).join(" / ")}</p>
        </article>
        <article className="business-panel">
          <h2>饮食计划预览</h2>
          <p>{demoPlan.meal_plan.daily_targets.calories} kcal · {demoPlan.meal_plan.daily_targets.protein_g}g protein</p>
          <p>{firstMealDay.meals.map((meal) => meal.name).join(" / ")}</p>
          <div className="button-row">
            <button type="button">生成计划</button>
            <button onClick={() => onNavigate("/")} type="button">接受计划</button>
            <button className="ghost" onClick={() => onNavigate("/agent")} type="button">询问 Agent</button>
          </div>
        </article>
      </section>
    </div>
  );
}
