import { useEffect, useState } from "react";
import { DEMO_USER_ID } from "../data/demoData";
import { createTranslator } from "../i18n";
import { api } from "../services/mockApi";
import type { Locale, SettingsData } from "../types/domain";

export function SettingsPage({ locale, onLocaleChange }: { locale: Locale; onLocaleChange: (locale: Locale) => void }) {
  const t = createTranslator(locale);
  const [data, setData] = useState<SettingsData | null>(null);
  const [notice, setNotice] = useState("");

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
    await api.saveSettings({ user_id: DEMO_USER_ID, language: nextLocale });
    setNotice(t("status.settingsSaved"));
  }

  if (!data) return <div className="business-placeholder">{t("status.loading")}</div>;

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
          <div className="section-heading"><span>User Profile</span><strong>Change Photo</strong></div>
          <div className="profile-form-grid">
            <span className="profile-photo" />
            <label>Full Name<input defaultValue={data.user.display_name} /></label>
            <label>Email Address<input defaultValue="alex.rivera@example.com" /></label>
          </div>
          <label>Bio / Goal Statement<textarea defaultValue="Preparing for the Berlin Marathon while maintaining upper body strength." /></label>
        </article>

        <article className="business-panel training-goals-card">
          <div className="section-heading"><span>Training Goals</span><strong>{data.profile.training_days_per_week} {t("labels.daysPerWeek")}</strong></div>
          <div className="goal-choice-grid">
            <button className="active" type="button">Endurance</button>
            <button type="button">Hypertrophy</button>
            <button type="button">Weight Loss</button>
          </div>
          <div className="slider-line"><span style={{ width: "38%" }} /></div>
        </article>
        </div>

        <div className="settings-side-stack">
        <article className="business-panel compact">
          <h2>Preferences</h2>
          <label>
            {t("settings.language")}
            <select aria-label="settings language" value={locale} onChange={(event) => void changeLanguage(event.target.value as Locale)}>
              <option value="zh-CN">中文</option>
              <option value="en-US">English</option>
            </select>
          </label>
          <label className="toggle-row">Metric System <input defaultChecked type="checkbox" /></label>
          <label className="toggle-row">Push Notifications <input type="checkbox" /></label>
          <button disabled type="button">{t("labels.dataExport")} · {t("labels.futureCapability")}</button>
          <small>{t("safety.nonMedical")}</small>
        </article>
        <article className="business-panel compact">
          <h2>Agent Tone</h2>
          <label className="radio-row"><input name="tone" type="radio" /> Clinical & Precise</label>
          <label className="radio-row"><input defaultChecked name="tone" type="radio" /> Encouraging & Coach-like</label>
          <label className="radio-row"><input name="tone" type="radio" /> Tough Love</label>
        </article>
        </div>
      </section>
    </div>
  );
}
