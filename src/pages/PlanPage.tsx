import { useEffect, useMemo, useState } from "react";
import { PageLoadState } from "../components/business/PageLoadState";
import { DEMO_USER_ID } from "../data/demoData";
import { createTranslator } from "../i18n";
import { api } from "../services/apiClient";
import type { Locale, Plan, RecordDraft } from "../types/domain";

type AdjustmentType = "reduce_intensity" | "increase_intensity" | "skip_workout" | "swap_exercise" | "swap_meal" | "change_schedule";

const adjustmentLabels: Record<Locale, Record<AdjustmentType, string>> = {
  "zh-CN": {
    reduce_intensity: "降低训练强度",
    increase_intensity: "增加训练强度",
    skip_workout: "跳过本次训练",
    swap_exercise: "替换训练动作",
    swap_meal: "替换计划餐食",
    change_schedule: "顺延训练日"
  },
  "en-US": {
    reduce_intensity: "Reduce intensity",
    increase_intensity: "Increase intensity",
    skip_workout: "Skip workout",
    swap_exercise: "Swap exercise",
    swap_meal: "Swap meal",
    change_schedule: "Reschedule workout"
  }
};

export function PlanPage({ locale, onNavigate, onAgentDraft }: { locale: Locale; onNavigate: (path: string) => void; onAgentDraft: (draft: RecordDraft) => void }) {
  const t = createTranslator(locale);
  const isChinese = locale === "zh-CN";
  const [activePlan, setActivePlan] = useState<Plan | null>(null);
  const [draft, setDraft] = useState<Plan | null>(null);
  const [notice, setNotice] = useState("");
  const [saving, setSaving] = useState(false);
  const [adjustmentType, setAdjustmentType] = useState<AdjustmentType>("reduce_intensity");
  const [targetDate, setTargetDate] = useState("");
  const [targetId, setTargetId] = useState("");
  const [replacementName, setReplacementName] = useState("");
  const [reason, setReason] = useState("");

  useEffect(() => { void loadPlan(); }, []);

  async function loadPlan() {
    const response = await api.getCurrentPlan(DEMO_USER_ID);
    if (response.error) setNotice(response.error.message);
    else {
      setActivePlan(response.data);
      setTargetDate(response.data.workout_plan.days[0]?.date ?? response.data.meal_plan.days[0]?.date ?? "");
    }
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
  const targetDay = useMemo(() => plan?.workout_plan.days.find((day) => day.date === targetDate), [plan, targetDate]);
  const mealDay = useMemo(() => plan?.meal_plan.days.find((day) => day.date === targetDate), [plan, targetDate]);
  const adjustsMeal = adjustmentType === "swap_meal";
  const needsReplacement = adjustmentType === "swap_exercise" || adjustmentType === "swap_meal";

  function createAdjustmentDraft() {
    if (!plan || !reason.trim()) {
      setNotice(isChinese ? "请填写调整原因。" : "Add a reason for this adjustment.");
      return;
    }
    if (needsReplacement && !replacementName.trim()) {
      setNotice(isChinese ? "请填写替换内容。" : "Add the replacement name.");
      return;
    }
    const payload: Record<string, unknown> = {
      adjustment_type: adjustmentType,
      reason: reason.trim(),
      target_date: targetDate
    };
    if (adjustmentType === "swap_exercise" && targetId) payload.target_exercise_id = targetId;
    if (adjustsMeal && targetId) payload.target_meal_id = targetId;
    if (needsReplacement) payload.replacement_name = replacementName.trim();
    onAgentDraft({ type: "plan_adjustment", requires_confirmation: true, payload });
    onNavigate("/agent");
  }

  if (!plan) {
    return <div className="business-page">
      <header className="page-header"><p>945</p><h1>{t("page.plan.title")}</h1><span>{t("page.plan.description")}</span></header>
      <section className="business-panel compact"><h2>{isChinese ? "生成你的首个计划" : "Generate your first plan"}</h2>
        <p>{notice || (isChinese ? "根据已填写的资料生成 7 天训练与饮食计划。" : "Create a 7-day workout and nutrition plan from your profile.")}</p>
        <button disabled={saving} onClick={() => void generate()} type="button">{t("actions.generate")}</button>
      </section>
    </div>;
  }

  const dates = Array.from(new Set([...plan.workout_plan.days, ...plan.meal_plan.days].map((day) => day.date))).sort();

  return (
    <div className="business-page">
      <header className="page-header"><p>945</p><h1>{t("page.plan.title")}</h1><span>{t("page.plan.description")}</span></header>
      {notice ? <div className="business-notice">{notice}</div> : null}
      <section className="page-grid">
        <article className="business-panel">
          <div className="section-heading"><span>{t("labels.userGoal")}</span><strong>{plan.goal.replace(/_/g, " ")}</strong></div>
          <p>{plan.status === "draft" ? "Draft" : "Active"}</p>
          <p>{plan.meal_plan.daily_targets.calories} {t("metrics.kcal")} · {plan.meal_plan.daily_targets.protein_g}{t("metrics.proteinGrams")}</p>
        </article>
        <article className="business-panel">
          <h2>{isChinese ? "训练周计划" : "Workout week"}</h2>
          {plan.workout_plan.days.map((day) => <div className="exercise-row" key={day.date}><div><strong>{day.date} · {day.name}</strong><span>{day.exercises.map((exercise) => exercise.name).join(" / ") || (isChinese ? "恢复日" : "Recovery day")}</span></div><span>{day.duration_minutes} {t("metrics.durationMinutes")}</span></div>)}
        </article>
        <article className="business-panel">
          <h2>{t("labels.mealPlanPreview")}</h2>
          {plan.meal_plan.days.map((day) => <div className="meal-row" key={day.date}><div><strong>{day.date}</strong><span>{day.meals.map((meal) => `${meal.name}: ${meal.foods.map((food) => `${food.name} ${food.portion}`).join(", ")}`).join(" · ")}</span></div><span>{day.meals.reduce((sum, meal) => sum + meal.total_macros.calories, 0)} {t("metrics.kcal")}</span></div>)}
          <div className="button-row"><button disabled={saving} onClick={() => void generate()} type="button">{t("actions.generate")}</button>{draft ? <button disabled={saving} onClick={() => void accept()} type="button">{t("actions.accept")}</button> : null}<button className="ghost" onClick={() => onNavigate("/agent")} type="button">{t("actions.askAgent")}</button></div>
        </article>
        <article className="business-panel plan-adjustment-panel">
          <div className="section-heading"><span>{isChinese ? "调整计划" : "Adjust plan"}</span><strong>{isChinese ? "需确认" : "Confirmation required"}</strong></div>
          <div className="plan-adjustment-grid">
            <label>{isChinese ? "调整方式" : "Adjustment"}<select aria-label={isChinese ? "调整方式" : "Adjustment type"} value={adjustmentType} onChange={(event) => { setAdjustmentType(event.target.value as AdjustmentType); setTargetId(""); }}>
              {Object.entries(adjustmentLabels[locale]).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select></label>
            <label>{isChinese ? "计划日期" : "Plan date"}<select aria-label={isChinese ? "计划日期" : "Plan date"} value={targetDate} onChange={(event) => { setTargetDate(event.target.value); setTargetId(""); }}>
              {dates.map((date) => <option key={date} value={date}>{date}</option>)}
            </select></label>
            {adjustmentType === "swap_exercise" ? <label>{isChinese ? "目标动作" : "Target exercise"}<select aria-label={isChinese ? "目标动作" : "Target exercise"} value={targetId} onChange={(event) => setTargetId(event.target.value)}>
              <option value="">{isChinese ? "自动选择第一项" : "Use the first item"}</option>
              {(targetDay?.exercises ?? []).map((item) => <option key={item.exercise_id} value={item.exercise_id}>{item.name}</option>)}
            </select></label> : null}
            {adjustsMeal ? <label>{isChinese ? "目标餐食" : "Target meal"}<select aria-label={isChinese ? "目标餐食" : "Target meal"} value={targetId} onChange={(event) => setTargetId(event.target.value)}>
              <option value="">{isChinese ? "自动选择第一项" : "Use the first item"}</option>
              {(mealDay?.meals ?? []).map((item) => <option key={item.meal_id} value={item.meal_id}>{item.name}</option>)}
            </select></label> : null}
            {needsReplacement ? <label>{isChinese ? "替换内容" : "Replacement"}<input aria-label={isChinese ? "替换内容" : "Replacement"} value={replacementName} onChange={(event) => setReplacementName(event.target.value)} placeholder={adjustsMeal ? (isChinese ? "例如：火鸡藜麦饭碗" : "e.g. Turkey quinoa bowl") : (isChinese ? "例如：地板卧推" : "e.g. Floor press")} /></label> : null}
          </div>
          <label>{isChinese ? "调整原因" : "Reason"}<textarea aria-label={isChinese ? "调整原因" : "Reason"} value={reason} onChange={(event) => setReason(event.target.value)} placeholder={isChinese ? "例如：今天恢复不足，需要降低负荷" : "e.g. Recovery is low today"} /></label>
          <div className="button-row"><button onClick={createAdjustmentDraft} type="button">{isChinese ? "生成调整草稿" : "Create adjustment draft"}</button></div>
        </article>
      </section>
    </div>
  );
}
