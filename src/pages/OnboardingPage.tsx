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
          <label>{t("labels.nickname")}<input value={displayName} onChange={(event) => setDisplayName(event.target.value)} /></label>
          <label>{t("labels.age")}<input defaultValue="29" type="number" /></label>
          <label>{t("labels.heightCm")}<input defaultValue="175" type="number" /></label>
          <label>{t("labels.weightKg")}<input defaultValue="76" type="number" /></label>
        </article>
        <article className="business-panel">
          <h2>{t("labels.goalAndPreferences")}</h2>
          <p>{t("labels.goal")}: body_recomposition</p>
          <p>{t("labels.training")}: 4 {t("labels.daysPerWeek")} · 60 min</p>
          <p>{t("labels.diet")}: high_protein</p>
          <p>{t("labels.constraints")}: busy_weekdays</p>
          <button onClick={() => void initializeProfile()} type="button">{t("actions.initializeProfile")}</button>
        </article>
      </section>
    </div>
  );
}
