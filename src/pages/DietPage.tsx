import { useEffect, useState } from "react";
import { demoPlan, DEMO_USER_ID, TODAY_DATE } from "../data/demoData";
import { createTranslator } from "../i18n";
import { api } from "../services/mockApi";
import type { DietPageData, Locale } from "../types/domain";

export function DietPage({ locale }: { locale: Locale }) {
  const t = createTranslator(locale);
  const [data, setData] = useState<DietPageData | null>(null);
  const [notice, setNotice] = useState("");
  const [manualMeal, setManualMeal] = useState("鸡胸肉沙拉");

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
  }

  async function confirmMeal(mealId: string) {
    const response = await api.confirmPlannedMeal({
      user_id: DEMO_USER_ID,
      plan_id: demoPlan.plan_id,
      date: TODAY_DATE,
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
      date: TODAY_DATE,
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

  if (!data) return <div className="business-placeholder">{t("status.loading")}</div>;

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
          {["Mon 16", "Tue 17", "Wed 18", "Thu 19", "Fri 20", "Sat 21", "Sun 22"].map((day) => (
            <button className={day.includes("Tue") ? "active" : ""} key={day} type="button">{day}</button>
          ))}
        </article>

        <article className="business-panel nutrition-day-card">
          <div className="section-heading">
            <span>{t("labels.todayNutritionTarget")}</span>
            <strong>Target: {data.targets.calories} kcal</strong>
          </div>
          <div className="macro-rings">
            <span><b>110</b>PRO</span>
            <span><b>320</b>CARB</span>
            <span><b>65</b>FAT</span>
          </div>
        </article>

        <article className="business-panel">
          <div className="section-heading">
            <span>{t("labels.plannedMeals")}</span>
            <strong>{data.selected_day.meals.length}</strong>
          </div>
          {data.selected_day.meals.map((meal) => (
            <div className="meal-row" key={meal.meal_id}>
              <div>
                <strong>{meal.name}</strong>
                <span>{meal.total_macros.calories} kcal · {meal.total_macros.protein_g}g protein</span>
              </div>
              <button onClick={() => void confirmMeal(meal.meal_id)} type="button">{t("actions.confirmPlannedMeal")}</button>
            </div>
          ))}
          <button className="ghost add-meal-button" type="button">+ Add Meal</button>
        </article>

        <article className="business-panel compact">
          <label>
            {t("labels.manualMealName")}
            <input value={manualMeal} onChange={(event) => setManualMeal(event.target.value)} />
          </label>
          <button onClick={() => void saveManualMeal()} type="button">{t("actions.saveManualMeal")}</button>
        </article>
        </div>

        <aside className="business-panel diet-side-panel">
          <div className="section-heading">
            <span>AI Meal Adjustment</span>
            <strong>New</strong>
          </div>
          <p>I noticed you completed an intense leg session yesterday. I've slightly increased your carbohydrate intake for lunch and dinner today.</p>
          <div className="button-row">
            <button className="ghost" type="button">Dismiss</button>
            <button type="button">Review Details</button>
          </div>
          <h2>Grocery List</h2>
          {["Chicken Breast (1.5kg)", "Sweet Potatoes (4 large)", "Greek Yogurt (0% Fat, 1L)", "Almonds (Raw, Unsweetened)"].map((item, index) => (
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
