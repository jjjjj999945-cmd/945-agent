import { useEffect, useState } from "react";
import { ConfirmDialog } from "../components/business/ConfirmDialog";
import { DEMO_USER_ID, TODAY_DATE } from "../data/demoData";
import { createTranslator } from "../i18n";
import { api } from "../services/apiClient";
import type { AgentMessage, Locale, RecordDraft } from "../types/domain";

export function AgentPage({ locale }: { locale: Locale }) {
  const t = createTranslator(locale);
  const isChinese = locale === "zh-CN";
  const roleLabels: Record<AgentMessage["role"], string> = {
    agent: isChinese ? "智能教练" : "Agent",
    user: isChinese ? "你" : "You"
  };
  const [messages, setMessages] = useState<AgentMessage[]>([]);
  const [input, setInput] = useState("");
  const [draft, setDraft] = useState<RecordDraft | null>(null);
  const [notice, setNotice] = useState("");

  useEffect(() => {
    void loadMessages();
  }, []);

  async function loadMessages() {
    const response = await api.getAgentMessages(DEMO_USER_ID);
    if (!response.error) setMessages(response.data);
  }

  async function send() {
    if (!input.trim()) return;
    const response = await api.sendAgentMessage({
      user_id: DEMO_USER_ID,
      locale,
      message: input,
      context: { current_page: "agent", date: TODAY_DATE }
    });
    if (response.error) {
      setNotice(response.error.message);
      return;
    }
    setDraft(response.data.record_draft ?? null);
    setInput("");
    await loadMessages();
  }

  function confirmDraft() {
    setDraft(null);
    setNotice(t("status.agentDraftConfirmed"));
  }

  function formatRecordDraft(recordDraft: RecordDraft | null) {
    if (!recordDraft) return "";
    if (!isChinese) return JSON.stringify(recordDraft.payload, null, 2);
    const typeLabels: Record<RecordDraft["type"], string> = {
      workout_log: "训练记录",
      meal_log: "饮食记录",
      daily_checkin: "每日打卡",
      plan_adjustment: "计划调整"
    };
    const payload = recordDraft.payload;
    const rows = [
      ["草稿类型", typeLabels[recordDraft.type]],
      ["动作名称", payload.exercise_name],
      ["组数", payload.sets],
      ["次数", payload.reps],
      ["重量", payload.weight_kg ? `${payload.weight_kg} kg` : undefined],
      ["餐食名称", payload.meal_name],
      ["备注", payload.effort_note ?? payload.note]
    ].filter(([, value]) => value !== undefined && value !== "");
    return rows.map(([label, value]) => `${label}: ${value}`).join("\n");
  }

  return (
    <div className="business-page agent-chat-page">
      <header className="page-header agent-page-header">
        <p>945</p>
        <h1>{isChinese ? "945 智能教练" : "945 Agent"}</h1>
        <span>{t("page.agent.description")}</span>
      </header>

      {notice ? <div className="business-notice">{notice}</div> : null}

      <section className="agent-chat-layout">
      <article className="business-panel chat-window">
        <div className="agent-thread">
          <div className="agent-bubble agent">
            <strong>{isChinese ? "945 智能教练 · 09:41" : "945 Agent · 09:41 AM"}</strong>
            <span>{isChinese ? "早上好。我已经看过你昨晚恢复阶段的身体数据，心率变异性比基线略低。" : "Good morning. I've reviewed your biometric data from last night's recovery phase. Your HRV is trending slightly lower than baseline."}</span>
          </div>
          <div className="agent-bubble user">
            <strong>{isChinese ? "你 · 09:45" : "You · 09:45 AM"}</strong>
            <span>{isChinese ? "说实话今天有点没劲。是不是该把强度降一点？" : "Feeling a bit sluggish, to be honest. Maybe we should dial back the intensity?"}</span>
          </div>
          <div className="agent-bubble agent">
            <strong>{isChinese ? "945 智能教练 · 09:46" : "945 Agent · 09:46 AM"}</strong>
            <span>{isChinese ? "明白。结合你的疲劳反馈和心率变异性数据，我建议今天改成 2 区恢复骑行。" : "Understood. Given the self-reported fatigue and HRV data, I recommend pivoting to a Zone 2 recovery ride."}</span>
          </div>
          {messages.map((message) => (
            <div className={`agent-bubble ${message.role}`} key={message.message_id}>
              <strong>{roleLabels[message.role]}</strong>
              <span>{message.content}</span>
            </div>
          ))}
        </div>
        <div className="agent-input-row">
          <input
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder={t("agent.inputPlaceholder")}
          />
          <button onClick={() => void send()} type="button">{t("actions.send")}</button>
        </div>
      </article>
      <aside className="agent-status-panel">
        <article className="business-panel compact">
          <div className="section-heading"><span>{isChinese ? "教练状态" : "Agent Status"}</span><strong>{isChinese ? "在线" : "Active"}</strong></div>
          <small>{isChinese ? "上下文：Oura 戒指、Whoop、Apple 健康" : "Context: Oura Ring, Whoop, Apple Health"}</small>
        </article>
        <article className="business-panel plan-draft-card">
          <div className="section-heading"><span>{isChinese ? "计划草稿" : "Plan Draft"}</span><strong>⋮</strong></div>
          <h2>{isChinese ? "恢复骑行" : "Recovery Ride"}</h2>
          <p>{isChinese ? "2 区专注 · 45 分钟" : "Zone 2 Focus · 45 min"}</p>
          <div className="exercise-row"><span>{isChinese ? "热身" : "Warm-up"}</span><strong>{isChinese ? "10 分钟 @ 100W" : "10 min @ 100W"}</strong></div>
          <div className="exercise-row"><span>{isChinese ? "主训练" : "Main Set"}</span><strong>{isChinese ? "30 分钟 @ 140W" : "30 min @ 140W"}</strong></div>
          <button onClick={confirmDraft} type="button">{isChinese ? "同步到 Garmin" : "Push to Garmin"}</button>
        </article>
        <article className="business-panel compact">
          <h2>{isChinese ? "实时状态" : "Live Context"}</h2>
          <div className="context-bar"><span style={{ width: "68%" }} /></div>
          <small>{isChinese ? "心率变异性偏低 · 主观强度偏高" : "HRV trending low · RPE elevated"}</small>
        </article>
      </aside>
      </section>

      <ConfirmDialog
        cancelLabel={t("actions.cancel")}
        confirmLabel={t("actions.confirm")}
        onCancel={() => setDraft(null)}
        onConfirm={confirmDraft}
        open={Boolean(draft)}
        title={t("agent.confirmDraftTitle")}
      >
        <p>{t("agent.confirmDraftBody")}</p>
        <pre>{formatRecordDraft(draft)}</pre>
      </ConfirmDialog>
    </div>
  );
}
