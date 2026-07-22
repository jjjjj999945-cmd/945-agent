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
  async function loadPlan() { const r = await api.getCurrentPlan(DEMO_USER_ID); if (r.error) setNotice(r.error.message); else setActivePlan(r.data); }
  async function generate() { setSaving(true); const r = await api.generatePlan({ user_id: DEMO_USER_ID }); setSaving(false); if (r.error) return setNotice(r.error.message); setDraft(r.data); setNotice(t("status.planGenerated")); }
  async function accept() { if (!draft) return; setSaving(true); const r = await api.acceptPlan({ user_id: DEMO_USER_ID, plan_id: draft.plan_id }); setSaving(false); if (r.error) return setNotice(r.error.message); setActivePlan(r.data); setDraft(null); setNotice(t("status.saved")); }
  const plan = draft ?? activePlan;
  if (!plan) return <PageLoadState message={notice || t("status.loading")} />;
  return <div className="business-page"><header className="page-header"><p>945</p><h1>{t("page.plan.title")}</h1><span>{t("page.plan.description")}</span></header>{notice ? <div className="business-notice">{notice}</div> : null}<section className="page-grid"><article className="business-panel"><div className="section-heading"><span>{t("labels.userGoal")}</span><strong>{plan.goal.replace(/_/g, " ")}</strong></div><p>{plan.status === "draft" ? "Draft" : "Active"}</p><p>{plan.meal_plan.daily_targets.calories} {t("metrics.kcal")} · {plan.meal_plan.daily_targets.protein_g}{t("metrics.proteinGrams")}</p></article><article className="business-panel"><h2>{locale === "zh-CN" ? "训练周计划" : "Workout week"}</h2>{plan.workout_plan.days.map((day) => <div className="exercise-row" key={day.date}><div><strong>{day.date} · {day.name}</strong><span>{day.exercises.map((exercise) => exercise.name).join(" / ")}</span></div><span>{day.duration_minutes} {t("metrics.durationMinutes")}</span></div>)}</article><article className="business-panel"><h2>{t("labels.mealPlanPreview")}</h2>{plan.meal_plan.days.map((day) => <div className="meal-row" key={day.date}><div><strong>{day.date}</strong><span>{day.meals.map((meal) => `${meal.name}: ${meal.foods.map((food) => `${food.name} ${food.portion}`).join(", ")}`).join(" · ")}</span></div><span>{day.meals.reduce((sum, meal) => sum + meal.total_macros.calories, 0)} {t("metrics.kcal")}</span></div>)}<div className="button-row"><button disabled={saving} onClick={() => void generate()} type="button">{t("actions.generate")}</button>{draft ? <button disabled={saving} onClick={() => void accept()} type="button">{t("actions.accept")}</button> : null}<button className="ghost" onClick={() => onNavigate("/agent")} type="button">{t("actions.askAgent")}</button></div></article></section></div>;
}
