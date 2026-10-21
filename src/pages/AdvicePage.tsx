import { useEffect, useRef, useState } from "react";
import { PageLoadState } from "../components/business/PageLoadState";
import { DEMO_USER_ID } from "../data/demoData";
import { createTranslator } from "../i18n";
import { api } from "../services/apiClient";
import { appToday } from "../services/dateContext";
import type { AdvicePageData, AgentAdvice, Locale, RecordDraft } from "../types/domain";

export function AdvicePage({ locale, onNavigate, onAgentDraft }: { locale: Locale; onNavigate: (path: string) => void; onAgentDraft: (draft: RecordDraft) => void }) {
  const t = createTranslator(locale);
  const isChinese = locale === "zh-CN";
  const [data, setData] = useState<AdvicePageData | null>(null);
  const [notice, setNotice] = useState("");
  const adviceRequestVersion = useRef(0);

  useEffect(() => {
    void loadAdvice();
  }, []);

  async function loadAdvice() {
    const requestVersion = ++adviceRequestVersion.current;
    const response = await api.getAdvice(DEMO_USER_ID);
    if (response.error) {
      setNotice(response.error.message);
      return;
    }
    if (requestVersion === adviceRequestVersion.current) setData(response.data);
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

  async function refreshFeedback() {
    const requestVersion = ++adviceRequestVersion.current;
    const response = await api.generateAdvice({ user_id: DEMO_USER_ID, date: appToday });
    if (response.error) {
      setNotice(response.error.message);
      return;
    }
    if (requestVersion !== adviceRequestVersion.current) return;
    setData({
      daily: response.data.find((item) => item.type === "daily_advice") ?? null,
      weekly: response.data.find((item) => item.type === "weekly_summary") ?? null,
      adjustments: response.data.filter((item) => item.type === "plan_adjustment")
    });
    setNotice(isChinese ? "已根据最新记录生成执行反馈。" : "Execution feedback was generated from the latest records.");
  }

  function createAdjustmentDraft(advice: AgentAdvice) {
    onAgentDraft({
      type: "plan_adjustment",
      requires_confirmation: true,
      payload: { adjustment_type: "reduce_intensity", reason: advice.reason, target_date: appToday }
    });
    onNavigate("/agent");
  }

  if (!data) return <PageLoadState message={notice || t("status.loading")} />;
  const cards = [data.daily, data.weekly, ...data.adjustments].filter(Boolean) as AgentAdvice[];
  const primaryAdvice = data.daily ?? data.weekly ?? cards[0];
  const adjustmentAdvice = cards.find((advice) => advice.type === "plan_adjustment") ?? null;
  const adviceTypeLabels: Record<AgentAdvice["type"], string> = {
    daily_advice: isChinese ? "今日建议" : "Daily Advice",
    weekly_summary: isChinese ? "周总结" : "Weekly Summary",
    plan_adjustment: isChinese ? "计划调整" : "Plan Adjustment",
    safety_warning: isChinese ? "安全提醒" : "Safety Warning"
  };
  const relatedDataLabels: Record<string, string> = {
    workout_logs: isChinese ? "训练记录" : "Workout logs",
    meal_logs: isChinese ? "饮食记录" : "Meal logs",
    daily_checkins: isChinese ? "每日打卡" : "Daily check-ins",
    meal_plan: isChinese ? "饮食计划" : "Meal plan",
    workout_plan: isChinese ? "训练计划" : "Workout plan",
    plans: isChinese ? "当前计划" : "Current plan",
    weekly_workouts_completed: isChinese ? "本周训练完成情况" : "Weekly workout completion",
    fatigue_level: isChinese ? "疲劳记录" : "Fatigue records",
    soreness_level: isChinese ? "酸痛记录" : "Soreness records"
  };

  if (!primaryAdvice) {
    return (
      <div className="business-page advice-analysis-page">
        <header className="page-header">
          <p>945</p>
          <h1>{isChinese ? "智能调整分析" : "AI Adjustment Analysis"}</h1>
          <span>{t("page.advice.description")}</span>
        </header>
        {notice ? <div className="business-notice">{notice}</div> : null}
        <section className="business-panel compact">
          <h2>{isChinese ? "暂时没有建议" : "No advice yet"}</h2>
          <p>{isChinese ? "完成首次打卡或刷新执行反馈后，945 会在这里生成可确认的调整建议。" : "Complete a check-in or refresh execution feedback to generate a confirmation-required adjustment here."}</p>
          <button onClick={() => void refreshFeedback()} type="button">
            {isChinese ? "刷新执行反馈" : "Refresh execution feedback"}
          </button>
        </section>
      </div>
    );
  }

  return (
    <div className="business-page advice-analysis-page">
      <header className="page-header">
        <p>945</p>
        <h1>{isChinese ? "智能调整分析" : "AI Adjustment Analysis"}</h1>
        <span>{t("page.advice.description")}</span>
      </header>
      {notice ? <div className="business-notice">{notice}</div> : null}

      <div className="advice-refresh-row"><button onClick={() => void refreshFeedback()} type="button">{isChinese ? "刷新执行反馈" : "Refresh execution feedback"}</button></div>

      <section className="advice-analysis-layout">
        <div className="advice-main-stack">
          <article className="business-panel analysis-reason-card">
            <div className="section-heading">
              <span>{isChinese ? "为什么建议这次调整" : "Why we suggest this change"}</span>
              <strong>{adviceTypeLabels[primaryAdvice.type]}</strong>
            </div>
            <h2>{primaryAdvice.title}</h2>
            <p>{primaryAdvice.content}</p>
            <small>{primaryAdvice.reason}</small>
            <div className="analysis-metrics">
              {primaryAdvice.related_data.length === 0 ? <span><b>{isChinese ? "参考数据" : "Reference data"}</b>{isChinese ? "当前记录不足" : "Not enough recorded data"}</span> : primaryAdvice.related_data.map((item) => <span key={item}><b>{relatedDataLabels[item] ?? item}</b>{isChinese ? "已纳入本次建议" : "Included in this recommendation"}</span>)}
            </div>
          </article>
          <article className="business-panel plan-comparison-card">
            <div className="section-heading">
              <span>{isChinese ? "建议行动" : "Recommended actions"}</span>
              <strong>{primaryAdvice.risk_level === "high" ? (isChinese ? "高优先级" : "High priority") : primaryAdvice.risk_level === "medium" ? (isChinese ? "需关注" : "Needs attention") : (isChinese ? "可执行" : "Actionable")}</strong>
            </div>
            {primaryAdvice.recommended_actions.length === 0 ? <p>{isChinese ? "当前没有额外行动项。" : "No additional action is needed."}</p> : primaryAdvice.recommended_actions.map((action) => <div className="comparison-row selected" key={action}><strong>{action}</strong></div>)}
          </article>
        </div>

        <aside className="advice-side-stack">
          <article className="business-panel compact update-schedule-card">
            <h2>{adjustmentAdvice ? (isChinese ? "确认计划调整" : "Confirm plan adjustment") : (isChinese ? "处理这条建议" : "Respond to this recommendation")}</h2>
            <p>{adjustmentAdvice ? (isChinese ? "先查看调整草稿，确认后才会更新当前计划。" : "Review the adjustment draft first. Your plan changes only after confirmation.") : (isChinese ? "采纳、暂缓或忽略会保存你对这条建议的反馈。" : "Accept, defer, or dismiss to save your feedback on this recommendation.")}</p>
            <div className="button-row">
              {adjustmentAdvice ? <button onClick={() => createAdjustmentDraft(adjustmentAdvice)} type="button">{isChinese ? "生成调整草稿" : "Create adjustment draft"}</button> : null}
              <button onClick={() => void updateAdvice(primaryAdvice, "accepted")} type="button">{t("actions.acceptAdvice")}</button>
              <button className="ghost" onClick={() => void updateAdvice(primaryAdvice, "dismissed")} type="button">{t("actions.dismiss")}</button>
            </div>
          </article>
          <article className="business-panel compact">
            <h2>{isChinese ? "建议历史" : "Advice history"}</h2>
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
