import { useEffect, useRef, useState } from "react";
import { PageLoadState } from "../components/business/PageLoadState";
import { DEMO_USER_ID } from "../data/demoData";
import { appToday } from "../services/dateContext";
import { usePlanContext } from "../contexts/PlanContext";
import { createTranslator } from "../i18n";
import { api } from "../services/apiClient";
import type { DietPageData, Locale, MacroTargets } from "../types/domain";

const emptyMacros: Record<keyof MacroTargets, string> = { calories: "", protein_g: "", carbs_g: "", fat_g: "" };

export function DietPage({ locale }: { locale: Locale }) {
  const t = createTranslator(locale);
  const { currentPlan } = usePlanContext();
  const isChinese = locale === "zh-CN";
  const [data, setData] = useState<DietPageData | null>(null);
  const [notice, setNotice] = useState("");
  const [manualMeal, setManualMeal] = useState("");
  const [manualMacros, setManualMacros] = useState(emptyMacros);
  const [selectedDate, setSelectedDate] = useState("");
  const manualMealInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => { void loadDiet(); }, []);

  async function loadDiet() {
    const response = await api.getDiet(DEMO_USER_ID);
    if (response.error) {
      setNotice(response.error.message);
      return;
    }
    setData(response.data);
    setSelectedDate(response.data.selected_day.date);
  }

  async function confirmMeal(mealId: string) {
    if (!currentPlan) {
      setNotice(isChinese ? "当前计划没有覆盖今天。" : "Current plan does not cover today.");
      return;
    }
    const response = await api.confirmPlannedMeal({ user_id: DEMO_USER_ID, plan_id: currentPlan.plan_id, date: selectedDate || appToday, meal_id: mealId });
    if (response.error) {
      setNotice(response.error.message);
      return;
    }
    setNotice(t("status.plannedMealConfirmed"));
    await loadDiet();
  }

  async function saveManualMeal() {
    const macros = Object.fromEntries(Object.entries(manualMacros).map(([key, value]) => [key, Number(value)])) as MacroTargets;
    if (!manualMeal.trim() || Object.values(macros).some((value) => !Number.isFinite(value) || value < 0)) {
      setNotice(isChinese ? "请填写餐食名称和有效的营养数据。" : "Enter a meal name and valid nutrition values.");
      return;
    }
    const response = await api.saveManualMeal({
      user_id: DEMO_USER_ID,
      plan_id: currentPlan?.plan_id,
      date: appToday,
      meal_name: manualMeal.trim(),
      foods: [{ name: manualMeal.trim(), portion: "1 serving", ...macros }]
    });
    if (response.error) {
      setNotice(response.error.message);
      return;
    }
    setNotice(t("status.manualMealSaved"));
    setManualMeal("");
    setManualMacros(emptyMacros);
    await loadDiet();
  }

  if (!data) return <PageLoadState message={notice || t("status.loading")} />;
  const selectedDay = data.plan.meal_plan.days.find((day) => day.date === selectedDate) ?? data.selected_day;
  const macroLabels: Record<keyof MacroTargets, string> = {
    calories: t("metrics.kcal"),
    protein_g: isChinese ? "蛋白质 g" : "Protein g",
    carbs_g: isChinese ? "碳水 g" : "Carbs g",
    fat_g: isChinese ? "脂肪 g" : "Fat g"
  };

  return (
    <div className="business-page diet-tracker-page">
      <header className="page-header"><p>945</p><h1>{t("page.diet.title")}</h1><span>{t("page.diet.description")}</span></header>
      {notice ? <div className="business-notice">{notice}</div> : null}
      <section className="diet-layout">
        <div className="diet-main-stack">
          <article className="business-panel calendar-strip">
            {data.plan.meal_plan.days.map((day) => <button aria-pressed={day.date === selectedDay.date} className={day.date === selectedDay.date ? "active" : ""} key={day.date} onClick={() => setSelectedDate(day.date)} type="button">{day.date}</button>)}
          </article>
          <article className="business-panel nutrition-day-card">
            <div className="section-heading"><span>{t("labels.todayNutritionTarget")}</span><strong>{isChinese ? "目标" : "Target"}: {data.targets.calories} {t("metrics.kcal")}</strong></div>
            <div className="macro-rings"><span><b>{data.targets.protein_g}</b>{isChinese ? "蛋白" : "PRO"}</span><span><b>{data.targets.carbs_g}</b>{isChinese ? "碳水" : "CARB"}</span><span><b>{data.targets.fat_g}</b>{isChinese ? "脂肪" : "FAT"}</span></div>
          </article>
          <article className="business-panel">
            <div className="section-heading"><span>{t("labels.plannedMeals")}</span><strong>{selectedDay.meals.length}</strong></div>
            {selectedDay.meals.map((meal) => <div className="meal-row" key={meal.meal_id}><div><strong>{meal.name}</strong><span>{meal.total_macros.calories} {t("metrics.kcal")} · {meal.total_macros.protein_g}{t("metrics.proteinGrams")}</span></div><button onClick={() => void confirmMeal(meal.meal_id)} type="button">{t("actions.confirmPlannedMeal")}</button></div>)}
            <button className="ghost add-meal-button" onClick={() => manualMealInputRef.current?.focus()} type="button">{isChinese ? "+ 添加餐食" : "+ Add Meal"}</button>
          </article>
          <article className="business-panel compact">
            <label>{t("labels.manualMealName")}<input ref={manualMealInputRef} value={manualMeal} onChange={(event) => setManualMeal(event.target.value)} /></label>
            <div className="manual-macro-grid">
              {(Object.keys(manualMacros) as Array<keyof MacroTargets>).map((key) => <label key={key}>{macroLabels[key]}<input inputMode="decimal" min="0" onChange={(event) => setManualMacros((value) => ({ ...value, [key]: event.target.value }))} type="number" value={manualMacros[key]} /></label>)}
            </div>
            <button disabled={!manualMeal.trim() || Object.values(manualMacros).some((value) => value === "")} onClick={() => void saveManualMeal()} type="button">{t("actions.saveManualMeal")}</button>
          </article>
        </div>
        <aside className="business-panel diet-side-panel">
          <div className="section-heading"><span>{isChinese ? "今日已记录" : "Today's logged meals"}</span><strong>{data.logs.length}</strong></div>
          {data.logs.length === 0 ? <p>{isChinese ? "暂无已记录餐食。" : "No meals logged yet."}</p> : data.logs.map((meal) => <div className="history-row" key={meal.meal_log_id}><strong>{meal.meal_name}</strong><span>{meal.calories} {t("metrics.kcal")} · {meal.protein_g}{t("metrics.proteinGrams")}</span></div>)}
        </aside>
      </section>
    </div>
  );
}
