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
    setNotice("设置已保存");
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

      <section className="page-grid">
        <article className="business-panel">
          <h2>{data.user.display_name}</h2>
          <p>{data.profile.goal.replace(/_/g, " ")} · {data.profile.training_days_per_week} days/week</p>
          <p>{data.profile.height_cm}cm · {data.profile.weight_kg}kg · {data.unit_system}</p>
        </article>

        <article className="business-panel compact">
          <label>
            {t("settings.language")}
            <select aria-label="settings language" value={locale} onChange={(event) => void changeLanguage(event.target.value as Locale)}>
              <option value="zh-CN">中文</option>
              <option value="en-US">English</option>
            </select>
          </label>
          <button disabled type="button">数据导出 · 后续能力</button>
          <small>{t("safety.nonMedical")}</small>
        </article>
      </section>
    </div>
  );
}
