import { useEffect, useState } from "react";
import { PageLoadState } from "../components/business/PageLoadState";
import { DEMO_USER_ID } from "../data/demoData";
import { createTranslator } from "../i18n";
import { api } from "../services/apiClient";
import type { Goal, Locale, Plan, SettingsData, UnitSystem, UserProfile } from "../types/domain";

export function SettingsPage({ locale, onLocaleChange }: { locale: Locale; onLocaleChange: (locale: Locale) => void }) {
  const t = createTranslator(locale);
  const isChinese = locale === "zh-CN";
  const [data, setData] = useState<SettingsData | null>(null);
  const [profileDraft, setProfileDraft] = useState<UserProfile | null>(null);
  const [planPreview, setPlanPreview] = useState<Plan | null>(null);
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
    setProfileDraft(response.data.profile);
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
    setProfileDraft(response.data.profile);
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

  function toggleProfileValue(field: "equipment" | "dietary_preferences" | "allergies" | "constraints", value: string) {
    setProfileDraft((current) => {
      if (!current) return current;
      const values = current[field];
      return { ...current, [field]: values.includes(value) ? values.filter((item) => item !== value) : [...values, value] };
    });
  }

  async function saveProfileAndGeneratePlan() {
    if (!profileDraft) return;
    const saved = await api.saveSettings({ user_id: DEMO_USER_ID, profile: profileDraft });
    if (saved.error) {
      setNotice(saved.error.message);
      return;
    }
    setData(saved.data);
    setProfileDraft(saved.data.profile);
    const generated = await api.generatePlan({ user_id: DEMO_USER_ID });
    if (generated.error) {
      setNotice(generated.error.message);
      return;
    }
    setPlanPreview(generated.data);
    setNotice(isChinese ? "资料已保存，计划预览已生成。" : "Profile saved and plan preview generated.");
  }

  async function acceptPlanPreview() {
    if (!planPreview) return;
    const response = await api.acceptPlan({ user_id: DEMO_USER_ID, plan_id: planPreview.plan_id });
    if (response.error) {
      setNotice(response.error.message);
      return;
    }
    setPlanPreview(null);
    setNotice(isChinese ? "新计划已接受并生效。" : "The new plan is accepted and active.");
  }

  async function exportData() {
    const response = await api.exportData(DEMO_USER_ID);
    if (response.error) {
      setNotice(response.error.message);
      return;
    }
    const blob = new Blob([JSON.stringify(response.data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `945-data-${new Date().toISOString().slice(0, 10)}.json`;
    link.click();
    URL.revokeObjectURL(url);
    setNotice(isChinese ? "数据导出已开始。" : "Data export started.");
  }

  if (!data || !profileDraft) return <PageLoadState message={notice || t("status.loading")} />;
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
        <article className="business-panel profile-preferences-card">
          <div className="section-heading"><span>{isChinese ? "计划个性化资料" : "Plan Personalization"}</span><strong>{isChinese ? "真实保存" : "Saved to profile"}</strong></div>
          <div className="profile-form-grid">
            <label>{isChinese ? "每周训练天数" : "Training days per week"}<input aria-label={isChinese ? "每周训练天数" : "Training days per week"} min="1" max="7" type="number" value={profileDraft.training_days_per_week} onChange={(event) => setProfileDraft({ ...profileDraft, training_days_per_week: Number(event.target.value) })} /></label>
            <label>{isChinese ? "单次训练分钟" : "Training minutes"}<input aria-label={isChinese ? "单次训练分钟" : "Training minutes"} min="15" max="180" step="15" type="number" value={profileDraft.training_duration_minutes} onChange={(event) => setProfileDraft({ ...profileDraft, training_duration_minutes: Number(event.target.value) })} /></label>
          </div>
          <div className="preference-choice-grid">
            <fieldset><legend>{isChinese ? "可用器械" : "Equipment"}</legend>{[["gym", isChinese ? "健身房" : "Gym"], ["dumbbells", isChinese ? "哑铃" : "Dumbbells"], ["bodyweight", isChinese ? "徒手" : "Bodyweight"]].map(([value, label]) => <label className="toggle-row" key={value}><input checked={profileDraft.equipment.includes(value)} onChange={() => toggleProfileValue("equipment", value)} type="checkbox" />{label}</label>)}</fieldset>
            <fieldset><legend>{isChinese ? "饮食偏好" : "Dietary preferences"}</legend>{[["high_protein", isChinese ? "高蛋白" : "High protein"], ["vegetarian", isChinese ? "素食" : "Vegetarian"], ["vegan", isChinese ? "纯素" : "Vegan"]].map(([value, label]) => <label className="toggle-row" key={value}><input checked={profileDraft.dietary_preferences.includes(value)} onChange={() => toggleProfileValue("dietary_preferences", value)} type="checkbox" />{label}</label>)}</fieldset>
            <fieldset><legend>{isChinese ? "过敏或禁忌" : "Allergies or exclusions"}</legend>{[["dairy", isChinese ? "乳制品" : "Dairy"], ["gluten", isChinese ? "麸质" : "Gluten"], ["seafood", isChinese ? "海鲜" : "Seafood"]].map(([value, label]) => <label className="toggle-row" key={value}><input checked={profileDraft.allergies.includes(value)} onChange={() => toggleProfileValue("allergies", value)} type="checkbox" />{label}</label>)}</fieldset>
            <fieldset><legend>{isChinese ? "时间限制" : "Schedule constraints"}</legend><label className="toggle-row"><input checked={profileDraft.constraints.includes("busy_weekdays")} onChange={() => toggleProfileValue("constraints", "busy_weekdays")} type="checkbox" />{isChinese ? "工作日繁忙" : "Busy weekdays"}</label></fieldset>
          </div>
          <div className="button-row"><button onClick={() => void saveProfileAndGeneratePlan()} type="button">{isChinese ? "保存并生成计划预览" : "Save and generate preview"}</button></div>
          {planPreview ? <div className="plan-preview-detail" aria-label={isChinese ? "个性化计划预览" : "Personalized plan preview"}>
            <div className="plan-preview-summary"><strong>{isChinese ? "计划预览" : "Plan preview"}</strong><span>{planPreview.goal.replace(/_/g, " ")} · {planPreview.workout_plan.days.length} {isChinese ? "个训练日" : "workout days"} · {planPreview.meal_plan.daily_targets.calories} {t("metrics.kcal")}</span><button onClick={() => void acceptPlanPreview()} type="button">{isChinese ? "接受此计划" : "Accept this plan"}</button></div>
            <div className="plan-preview-columns">
              <section><h3>{isChinese ? "训练安排" : "Workout schedule"}</h3>{planPreview.workout_plan.days.map((day) => <div className="preview-day-row" key={day.date}><strong>{day.date} · {day.name}</strong><span>{day.exercises.map((exercise) => `${exercise.name} ${exercise.sets} × ${exercise.reps}`).join(" / ") || (isChinese ? "恢复日" : "Recovery day")}</span></div>)}</section>
              <section><h3>{isChinese ? "饮食安排" : "Meal schedule"}</h3>{planPreview.meal_plan.days.map((day) => <div className="preview-day-row" key={day.date}><strong>{day.date} · {day.meals.reduce((sum, meal) => sum + meal.total_macros.calories, 0)} {t("metrics.kcal")}</strong><span>{day.meals.map((meal) => `${meal.name}: ${meal.foods.map((food) => `${food.name} ${food.portion}`).join(", ")}`).join(" · ")}</span></div>)}</section>
            </div>
          </div> : null}
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
          <button onClick={() => void exportData()} type="button">{t("labels.dataExport")}</button>
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
