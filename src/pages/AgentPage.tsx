import { useEffect, useState, type ReactNode } from "react";
import { ConfirmDialog } from "../components/business/ConfirmDialog";
import { OnboardingPage } from "./OnboardingPage";
import { DEMO_USER_ID } from "../data/demoData";
import { appToday } from "../services/dateContext";
import { usePlanContext } from "../contexts/PlanContext";
import { createTranslator } from "../i18n";
import { api } from "../services/apiClient";
import { saveRecordDraft } from "../services/recordDraft";
import type { AgentMessage, AgentRun, Locale, RecordDraft, TodayResponseData } from "../types/domain";

function renderInlineMessageText(text: string) {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, index) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={index}>{part.slice(2, -2)}</strong>;
    }
    return part;
  });
}

function renderMessageContent(content: string) {
  const lines = content.split("\n");
  const blocks: ReactNode[] = [];
  let listItems: string[] = [];

  const flushList = () => {
    if (!listItems.length) return;
    blocks.push(<ul key={`list-${blocks.length}`}>{listItems.map((item, index) => <li key={index}>{renderInlineMessageText(item)}</li>)}</ul>);
    listItems = [];
  };

  for (const line of lines) {
    const listMatch = line.match(/^\s*[-*]\s+(.+)$/);
    if (listMatch) {
      listItems.push(listMatch[1]);
      continue;
    }
    flushList();
    if (line.trim()) blocks.push(<p key={`paragraph-${blocks.length}`}>{renderInlineMessageText(line)}</p>);
  }
  flushList();
  return blocks;
}

