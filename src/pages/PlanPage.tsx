import { useEffect, useState } from "react";
import { PageLoadState } from "../components/business/PageLoadState";
import { DEMO_USER_ID } from "../data/demoData";
import { createTranslator } from "../i18n";
import { api } from "../services/apiClient";
import type { Locale, Plan } from "../types/domain";

export function PlanPage({ locale, onNavigate }: { locale: Locale; onNavigate: (path: string) => void }) {
  const t = createTranslator(locale);
  const [activePlan, setActivePlan] = useState<Plan | null>(null);
  const [draft, setDraft] = useState<Plan | null>(null);
  const [notice, setNotice] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => { void loadPlan(); }, []);

  async function loadPlan() {
    const response = await api.getCurrentPlan(DEMO_USER_ID);
    if (response.error) setNotice(response.error.message);
    else setActivePlan(response.data);
  }

  async function generate() {
    setSaving(true);
    const response = await api.generatePlan({ user_id: DEMO_USER_ID });
    setSaving(false);
    if (response.error) return setNotice(response.error.message);
    setDraft(response.data);
    setNotice(t("status.planGenerated"));
  }

  async function accept() {
    if (!draft) return;
    setSaving(true);
    const response = await api.acceptPlan({ user_id: DEMO_USER_ID, plan_id: draft.plan_id });
    setSaving(false);
    if (response.error) return setNotice(response.error.message);
    setActivePlan(response.data);
    setDraft(null);
    setNotice(t("status.saved"));
  }

  const plan = draft ?? activePlan;
  if (!plan) return <PageLoadState message={notice || t("status.loading")} />;
  const workout = plan.workout_plan.days[0];
  const meals = plan.meal_plan.days[0];

  return <div className="business-page">
    <header className="page-header"><p>945</p><h1>{t("page.plan.title")}</h1><span>{t("page.plan.description")}</span></header>
    {notice ? <div className="business-notice">{notice}</div> : null}
    <section className="page-grid">
      <article className="business-panel"><div className="section-heading"><span>{t("labels.userGoal")}</span><strong>{plan.goal.replace(/_/g, " ")}</strong></div><p>{plan.status === "draft" ? "Draft" : "Active"}</p></article>
      <article className="business-panel"><h2>{workout.name}</h2><p>{workout.duration_minutes} {t("metrics.durationMinutes")} · {workout.focus.replace(/_/g, " ")}</p><p>{workout.exercises.map((exercise) => exercise.name).join(" / ")}</p></article>
      <article className="business-panel"><h2>{t("labels.mealPlanPreview")}</h2><p>{plan.meal_plan.daily_targets.calories} {t("metrics.kcal")} · {plan.meal_plan.daily_targets.protein_g}{t("metrics.proteinGrams")}</p><p>{meals.meals.map((meal) => meal.name).join(" / ")}</p><div className="button-row"><button disabled={saving} onClick={() => void generate()} type="button">{t("actions.generate")}</button>{draft ? <button disabled={saving} onClick={() => void accept()} type="button">{t("actions.accept")}</button> : null}<button className="ghost" onClick={() => onNavigate("/agent")} type="button">{t("actions.askAgent")}</button></div></article>
    </section>
  </div>;
}
