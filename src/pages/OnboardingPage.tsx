import { useState } from "react";
import { createTranslator } from "../i18n";
import { api } from "../services/mockApi";
import { DEMO_USER_ID } from "../data/demoData";
import type { Locale } from "../types/domain";

export function OnboardingPage({ locale, onNavigate }: { locale: Locale; onNavigate: (path: string) => void }) {
  const t = createTranslator(locale);
  const [displayName, setDisplayName] = useState("Alex");

  async function initializeProfile() {
    await api.updateProfile({
      user_id: DEMO_USER_ID,
      age: 29,
      height_cm: 175,
      weight_kg: 76,
      goal: "body_recomposition",
      experience_level: "novice",
      training_days_per_week: 4,
      training_duration_minutes: 60,
      dietary_preferences: ["high_protein"],
      constraints: ["busy_weekdays"]
    });
    onNavigate("/plan");
  }

  return (
    <div className="business-page">
      <header className="page-header">
        <p>945</p>
        <h1>{t("page.onboarding.title")}</h1>
        <span>{t("page.onboarding.description")}</span>
      </header>
      <section className="page-grid">
        <article className="business-panel compact">
          <label>昵称<input value={displayName} onChange={(event) => setDisplayName(event.target.value)} /></label>
          <label>年龄<input defaultValue="29" type="number" /></label>
          <label>身高 cm<input defaultValue="175" type="number" /></label>
          <label>体重 kg<input defaultValue="76" type="number" /></label>
        </article>
        <article className="business-panel">
          <h2>目标和偏好</h2>
          <p>目标：body_recomposition</p>
          <p>训练：每周 4 天，每次 60 分钟</p>
          <p>饮食：high_protein</p>
          <p>限制：busy_weekdays</p>
          <button onClick={() => void initializeProfile()} type="button">Initialize demo profile</button>
        </article>
      </section>
    </div>
  );
}
