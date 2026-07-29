import { useState } from "react";
import { DEMO_USER_ID } from "../data/demoData";
import { createTranslator } from "../i18n";
import { usePlanContext } from "../contexts/PlanContext";
import { api } from "../services/apiClient";
import type { ExperienceLevel, Goal, Locale } from "../types/domain";

type OnboardingPageProps = { embedded?: boolean; locale: Locale; onNavigate: (path: string) => void };

const goalOptions: Array<{ value: Goal; zh: string; en: string }> = [
  { value: "fat_loss", zh: "减脂", en: "Fat loss" },
  { value: "muscle_gain", zh: "增肌", en: "Muscle gain" },
  { value: "body_recomposition", zh: "体态重组", en: "Body recomposition" },
  { value: "strength", zh: "力量提升", en: "Strength" },
  { value: "conditioning", zh: "体能提升", en: "Conditioning" },
  { value: "maintenance", zh: "维持健康", en: "Maintenance" }
];

function toggle(values: string[], value: string) {
  return values.includes(value) ? values.filter((item) => item !== value) : [...values, value];
}

export function OnboardingPage({ embedded = false, locale, onNavigate }: OnboardingPageProps) {
  const { refreshPlanState } = usePlanContext();
  const t = createTranslator(locale);
  const zh = locale === "zh-CN";
  const [age, setAge] = useState(29);
  const [heightCm, setHeightCm] = useState(175);
  const [weightKg, setWeightKg] = useState(76);
  const [goal, setGoal] = useState<Goal>("body_recomposition");
  const [experience, setExperience] = useState<ExperienceLevel>("novice");
  const [days, setDays] = useState(4);
  const [duration, setDuration] = useState(60);
  const [equipment, setEquipment] = useState<string[]>(["dumbbells", "gym"]);
  const [dietaryPreferences, setDietaryPreferences] = useState<string[]>(["high_protein"]);
  const [allergies, setAllergies] = useState("");
  const [constraints, setConstraints] = useState<string[]>(["busy_weekdays"]);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError("");
    const profile = await api.updateProfile({
      user_id: DEMO_USER_ID,
      age,
      height_cm: heightCm,
      weight_kg: weightKg,
      goal,
      experience_level: experience,
      training_days_per_week: days,
      training_duration_minutes: duration,
      equipment,
      dietary_preferences: dietaryPreferences,
      allergies: allergies.split(/[,，]/).map((item) => item.trim()).filter(Boolean),
      constraints
    });
    if (profile.error) {
      setSaving(false);
      setError(profile.error.message);
      return;
    }
    const plan = await api.generatePlan({ user_id: DEMO_USER_ID, goal });
    if (plan.error) {
      setSaving(false);
      setError(plan.error.message);
      return;
    }
    const accepted = await api.acceptPlan({ user_id: DEMO_USER_ID, plan_id: plan.data.plan_id });
    setSaving(false);
    if (accepted.error) {
      setError(accepted.error.message);
      return;
    }
    await refreshPlanState();
    onNavigate("/");
  }

  const form = <form className="onboarding-form" onSubmit={submit}>
      <section className="business-panel"><h2>{zh ? "身体与目标" : "Body and goal"}</h2><div className="onboarding-fields">
        <label>{t("labels.age")}<input aria-label={t("labels.age")} min="14" max="100" required type="number" value={age} onChange={(event) => setAge(Number(event.target.value))} /></label>
        <label>{t("labels.heightCm")}<input aria-label={t("labels.heightCm")} min="100" max="250" required type="number" value={heightCm} onChange={(event) => setHeightCm(Number(event.target.value))} /></label>
        <label>{t("labels.weightKg")}<input aria-label={t("labels.weightKg")} min="30" max="300" required step="0.1" type="number" value={weightKg} onChange={(event) => setWeightKg(Number(event.target.value))} /></label>
        <label>{t("labels.goal")}<select aria-label={t("labels.goal")} value={goal} onChange={(event) => setGoal(event.target.value as Goal)}>{goalOptions.map((option) => <option key={option.value} value={option.value}>{zh ? option.zh : option.en}</option>)}</select></label>
      </div></section>
      <section className="business-panel"><h2>{zh ? "训练条件" : "Training setup"}</h2><div className="onboarding-fields">
        <label>{zh ? "训练经验" : "Experience"}<select aria-label={zh ? "训练经验" : "Experience"} value={experience} onChange={(event) => setExperience(event.target.value as ExperienceLevel)}><option value="beginner">{zh ? "初学者" : "Beginner"}</option><option value="novice">{zh ? "入门" : "Novice"}</option><option value="intermediate">{zh ? "中级" : "Intermediate"}</option><option value="advanced">{zh ? "高级" : "Advanced"}</option></select></label>
        <label>{zh ? "每周训练天数" : "Days per week"}<input aria-label={zh ? "每周训练天数" : "Days per week"} min="1" max="7" required type="number" value={days} onChange={(event) => setDays(Number(event.target.value))} /></label>
        <label>{zh ? "每次训练分钟" : "Minutes per session"}<input aria-label={zh ? "每次训练分钟" : "Minutes per session"} min="15" max="240" required step="5" type="number" value={duration} onChange={(event) => setDuration(Number(event.target.value))} /></label>
      </div><fieldset><legend>{zh ? "可用器械" : "Equipment"}</legend>{["gym", "dumbbells", "bodyweight"].map((item) => <label className="onboarding-choice" key={item}><input checked={equipment.includes(item)} onChange={() => setEquipment(toggle(equipment, item))} type="checkbox" />{item}</label>)}</fieldset></section>
      <section className="business-panel"><h2>{zh ? "饮食与限制" : "Nutrition and constraints"}</h2><fieldset><legend>{zh ? "饮食偏好" : "Dietary preferences"}</legend>{["high_protein", "vegetarian", "vegan"].map((item) => <label className="onboarding-choice" key={item}><input checked={dietaryPreferences.includes(item)} onChange={() => setDietaryPreferences(toggle(dietaryPreferences, item))} type="checkbox" />{item}</label>)}</fieldset>
        <label>{zh ? "过敏或忌口（用逗号分隔）" : "Allergies or exclusions (comma separated)"}<input aria-label={zh ? "过敏或忌口" : "Allergies or exclusions"} value={allergies} onChange={(event) => setAllergies(event.target.value)} /></label>
        <fieldset><legend>{zh ? "日程限制" : "Schedule constraints"}</legend><label className="onboarding-choice"><input checked={constraints.includes("busy_weekdays")} onChange={() => setConstraints(toggle(constraints, "busy_weekdays"))} type="checkbox" />{zh ? "工作日繁忙" : "Busy weekdays"}</label></fieldset>
      </section>
      {error && <p className="form-error">{error}</p>}
      <div className="button-row"><button disabled={saving} type="submit">{saving ? (zh ? "正在创建计划..." : "Creating plan...") : (zh ? "创建并启用我的计划" : "Create and activate my plan")}</button></div>
    </form>;

  if (embedded) return form;

  return <div className="business-page">
    <header className="page-header"><p>945</p><h1>{zh ? "创建你的训练档案" : "Build your fitness profile"}</h1><span>{zh ? "填写这些信息后，945 会创建你的第一份 7 天训练和饮食计划。" : "Use these details to create your first 7-day workout and nutrition plan."}</span></header>
    {form}
  </div>;
}
