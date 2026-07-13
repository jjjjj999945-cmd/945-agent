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

  return (
    <div className="business-page">
      <header className="page-header">
        <p>945</p>
        <h1>{t("page.advice.title")}</h1>
        <span>{t("page.advice.description")}</span>
      </header>
      {notice ? <div className="business-notice">{notice}</div> : null}

      <section className="page-grid">
        {cards.map((advice) => (
          <article className="business-panel" key={advice.advice_id}>
            <div className="section-heading">
              <span>{advice.type}</span>
              <strong>{advice.risk_level}</strong>
            </div>
            <h2>{advice.title}</h2>
            <p>{advice.content}</p>
            <small>{advice.reason}</small>
            <div className="button-row">
              <button onClick={() => void updateAdvice(advice, "accepted")} type="button">{t("actions.acceptAdvice")}</button>
              <button className="ghost" onClick={() => void updateAdvice(advice, "dismissed")} type="button">{t("actions.dismiss")}</button>
              <button className="ghost" onClick={() => void updateAdvice(advice, "deferred")} type="button">{t("actions.defer")}</button>
            </div>
          </article>
        ))}
      </section>
    </div>
  );
}