export function AgentPage({ locale, pendingDraft, onDraftHandled }: { locale: Locale; pendingDraft?: RecordDraft | null; onDraftHandled?: () => void }) {
  const t = createTranslator(locale);
  const { coverageStatus, currentPlan, isLoading, profile, refreshPlanState } = usePlanContext();
  const isChinese = locale === "zh-CN";
  const needsPlan = !isLoading && (!profile || coverageStatus !== "active_today");
  const planEntryCopy = profile
    ? (coverageStatus === "expired"
      ? (isChinese ? "上一份计划已经结束。创建并启用新计划后，945 会按你的最新目标继续安排训练与饮食。" : "Your previous plan has ended. Create and activate a new plan so 945 can continue arranging your training and nutrition.")
      : (isChinese ? "创建并启用计划后，945 才能根据你的目标安排训练、饮食与每日建议。" : "Create and activate a plan so 945 can arrange training, nutrition, and daily advice around your goal."))
    : (isChinese ? "先完善基础资料，945 才能为你生成合适的训练与饮食计划。" : "Complete your basic profile first so 945 can generate an appropriate training and nutrition plan.");
  const [messages, setMessages] = useState<AgentMessage[]>([]);
  const [latestRun, setLatestRun] = useState<AgentRun | null>(null);
  const [today, setToday] = useState<TodayResponseData | null>(null);
  const [input, setInput] = useState("");
  const [draft, setDraft] = useState<RecordDraft | null>(null);
  const [notice, setNotice] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [isRetrying, setIsRetrying] = useState(false);
  const [savingDraft, setSavingDraft] = useState(false);
  const [showProfileSetup, setShowProfileSetup] = useState(false);

  useEffect(() => {
    void loadMessages();
    void loadTodayContext();
    void loadLatestRun();
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

  async function loadLatestRun() {
    const response = await api.getAgentRuns(DEMO_USER_ID);
    if (!response.error) setLatestRun(response.data[0] ?? null);
  }

  async function send() {
    if (!input.trim() || isSending) return;
    setNotice("");
    setIsSending(true);
    try {
      const response = await api.sendAgentMessage({
        user_id: DEMO_USER_ID,
        locale,
        message: input,
        context: { current_page: "agent", date: appToday }
      });
      if (response.error) {
        setNotice(response.error.message);
        await loadLatestRun();
        return;
      }
      setDraft(response.data.record_draft ?? null);
      setInput("");
      await loadMessages();
      setMessages((current) => current.some((message) => message.message_id === response.data.message_id) ? current : [...current, response.data]);
      await loadTodayContext();
      await loadLatestRun();
    } finally {
      setIsSending(false);
    }
  }

  async function retryLatestRun() {
    if (!latestRun || latestRun.status !== "failed" || isRetrying) return;
    setNotice("");
    setIsRetrying(true);
    try {
      const response = await api.retryAgentRun({
        user_id: DEMO_USER_ID,
        agent_run_id: latestRun.agent_run_id
      });
      if (response.error) {
        setNotice(response.error.message);
        return;
      }
      setDraft(response.data.record_draft ?? null);
      await loadMessages();
      await loadTodayContext();
      await loadLatestRun();
    } finally {
      setIsRetrying(false);
    }
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
    if (draft.type === "plan_adjustment") await refreshPlanState();
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
      {needsPlan ? (
        <section className="business-panel compact">
          <div className="section-heading"><span>{isChinese ? "计划状态" : "Plan status"}</span><strong>{isChinese ? "等待创建" : "Setup required"}</strong></div>
          <h2>{isChinese ? "当前没有可执行的训练与饮食计划" : "No active training and nutrition plan"}</h2>
          <p>{planEntryCopy}</p>
          <div className="button-row"><button onClick={() => setShowProfileSetup(true)} type="button">{isChinese ? "开始创建计划" : "Create a plan"}</button></div>
        </section>
      ) : null}
      {needsPlan && showProfileSetup ? <OnboardingPage embedded locale={locale} onNavigate={() => setShowProfileSetup(false)} /> : null}

      <section className="agent-chat-layout">
      <article className="business-panel chat-window">
        <div className="agent-thread">
          {messages.map((message) => (
            <div className={`agent-message ${message.role}`} key={message.message_id}>
              <div className="agent-message-content">{renderMessageContent(message.content)}</div>
            </div>
          ))}
        </div>
        <div className="agent-input-row">
          <input
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder={t("agent.inputPlaceholder")}
          />
          <button disabled={isSending} onClick={() => void send()} type="button">{t("actions.send")}</button>
        </div>
      </article>
      <aside className="agent-status-panel">
        <article aria-live="polite" className="business-panel compact" role="status">
          <div className="section-heading"><span>{isChinese ? "教练状态" : "Agent Status"}</span><strong>{isSending ? (isChinese ? "分析中" : "Analyzing") : (isChinese ? "在线" : "Active")}</strong></div>
          <small>{isSending ? (isChinese ? "正在读取当前上下文并生成建议" : "Reading your current context and preparing a suggestion.") : (isChinese ? "上下文：当前计划、训练记录、饮食记录、每日打卡与建议。" : "Context: active plan, workout records, meal records, check-ins, and advice.")}</small>
        </article>
        <article aria-live="polite" className="business-panel compact" role="status">
          <div className="section-heading">
            <span>{isChinese ? "本次请求" : "Latest request"}</span>
            <strong>
              {isSending || isRetrying
                ? (isChinese ? "分析中" : "Analyzing")
                : latestRun?.status === "failed"
                  ? (isChinese ? "需要重试" : "Needs retry")
                  : latestRun?.status === "completed"
                    ? (isChinese ? "已完成" : "Completed")
                    : (isChinese ? "等待请求" : "Waiting")}
            </strong>
          </div>
          {isSending || isRetrying ? <small>{isChinese ? "正在读取当前上下文并生成建议" : "Reading your context and preparing a suggestion."}</small> : null}
          {!isSending && !isRetrying && latestRun?.status === "failed" ? <small>{isChinese ? `上次请求未完成${latestRun.error_code ? `：${latestRun.error_code}` : ""}` : `The last request did not finish${latestRun.error_code ? `: ${latestRun.error_code}` : ""}.`}</small> : null}
          {!isSending && !isRetrying && latestRun?.status === "completed" ? <small>{isChinese ? "本次请求已完成" : "This request completed."}</small> : null}
          {!isSending && !isRetrying && !latestRun ? <small>{isChinese ? "发送消息后，945 会在这里反馈处理结果。" : "945 will show the request result here after you send a message."}</small> : null}
          {latestRun?.status === "failed" ? (
            <div className="button-row">
              <button disabled={isRetrying} onClick={() => void retryLatestRun()} type="button">
                {isRetrying ? (isChinese ? "重试中" : "Retrying") : (isChinese ? "重试此请求" : "Retry request")}
              </button>
            </div>
          ) : null}
        </article>
        <article className="business-panel plan-draft-card">
          <div className="section-heading"><span>{isChinese ? "今日训练" : "Today's workout"}</span><strong>{today?.today_workout ? `${today.today_workout.duration_minutes} ${t("metrics.durationMinutes")}` : "-"}</strong></div>
          <h2>{today?.today_workout?.name ?? (isChinese ? "今天没有训练安排" : "No workout scheduled")}</h2>
          {today?.today_workout?.exercises.map((exercise) => <div className="exercise-row" key={exercise.exercise_id}><span>{exercise.name}</span><strong>{exercise.sets} × {exercise.reps}</strong></div>)}
          {!needsPlan ? <div className="button-row"><button onClick={() => window.location.assign("/today")} type="button">{isChinese ? "查看今日执行" : "Open today's execution"}</button></div> : null}
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
