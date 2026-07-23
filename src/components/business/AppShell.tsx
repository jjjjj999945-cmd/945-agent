import { createTranslator } from "../../i18n";
import { primaryRoutes, type RouteId } from "../../routes";
import type { Locale } from "../../types/domain";

type AppShellProps = {
  activeRoute: RouteId;
  locale: Locale;
  onLocaleChange: (locale: Locale) => void;
  onNavigate: (path: string) => void;
  onLogout?: () => void;
  children: React.ReactNode;
};

export function AppShell({ activeRoute, locale, onLocaleChange, onNavigate, onLogout, children }: AppShellProps) {
  const t = createTranslator(locale);
  const railIcons: Record<RouteId, string> = {
    today: "dashboard",
    onboarding: "person_add",
    plan: "event_note",
    workout: "exercise",
    diet: "local_dining",
    body: "monitor_heart",
    advice: "tips_and_updates",
    agent: "neurology",
    settings: "settings"
  };

  const topNav = locale === "zh-CN"
    ? [
        { label: "今日", path: "/", active: activeRoute === "today" },
        { label: "分析", path: "/advice", active: activeRoute === "advice" || activeRoute === "body" || activeRoute === "diet" },
        { label: "计划", path: "/plan", active: activeRoute === "plan" || activeRoute === "workout" },
        { label: "设置", path: "/settings", active: activeRoute === "settings" }
      ]
    : [
        { label: "Dashboard", path: "/", active: activeRoute === "today" },
        { label: "Analytics", path: "/advice", active: activeRoute === "advice" || activeRoute === "body" || activeRoute === "diet" },
        { label: "Schedule", path: "/plan", active: activeRoute === "plan" || activeRoute === "workout" },
        { label: "Settings", path: "/settings", active: activeRoute === "settings" }
      ];

  return (
    <div className="business-shell">
      <aside className="business-sidebar" aria-label={locale === "zh-CN" ? "945 导航" : "945 navigation"}>
        <button aria-label={locale === "zh-CN" ? "945 今日工作台" : "945 dashboard"} className="business-logo" onClick={() => onNavigate("/")} type="button">
          <span className="rail-icon-base">9</span>
          <span aria-hidden="true" className="rail-icon-hover">9</span>
        </button>
        <nav className="business-nav">
          {primaryRoutes.map((route) => (
            <button
              aria-label={t(route.navKey)}
              className={route.id === activeRoute ? "active" : ""}
              key={route.id}
              onClick={() => onNavigate(route.path)}
              title={t(route.navKey)}
              type="button"
            >
              <span className="material-symbols-outlined rail-icon-base">{railIcons[route.id]}</span>
              <span aria-hidden="true" className="material-symbols-outlined rail-icon-hover">{railIcons[route.id]}</span>
            </button>
          ))}
        </nav>
        <a aria-label={t("shell.prototypeReference")} className="prototype-reference-link" href="/prototype" title={t("shell.prototypeReference")}>
          <span className="material-symbols-outlined rail-icon-base">layers</span>
          <span aria-hidden="true" className="material-symbols-outlined rail-icon-hover">layers</span>
        </a>
        <span className="business-avatar" aria-hidden="true" />
      </aside>
      <div className="business-workbench">
        <header className="business-topbar">
          <button className="business-brand-wordmark" onClick={() => onNavigate("/")} type="button">
            {locale === "zh-CN" ? "945 健身工作台" : "945 Workbench"}
          </button>
          <nav className="top-nav" aria-label={locale === "zh-CN" ? "主导航" : "Primary"}>
            {topNav.map((item) => (
              <button className={item.active ? "active" : ""} key={item.label} onClick={() => onNavigate(item.path)} type="button">
                {item.label}
              </button>
            ))}
          </nav>
          <div className="top-actions">
            <button aria-label={locale === "zh-CN" ? "通知" : "Notifications"} className="icon-button" type="button">
              <span className="material-symbols-outlined">notifications</span>
            </button>
            <label className="business-language">
              <span>{t("settings.language")}</span>
              <select value={locale} onChange={(event) => onLocaleChange(event.target.value as Locale)}>
                <option value="zh-CN">中文</option>
                <option value="en-US">English</option>
              </select>
            </label>
            <button className="sync-agent-button" onClick={() => onNavigate("/agent")} type="button">
              <span className="material-symbols-outlined">sync</span>
              {locale === "zh-CN" ? "同步教练" : "Sync Agent"}
            </button>
            {onLogout ? <button className="logout-button" onClick={onLogout} type="button">{locale === "zh-CN" ? "退出登录" : "Sign out"}</button> : null}
          </div>
        </header>
        <section className="business-main">{children}</section>
      </div>
    </div>
  );
}
