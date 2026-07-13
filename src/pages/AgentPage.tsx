import { useEffect, useState } from "react";
import { ConfirmDialog } from "../components/business/ConfirmDialog";
import { DEMO_USER_ID, TODAY_DATE } from "../data/demoData";
import { createTranslator } from "../i18n";
import { api } from "../services/mockApi";
import type { AgentMessage, Locale, RecordDraft } from "../types/domain";

export function AgentPage({ locale }: { locale: Locale }) {
  const t = createTranslator(locale);
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

  return (
    <div className="business-page agent-chat-page">
      {notice ? <div className="business-notice">{notice}</div> : null}

      <section className="agent-chat-layout">
      <article className="business-panel chat-window">
        <div className="agent-thread">
          <div className="agent-bubble agent">
            <strong>945 Agent · 09:41 AM</strong>
            <span>Good morning. I've reviewed your biometric data from last night's recovery phase. Your HRV is trending slightly lower than baseline.</span>
          </div>
          <div className="agent-bubble user">
            <strong>You · 09:45 AM</strong>
            <span>Feeling a bit sluggish, to be honest. Maybe we should dial back the intensity?</span>
          </div>
          <div className="agent-bubble agent">
            <strong>945 Agent · 09:46 AM</strong>
            <span>Understood. Given the self-reported fatigue and HRV data, I recommend pivoting to a Zone 2 recovery ride.</span>
          </div>
          {messages.map((message) => (
            <div className={`agent-bubble ${message.role}`} key={message.message_id}>
              <strong>{message.role}</strong>
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
          <div className="section-heading"><span>Agent Status</span><strong>Active</strong></div>
          <small>Context: Oura Ring, Whoop, Apple Health</small>
        </article>
        <article className="business-panel plan-draft-card">
          <div className="section-heading"><span>Plan Draft</span><strong>⋮</strong></div>
          <h2>Recovery Ride</h2>
          <p>Zone 2 Focus · 45 min</p>
          <div className="exercise-row"><span>Warm-up</span><strong>10 min @ 100W</strong></div>
          <div className="exercise-row"><span>Main Set</span><strong>30 min @ 140W</strong></div>
          <button onClick={confirmDraft} type="button">Push to Garmin</button>
        </article>
        <article className="business-panel compact">
          <h2>Live Context</h2>
          <div className="context-bar"><span style={{ width: "68%" }} /></div>
          <small>HRV trending low · RPE elevated</small>
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
        <pre>{JSON.stringify(draft?.payload ?? {}, null, 2)}</pre>
      </ConfirmDialog>
    </div>
  );
}
