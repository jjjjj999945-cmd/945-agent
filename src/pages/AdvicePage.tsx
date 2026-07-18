import { useEffect, useState } from "react";
import { PageLoadState } from "../components/business/PageLoadState";
import { DEMO_USER_ID } from "../data/demoData";
import { createTranslator } from "../i18n";
import { api } from "../services/apiClient";
import type { AdvicePageData, AgentAdvice, Locale } from "../types/domain";

export function AdvicePage({ locale }: { locale: Locale }) {
  const t = createTranslator(locale);
  const isChinese = locale === "zh-CN";
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

  if (!data) return <PageLoadState message={notice || t("status.loading")} />;
  const cards = [data.daily, data.weekly, ...data.adjustments].filter(Boolean) as AgentAdvice[];
  const primaryAdvice = data.weekly ?? data.daily ?? cards[0];
  const adviceTypeLabels: Record<AgentAdvice["type"], string> = {
    daily_advice: isChinese ? "今日建议" : "Daily Advice",
    weekly_summary: isChinese ? "周总结" : "Weekly Summary",
    plan_adjustment: isChinese ? "计划调整" : "Plan Adjustment",
    safety_warning: isChinese ? "安全提醒" : "Safety Warning"
  };

  return (
    <div className="business-page advice-analysis-page">
      <header className="page-header">
        <p>945</p>
        <h1>{isChinese ? "智能调整分析" : "AI Adjustment Analysis"}</h1>
        <span>{t("page.advice.description")}</span>
      </header>
      {notice ? <div className="business-notice">{notice}</div> : null}

      <section className="advice-analysis-layout">
        <div className="advice-main-stack">
          <article className="business-panel analysis-reason-card">
            <div className="section-heading">
              <span>{isChinese ? "为什么建议这次调整" : "Why we suggest this change"}</span>
              <strong>{isChinese ? "置信度 94%" : "Confidence 94%"}</strong>
            </div>
            <h2>{primaryAdvice.title}</h2>
            <p>{primaryAdvice.content}</p>
            <small>{primaryAdvice.reason}</small>
            <div className="analysis-metrics">
              <span><b>{isChinese ? "心率变异性趋势" : "HRV Trend"}</b>{isChinese ? "下降 15%" : "-15% drop"}</span>
              <span><b>{isChinese ? "睡眠评分" : "Sleep Score"}</b>64/100</span>
              <span><b>{isChinese ? "训练负荷" : "Training Load"}</b>{isChinese ? "峰值日" : "Peak day"}</span>
            </div>
          </article>
          <article className="business-panel plan-comparison-card">
            <div className="section-heading">
              <span>{isChinese ? "计划对比" : "Plan Comparison"}</span>
              <strong>{isChinese ? "45 分钟高强度" : "45 min high intensity"}</strong>
            </div>
            <div className="comparison-row muted">
              <span>{isChinese ? "原计划" : "Original Plan"}</span>
              <strong>{isChinese ? "HIIT 阈值间歇" : "HIIT Threshold Intervals"}</strong>
            </div>
            <div className="comparison-row selected">
              <span>{isChinese ? "建议计划" : "Suggested Plan"}</span>
              <strong>{isChinese ? "主动恢复瑜伽 · 30 分钟" : "Active Recovery Yoga · 30 min"}</strong>
            </div>
          </article>
        </div>

        <aside className="advice-side-stack">
          <article className="business-panel compact update-schedule-card">
            <div className="update-icon"><span className="material-symbols-outlined">published_with_changes</span></div>
            <h2>{isChinese ? "更新日程？" : "Update Schedule?"}</h2>
            <p>{isChinese ? "立即把这次调整应用到你的训练日历。" : "Apply this adjustment to your calendar immediately."}</p>
            <div className="button-row">
              <button onClick={() => void updateAdvice(primaryAdvice, "accepted")} type="button">{isChinese ? "接受调整" : "Accept Adjustment"}</button>
              <button className="ghost" onClick={() => void updateAdvice(primaryAdvice, "dismissed")} type="button">{isChinese ? "保留原计划" : "Keep Original Plan"}</button>
            </div>
          </article>
          <article className="business-panel compact">
            <h2>{isChinese ? "来源指标" : "Source Metrics"}</h2>
            <div className="source-row"><span>{isChinese ? "静息心率" : "Resting HR"}</span><strong>62 bpm ↑</strong></div>
            <div className="source-row"><span>{isChinese ? "深睡眠" : "Deep Sleep"}</span><strong>{isChinese ? "1小时12分 ↓" : "1h 12m ↓"}</strong></div>
            <div className="source-row"><span>{isChinese ? "肌肉准备度" : "Muscle Readiness"}</span><strong>42%</strong></div>
          </article>
          <article className="business-panel compact">
            <h2>{t("page.advice.title")}</h2>
            {cards.map((advice) => (
              <div className="compact-advice-row" key={advice.advice_id}>
                <span>{adviceTypeLabels[advice.type]}</span>
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
