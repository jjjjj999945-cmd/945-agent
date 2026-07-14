import { useEffect, useState } from "react";
import { DEMO_USER_ID } from "../data/demoData";
import { createTranslator } from "../i18n";
import { api } from "../services/mockApi";
import type { Goal, Locale, SettingsData, UnitSystem } from "../types/domain";

export function SettingsPage({ locale, onLocaleChange }: { locale: Locale; onLocaleChange: (locale: Locale) => void }) {
  const t = createTranslator(locale);
  const isChinese = locale === "zh-CN";
  const [data, setData] = useState<SettingsData | null>(null);
  const [notice, setNotice] = useState("");
  const [notificationsEnabled, setNotificationsEnabled] = useState(false);
  const [agentTone, setAgentTone] = useState<"clinical" | "encouraging" | "strict">("encouraging");

  useEffect(() => {
    void loadSettings();
  }, []);

  async function loadSettings() {
    const response = await api.getSettings(DEMO_USER_ID);
    if (response.error) {
      setNotice(response.error.message);
      return;
    }
    setData(response.data);
  }

  async function changeLanguage(nextLocale: Locale) {
    onLocaleChange(nextLocale);
    const response = await api.saveSettings({ user_id: DEMO_USER_ID, language: nextLocale });
    if (!response.error) setData(response.data);
    setNotice(t("status.settingsSaved"));
  }

  async function changeGoal(goal: Goal, label: string) {
    if (!data) return;
    const response = await api.saveSettings({
      user_id: DEMO_USER_ID,
      profile: { ...data.profile, goal }
    });
    if (response.error) {
      setNotice(response.error.message);
      return;
    }
    setData(response.data);
    setNotice(isChinese ? `${t("status.settingsSaved")}：训练目标已切换为${label}` : `${t("status.settingsSaved")}: training goal changed to ${label}`);
  }

  async function changeUnitSystem(unit_system: UnitSystem) {
    const response = await api.saveSettings({ user_id: DEMO_USER_ID, unit_system });
    if (response.error) {
      setNotice(response.error.message);
      return;
    }
    setData(response.data);
    setNotice(isChinese ? `${t("status.settingsSaved")}：单位偏好已更新` : `${t("status.settingsSaved")}: unit preference updated`);
  }

  function changeNotifications(enabled: boolean) {
    setNotificationsEnabled(enabled);
    setNotice(isChinese ? `${t("status.settingsSaved")}：通知偏好已更新` : `${t("status.settingsSaved")}: notification preference updated`);
  }

  function changeAgentTone(tone: "clinical" | "encouraging" | "strict", label: string) {
    setAgentTone(tone);
    setNotice(isChinese ? `${t("status.settingsSaved")}：教练语气已切换为${label}` : `${t("status.settingsSaved")}: Agent tone changed to ${label}`);
  }

  if (!data) return <div className="business-placeholder">{t("status.loading")}</div>;
  const goalChoices: Array<{ goal: Goal; label: string }> = isChinese
    ? [
        { goal: "conditioning", label: "耐力" },
        { goal: "muscle_gain", label: "增肌" },
        { goal: "fat_loss", label: "减脂" }
      ]
    : [
        { goal: "conditioning", label: "Endurance" },
        { goal: "muscle_gain", label: "Hypertrophy" },
        { goal: "fat_loss", label: "Weight Loss" }
      ];

  return (
    <div className="business-page">
      <header className="page-header">
        <p>945</p>
        <h1>{t("page.settings.title")}</h1>
        <span>{t("page.settings.description")}</span>
      </header>
      {notice ? <div className="business-notice">{notice}</div> : null}

      <section className="settings-layout">
        <div className="settings-main-stack">
        <article className="business-panel user-profile-card">
          <div className="section-heading"><span>{isChinese ? "用户资料" : "User Profile"}</span><strong>{isChinese ? "更换照片" : "Change Photo"}</strong></div>
          <div className="profile-form-grid">
            <span className="profile-photo" />
            <label>{isChinese ? "姓名" : "Full Name"}<input defaultValue={data.user.display_name} /></label>
            <label>{isChinese ? "邮箱地址" : "Email Address"}<input defaultValue="alex.rivera@example.com" /></label>
          </div>
          <label>{isChinese ? "简介 / 目标说明" : "Bio / Goal Statement"}<textarea defaultValue={isChinese ? "备战柏林马拉松，同时维持上肢力量。" : "Preparing for the Berlin Marathon while maintaining upper body strength."} /></label>
        </article>

        <article className="business-panel training-goals-card">
          <div className="section-heading"><span>{isChinese ? "训练目标" : "Training Goals"}</span><strong>{isChinese ? "已可用" : "Available"}</strong></div>
          <p className="settings-boundary-copy">{data.profile.training_days_per_week} {t("labels.daysPerWeek")} · {isChinese ? "点击后会保存到 demo 设置状态" : "Selections save to the demo settings state"}</p>
          <div className="goal-choice-grid">
            {goalChoices.map((choice) => (
              <button
                className={data.profile.goal === choice.goal ? "active" : undefined}
                key={choice.goal}
                onClick={() => void changeGoal(choice.goal, choice.label)}
                type="button"
              >
                {choice.label}
              </button>
            ))}
          </div>
          <div className="slider-line"><span style={{ width: "38%" }} /></div>
        </article>
        </div>

        <div className="settings-side-stack">
        <article className="business-panel compact">
          <div className="section-heading"><h2>{isChinese ? "偏好设置" : "Preferences"}</h2><strong>{isChinese ? "已可用" : "Available"}</strong></div>
          <label>
            {t("settings.language")}
            <select aria-label={isChinese ? "语言" : "settings language"} value={locale} onChange={(event) => void changeLanguage(event.target.value as Locale)}>
              <option value="zh-CN">中文</option>
              <option value="en-US">English</option>
            </select>
          </label>
          <label className="toggle-row">
            {isChinese ? "公制单位" : "Metric System"}
            <input
              checked={data.unit_system === "metric"}
              onChange={(event) => void changeUnitSystem(event.target.checked ? "metric" : "imperial")}
              type="checkbox"
            />
          </label>
          <label className="toggle-row">
            {isChinese ? "推送通知" : "Push Notifications"}
            <input checked={notificationsEnabled} onChange={(event) => changeNotifications(event.target.checked)} type="checkbox" />
          </label>
          <button disabled type="button">{t("labels.dataExport")} · {t("labels.futureCapability")}</button>
          <small>{t("safety.nonMedical")}</small>
        </article>
        <article className="business-panel compact">
          <div className="section-heading"><h2>{isChinese ? "教练语气" : "Agent Tone"}</h2><strong>{isChinese ? "本地 demo" : "Local demo"}</strong></div>
          <label className="radio-row">
            <input checked={agentTone === "clinical"} name="tone" onChange={() => changeAgentTone("clinical", isChinese ? "专业精准" : "Clinical & Precise")} type="radio" />
            {isChinese ? "专业精准" : "Clinical & Precise"}
          </label>
          <label className="radio-row">
            <input checked={agentTone === "encouraging"} name="tone" onChange={() => changeAgentTone("encouraging", isChinese ? "鼓励式教练" : "Encouraging & Coach-like")} type="radio" />
            {isChinese ? "鼓励式教练" : "Encouraging & Coach-like"}
          </label>
          <label className="radio-row">
            <input checked={agentTone === "strict"} name="tone" onChange={() => changeAgentTone("strict", isChinese ? "严格督促" : "Tough Love")} type="radio" />
            {isChinese ? "严格督促" : "Tough Love"}
          </label>
          <small>{isChinese ? "当前只影响本地 demo 展示，真实 Agent 语气配置会在后端接入后持久化。" : "Currently affects the local demo only. Real Agent tone persistence belongs to the backend phase."}</small>
        </article>
        </div>
      </section>
    </div>
  );
}
