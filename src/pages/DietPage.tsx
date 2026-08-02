import { useEffect, useRef, useState } from "react";
import { PageLoadState } from "../components/business/PageLoadState";
import { DEMO_USER_ID } from "../data/demoData";
import { appToday } from "../services/dateContext";
import { usePlanContext } from "../contexts/PlanContext";
import { createTranslator } from "../i18n";
import { api } from "../services/apiClient";
import type { DietPageData, Locale } from "../types/domain";

export function DietPage({ locale }: { locale: Locale }) {
  const t = createTranslator(locale);
  const { currentPlan } = usePlanContext();
  const isChinese = locale === "zh-CN";
  const [data, setData] = useState<DietPageData | null>(null);
  const [notice, setNotice] = useState("");
  const [manualMeal, setManualMeal] = useState("鸡胸肉沙拉");
  const [selectedDate, setSelectedDate] = useState("");
  const [showAdjustmentDetails, setShowAdjustmentDetails] = useState(false);
  const manualMealInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    void loadDiet();
  }, []);

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
      setNotice("Current plan does not cover today.");
      return;
    }
    const response = await api.confirmPlannedMeal({
      user_id: DEMO_USER_ID,
      plan_id: currentPlan.plan_id,
      date: selectedDate || appToday,
      meal_id: mealId
    });
    if (response.error) {
      setNotice(response.error.message);
      return;
    }
    setNotice(t("status.plannedMealConfirmed"));
    await loadDiet();
  }

  async function saveManualMeal() {
    const response = await api.saveManualMeal({
      user_id: DEMO_USER_ID,
      plan_id: currentPlan?.plan_id,
      date: appToday,
      meal_name: manualMeal,
      foods: [{ name: manualMeal, portion: "1 serving", calories: 420, protein_g: 38, carbs_g: 24, fat_g: 14 }],
      notes: "Manual MVP entry"
    });
    if (response.error) {
      setNotice(response.error.message);
      return;
    }
    setNotice(t("status.manualMealSaved"));
    await loadDiet();
  }

  if (!data) return <PageLoadState message={notice || t("status.loading")} />;
  const selectedDay = data.plan.meal_plan.days.find((day) => day.date === selectedDate) ?? data.selected_day;

  return (
    <div className="business-page diet-tracker-page">
      <header className="page-header">
        <p>945</p>
        <h1>{t("page.diet.title")}</h1>
        <span>{t("page.diet.description")}</span>
      </header>
      {notice ? <div className="business-notice">{notice}</div> : null}

      <section className="diet-layout">
        <div className="diet-main-stack">
        <article className="business-panel calendar-strip">
          {data.plan.meal_plan.days.map((day) => (
            <button aria-pressed={day.date === selectedDay.date} className={day.date === selectedDay.date ? "active" : ""} key={day.date} onClick={() => setSelectedDate(day.date)} type="button">{day.date}</button>
          ))}
        </article>

        <article className="business-panel nutrition-day-card">
          <div className="section-heading">
            <span>{t("labels.todayNutritionTarget")}</span>
            <strong>{isChinese ? "目标" : "Target"}: {data.targets.calories} {t("metrics.kcal")}</strong>
          </div>
          <div className="macro-rings">
            <span><b>{data.targets.protein_g}</b>{isChinese ? "蛋白" : "PRO"}</span>
            <span><b>{data.targets.carbs_g}</b>{isChinese ? "碳水" : "CARB"}</span>
            <span><b>{data.targets.fat_g}</b>{isChinese ? "脂肪" : "FAT"}</span>
          </div>
        </article>

        <article className="business-panel">
          <div className="section-heading">
            <span>{t("labels.plannedMeals")}</span>
            <strong>{selectedDay.meals.length}</strong>
          </div>
          {selectedDay.meals.map((meal) => (
            <div className="meal-row" key={meal.meal_id}>
              <div>
                <strong>{meal.name}</strong>
                <span>{meal.total_macros.calories} {t("metrics.kcal")} · {meal.total_macros.protein_g}{t("metrics.proteinGrams")}</span>
              </div>
              <button onClick={() => void confirmMeal(meal.meal_id)} type="button">{t("actions.confirmPlannedMeal")}</button>
            </div>
          ))}
          <button className="ghost add-meal-button" onClick={() => manualMealInputRef.current?.focus()} type="button">{isChinese ? "+ 添加餐食" : "+ Add Meal"}</button>
        </article>

        <article className="business-panel compact">
          <label>
            {t("labels.manualMealName")}
            <input ref={manualMealInputRef} value={manualMeal} onChange={(event) => setManualMeal(event.target.value)} />
          </label>
          <button onClick={() => void saveManualMeal()} type="button">{t("actions.saveManualMeal")}</button>
        </article>
        </div>

        <aside className="business-panel diet-side-panel">
          <div className="section-heading">
            <span>{isChinese ? "智能饮食调整" : "AI Meal Adjustment"}</span>
            <strong>{isChinese ? "新的" : "New"}</strong>
          </div>
          <p>{isChinese ? "我注意到你昨天完成了一次高强度腿部训练，所以今天午餐和晚餐的碳水摄入略微上调。" : "I noticed you completed an intense leg session yesterday. I've slightly increased your carbohydrate intake for lunch and dinner today."}</p>
          <div className="button-row">
            <button className="ghost" onClick={() => setNotice(isChinese ? "已忽略本次饮食调整建议。" : "Nutrition adjustment dismissed.")} type="button">{isChinese ? "忽略" : "Dismiss"}</button>
            <button aria-expanded={showAdjustmentDetails} onClick={() => setShowAdjustmentDetails((visible) => !visible)} type="button">{isChinese ? "查看详情" : "Review Details"}</button>
          </div>
          {showAdjustmentDetails ? <div className="diet-adjustment-details">{isChinese ? "碳水安排：午餐和晚餐各上调一份主食。" : "Carbohydrate plan: add one serving of staple carbs to lunch and dinner."}</div> : null}
          <h2>{isChinese ? "采购清单" : "Grocery List"}</h2>
          {(isChinese ? ["鸡胸肉 1.5kg", "红薯 4 个", "希腊酸奶 1L", "原味杏仁"] : ["Chicken Breast (1.5kg)", "Sweet Potatoes (4 large)", "Greek Yogurt (0% Fat, 1L)", "Almonds (Raw, Unsweetened)"]).map((item, index) => (
            <label className="check-row" key={item}>
              <input defaultChecked={index === 3} type="checkbox" />
              {item}
            </label>
          ))}
        </aside>
      </section>
    </div>
  );
}
