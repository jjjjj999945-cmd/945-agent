import { useEffect, useState } from "react";
import { DEMO_USER_ID } from "../data/demoData";
import { createTranslator } from "../i18n";
import { api } from "../services/mockApi";
import type { AdvicePageData, AgentAdvice, Locale } from "../types/domain";

export function AdvicePage({ locale }: { locale: Locale }) {
  const t = createTranslator(locale);
  const [data, setData] = useState<AdvicePageData | null>(null);
  const [notice, setNotice] = useState("");

  useEffect(() => {
    void loadAdvice();
  }, []);

  async function loadAdvice() {
    const response = await api.getAdvice(DEMO_USER_ID);
    if (response.error) {
      setNotice(response.error.message);
      return;
    }
    setData(response.data);
  }

  async function updateAdvice(advice: AgentAdvice, status: AgentAdvice["accepted_status"]) {
    const response = await api.updateAdviceStatus({
      user_id: DEMO_USER_ID,
      advice_id: advice.advice_id,
      accepted_status: status
    });
    if (response.error) {
      setNotice(response.error.message);
      return;
    }
    setNotice(t("status.adviceUpdated"));
    await loadAdvice();
  }

  if (!data) return <div className="business-placeholder">{t("status.loading")}</div>;
  const cards = [data.daily, data.weekly, ...data.adjustments].filter(Boolean) as AgentAdvice[];
  const primaryAdvice = data.weekly ?? data.daily ?? cards[0];

  return (
    <div className="business-page advice-analysis-page">
      <header className="page-header">
        <p>945</p>
        <h1>AI Adjustment Analysis</h1>
        <span>{t("page.advice.description")}</span>
      </header>
      {notice ? <div className="business-notice">{notice}</div> : null}

      <section className="advice-analysis-layout">
        <div className="advice-main-stack">
          <article className="business-panel analysis-reason-card">
            <div className="section-heading">
              <span>Why we suggest this change</span>
              <strong>Confidence 94%</strong>
            </div>
            <h2>{primaryAdvice.title}</h2>
            <p>{primaryAdvice.content}</p>
            <small>{primaryAdvice.reason}</small>
            <div className="analysis-metrics">
              <span><b>HRV Trend</b>-15% drop</span>
              <span><b>Sleep Score</b>64/100</span>
              <span><b>Training Load</b>Peak day</span>
            </div>
          </article>
          <article className="business-panel plan-comparison-card">
            <div className="section-heading">
              <span>Plan Comparison</span>
              <strong>45 min high intensity</strong>
            </div>
            <div className="comparison-row muted">
              <span>Original Plan</span>
              <strong>HIIT Threshold Intervals</strong>
            </div>
            <div className="comparison-row selected">
              <span>Suggested Plan</span>
              <strong>Active Recovery Yoga · 30 min</strong>
            </div>
          </article>
        </div>

        <aside className="advice-side-stack">
          <article className="business-panel compact update-schedule-card">
            <div className="update-icon"><span className="material-symbols-outlined">published_with_changes</span></div>
            <h2>Update Schedule?</h2>
            <p>Apply this adjustment to your calendar immediately.</p>
            <div className="button-row">
              <button onClick={() => void updateAdvice(primaryAdvice, "accepted")} type="button">Accept Adjustment</button>
              <button className="ghost" onClick={() => void updateAdvice(primaryAdvice, "dismissed")} type="button">Keep Original Plan</button>
            </div>
          </article>
          <article className="business-panel compact">
            <h2>Source Metrics</h2>
            <div className="source-row"><span>Resting HR</span><strong>62 bpm ↑</strong></div>
            <div className="source-row"><span>Deep Sleep</span><strong>1h 12m ↓</strong></div>
            <div className="source-row"><span>Muscle Readiness</span><strong>42%</strong></div>
          </article>
          <article className="business-panel compact">
            <h2>{t("page.advice.title")}</h2>
            {cards.map((advice) => (
              <div className="compact-advice-row" key={advice.advice_id}>
                <span>{advice.type}</span>
                <div className="button-row">
                  <button onClick={() => void updateAdvice(advice, "accepted")} type="button">{t("actions.acceptAdvice")}</button>
                  <button className="ghost" onClick={() => void updateAdvice(advice, "dismissed")} type="button">{t("actions.dismiss")}</button>
                  <button className="ghost" onClick={() => void updateAdvice(advice, "deferred")} type="button">{t("actions.defer")}</button>
                </div>
              </div>
            ))}
          </article>
        </aside>
      </section>
    </div>
  );
}
