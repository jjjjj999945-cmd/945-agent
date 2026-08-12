import { useEffect, useState } from "react";
import { PageLoadState } from "../components/business/PageLoadState";
import { DEMO_USER_ID, TODAY_DATE } from "../data/demoData";
import { createTranslator } from "../i18n";
import { api } from "../services/apiClient";
import type { BodyPageData, Locale } from "../types/domain";

export function BodyPage({ locale }: { locale: Locale }) {
  const t = createTranslator(locale);
  const isChinese = locale === "zh-CN";
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
    setNotice(t("status.bodyMetricSaved"));
    await loadBody();
  }

  if (!data) return <PageLoadState message={notice || t("status.loading")} />;

  return (
    <div className="business-page">
      <header className="page-header">
        <p>945</p>
        <h1>{t("page.body.title")}</h1>
        <span>{t("page.body.description")}</span>
      </header>
      {notice ? <div className="business-notice">{notice}</div> : null}

      <section className="metric-grid">
        <div className="metric-card"><span>{t("labels.currentWeight")}</span><strong>{data.latest_metric.weight_kg}kg</strong></div>
        <div className="metric-card"><span>{isChinese ? "身体质量指数" : "BMI"}</span><strong>{data.latest_metric.bmi ?? "--"}</strong></div>
        <div className="metric-card"><span>{t("labels.trend7")}</span><strong>{data.trend_7_day_kg.toFixed(1)}kg</strong></div>
        <div className="metric-card"><span>{t("labels.currentGoal")}</span><strong>{isChinese ? "身体重组" : data.profile.goal.replace(/_/g, " ")}</strong></div>
      </section>

      <section className="page-grid">
        <article className="business-panel compact">
          <label>
            {t("form.weightKg")}
            <input type="number" value={weight} onChange={(event) => setWeight(event.target.value)} />
          </label>
          <button onClick={() => void saveWeight()} type="button">{t("actions.saveBodyMetric")}</button>
        </article>
        <article className="business-panel">
          <div className="section-heading">
            <span>{t("labels.metricHistory")}</span>
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
