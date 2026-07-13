import { useEffect, useState } from "react";
import { DEMO_USER_ID, TODAY_DATE } from "../data/demoData";
import { createTranslator } from "../i18n";
import { api } from "../services/mockApi";
import type { BodyPageData, Locale } from "../types/domain";

export function BodyPage({ locale }: { locale: Locale }) {
  const t = createTranslator(locale);
  const [data, setData] = useState<BodyPageData | null>(null);
  const [weight, setWeight] = useState("75.2");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    void loadBody();
  }, []);

  async function loadBody() {
    const response = await api.getBodyMetrics(DEMO_USER_ID);
    if (response.error) {
      setNotice(response.error.message);
      return;
    }
    setData(response.data);
  }

  async function saveWeight() {
    const response = await api.saveBodyMetric({
      user_id: DEMO_USER_ID,
      date: TODAY_DATE,
      weight_kg: Number(weight),
      bmi: 24.6
    });
    if (response.error) {
      setNotice(response.error.message);
      return;
    }
    setNotice("身体数据已保存");
    await loadBody();
  }

  if (!data) return <div className="business-placeholder">{t("status.loading")}</div>;

  return (
    <div className="business-page">
      <header className="page-header">
        <p>945</p>
        <h1>{t("page.body.title")}</h1>
        <span>{t("page.body.description")}</span>
      </header>
      {notice ? <div className="business-notice">{notice}</div> : null}

      <section className="metric-grid">
        <div className="metric-card"><span>当前体重</span><strong>{data.latest_metric.weight_kg}kg</strong></div>
        <div className="metric-card"><span>BMI</span><strong>{data.latest_metric.bmi ?? "--"}</strong></div>
        <div className="metric-card"><span>7 天趋势</span><strong>{data.trend_7_day_kg.toFixed(1)}kg</strong></div>
        <div className="metric-card"><span>当前目标</span><strong>{data.profile.goal.replace(/_/g, " ")}</strong></div>
      </section>

      <section className="page-grid">
        <article className="business-panel compact">
          <label>
            今日体重 kg
            <input type="number" value={weight} onChange={(event) => setWeight(event.target.value)} />
          </label>
          <button onClick={() => void saveWeight()} type="button">保存身体数据</button>
        </article>
        <article className="business-panel">
          <div className="section-heading">
            <span>记录历史</span>
            <strong>{data.metrics.length}</strong>
          </div>
          {data.metrics.map((metric) => (
            <div className="exercise-row" key={metric.metric_id}>
              <strong>{metric.date}</strong>
              <span>{metric.weight_kg}kg</span>
            </div>
          ))}
        </article>
      </section>
    </div>
  );
}
