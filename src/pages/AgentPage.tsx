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
    setNotice("Agent 草稿已确认");
  }

  return (
    <div className="business-page">
      <header className="page-header">
        <p>945</p>
        <h1>{t("page.agent.title")}</h1>
        <span>{t("page.agent.description")}</span>
      </header>
      {notice ? <div className="business-notice">{notice}</div> : null}

      <section className="business-panel">
        <div className="agent-thread">
          {messages.length ? messages.map((message) => (
            <div className={`agent-bubble ${message.role}`} key={message.message_id}>
              <strong>{message.role}</strong>
              <span>{message.content}</span>
            </div>
          )) : <p>{t("agent.todayPrompt")}</p>}
        </div>
        <div className="agent-input-row">
          <input
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="告诉 Agent 你今天完成了什么"
          />
          <button onClick={() => void send()} type="button">发送</button>
        </div>
      </section>

      <ConfirmDialog
        cancelLabel={t("actions.cancel")}
        confirmLabel={t("actions.confirm")}
        onCancel={() => setDraft(null)}
        onConfirm={confirmDraft}
        open={Boolean(draft)}
        title="确认 Agent 草稿"
      >
        <p>{t("agent.confirmDraftBody")}</p>
        <pre>{JSON.stringify(draft?.payload ?? {}, null, 2)}</pre>
      </ConfirmDialog>
    </div>
  );
}
