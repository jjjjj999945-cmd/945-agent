import { useEffect, useState } from "react";
import { ConfirmDialog } from "../components/business/ConfirmDialog";
import { DEMO_USER_ID } from "../data/demoData";
import { appToday } from "../services/dateContext";
import { usePlanContext } from "../contexts/PlanContext";
import { createTranslator } from "../i18n";
import { api } from "../services/apiClient";
import { saveRecordDraft } from "../services/recordDraft";
import type { AgentMessage, Locale, RecordDraft, TodayResponseData } from "../types/domain";

export function AgentPage({ locale, pendingDraft, onDraftHandled }: { locale: Locale; pendingDraft?: RecordDraft | null; onDraftHandled?: () => void }) {
  const t = createTranslator(locale);
  const { currentPlan } = usePlanContext();
  const isChinese = locale === "zh-CN";
  const roleLabels: Record<AgentMessage["role"], string> = {
    agent: isChinese ? "智能教练" : "Agent",
    user: isChinese ? "你" : "You"
  };
  const [messages, setMessages] = useState<AgentMessage[]>([]);
  const [today, setToday] = useState<TodayResponseData | null>(null);
  const [input, setInput] = useState("");
  const [draft, setDraft] = useState<RecordDraft | null>(null);
  const [notice, setNotice] = useState("");
  const [savingDraft, setSavingDraft] = useState(false);

  useEffect(() => {
    void loadMessages();
    void loadTodayContext();
  }, []);

  useEffect(() => {
    if (pendingDraft) setDraft(pendingDraft);
  }, [pendingDraft]);

  async function loadMessages() {
    const response = await api.getAgentMessages(DEMO_USER_ID);
    if (!response.error) setMessages(response.data);
  }

  async function loadTodayContext() {
    const response = await api.getToday({ user_id: DEMO_USER_ID, date: appToday });
    if (!response.error) setToday(response.data);
  }

  async function send() {
    if (!input.trim()) return;
    const response = await api.sendAgentMessage({
      user_id: DEMO_USER_ID,
      locale,
      message: input,
      context: { current_page: "agent", date: appToday }
    });
    if (response.error) {
      setNotice(response.error.message);
      return;
    }
    setDraft(response.data.record_draft ?? null);
    setInput("");
    await loadMessages();
    await loadTodayContext();
  }

  async function confirmDraft() {
    if (!draft || savingDraft) return;
    setSavingDraft(true);
    const response = await saveRecordDraft(draft, {
      user_id: DEMO_USER_ID,
      date: appToday,
      plan_id: currentPlan?.plan_id
    });
    setSavingDraft(false);
    if (response.error) {
      setNotice(response.error.message);
      return;
    }
    setDraft(null);
    onDraftHandled?.();
    setNotice(t("status.agentDraftConfirmed"));
    await loadTodayContext();
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
      ["调整类型", payload.adjustment_type],
      ["目标日期", payload.target_date],
      ["替换名称", payload.replacement_name],
      ["备注", payload.effort_note ?? payload.note ?? payload.reason]
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
            <strong>{isChinese ? "945 智能教练" : "945 Agent"}</strong>
            <span>{today?.latest_advice?.content ?? (isChinese ? "我会根据你的计划、记录和每日打卡生成可确认的建议。" : "I use your plan, records, and daily check-ins to produce confirmation-required suggestions.")}</span>
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
          <small>{isChinese ? "上下文：当前计划、训练记录、饮食记录、每日打卡与建议。" : "Context: active plan, workout records, meal records, check-ins, and advice."}</small>
        </article>
        <article className="business-panel plan-draft-card">
          <div className="section-heading"><span>{isChinese ? "今日训练" : "Today's workout"}</span><strong>{today?.today_workout ? `${today.today_workout.duration_minutes} ${t("metrics.durationMinutes")}` : "-"}</strong></div>
          <h2>{today?.today_workout?.name ?? (isChinese ? "今天没有训练安排" : "No workout scheduled")}</h2>
          {today?.today_workout?.exercises.map((exercise) => <div className="exercise-row" key={exercise.exercise_id}><span>{exercise.name}</span><strong>{exercise.sets} × {exercise.reps}</strong></div>)}
        </article>
        <article className="business-panel compact">
          <h2>{isChinese ? "今日执行状态" : "Today status"}</h2>
          <div className="exercise-row"><span>{isChinese ? "蛋白质" : "Protein"}</span><strong>{today ? `${today.status_summary.protein_logged_g}/${today.status_summary.protein_target_g}g` : "-"}</strong></div>
          <div className="exercise-row"><span>{isChinese ? "热量" : "Calories"}</span><strong>{today ? `${today.status_summary.calories_logged}/${today.status_summary.calories_target}` : "-"}</strong></div>
          <small>{today?.status_summary.recovery_status === "fatigued" ? (isChinese ? "恢复状态：疲劳，建议优先恢复。" : "Recovery status: fatigued. Prioritize recovery.") : (isChinese ? "恢复状态正常。" : "Recovery status: normal.")}</small>
        </article>
      </aside>
      </section>

      <ConfirmDialog
        cancelLabel={t("actions.cancel")}
        confirmDisabled={savingDraft}
        confirmLabel={t("actions.confirm")}
        onCancel={() => { setDraft(null); onDraftHandled?.(); }}
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
