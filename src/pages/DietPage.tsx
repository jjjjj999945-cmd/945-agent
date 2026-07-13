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
    setNotice("计划餐已确认");
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
    setNotice("手动餐食已保存");
    await loadDiet();
  }

  if (!data) return <div className="business-placeholder">{t("status.loading")}</div>;

  return (
    <div className="business-page">
      <header className="page-header">
        <p>945</p>
        <h1>{t("page.diet.title")}</h1>
        <span>{t("page.diet.description")}</span>
      </header>
      {notice ? <div className="business-notice">{notice}</div> : null}

      <section className="page-grid">
        <article className="business-panel">
          <div className="section-heading">
            <span>今日营养目标</span>
            <strong>{data.targets.calories} kcal</strong>
          </div>
          <p>Protein {data.targets.protein_g}g · Carbs {data.targets.carbs_g}g · Fat {data.targets.fat_g}g</p>
          <p>已记录餐食：{data.logs.length}</p>
        </article>

        <article className="business-panel">
          <div className="section-heading">
            <span>计划餐</span>
            <strong>{data.selected_day.meals.length}</strong>
          </div>
          {data.selected_day.meals.map((meal) => (
            <div className="meal-row" key={meal.meal_id}>
              <div>
                <strong>{meal.name}</strong>
                <span>{meal.total_macros.calories} kcal · {meal.total_macros.protein_g}g protein</span>
              </div>
              <button onClick={() => void confirmMeal(meal.meal_id)} type="button">确认计划餐</button>
            </div>
          ))}
        </article>

        <article className="business-panel compact">
          <label>
            手动餐食名称
            <input value={manualMeal} onChange={(event) => setManualMeal(event.target.value)} />
          </label>
          <button onClick={() => void saveManualMeal()} type="button">保存手动餐食</button>
        </article>
      </section>
    </div>
  );
}
