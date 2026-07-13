import { createTranslator } from "../../i18n";
import { primaryRoutes, type RouteId } from "../../routes";
import type { Locale } from "../../types/domain";

type AppShellProps = {
  activeRoute: RouteId;
  locale: Locale;
  onLocaleChange: (locale: Locale) => void;
  onNavigate: (path: string) => void;
  children: React.ReactNode;
};

export function AppShell({ activeRoute, locale, onLocaleChange, onNavigate, children }: AppShellProps) {
  const t = createTranslator(locale);
  const railIcons: Record<RouteId, string> = {
    today: "calendar_today",
    onboarding: "person_add",
    plan: "event_note",
    workout: "fitness_center",
    diet: "restaurant",
    body: "monitoring",
    advice: "auto_awesome",
    agent: "smart_toy",
    settings: "settings"
  };

  const topNav = [
    { label: "Dashboard", path: "/", active: activeRoute === "today" },
    { label: "Analytics", path: "/advice", active: activeRoute === "advice" || activeRoute === "body" || activeRoute === "diet" },
    { label: "Schedule", path: "/plan", active: activeRoute === "plan" || activeRoute === "workout" },
    { label: "Settings", path: "/settings", active: activeRoute === "settings" }
  ];

  return (
    <div className="business-shell">
      <aside className="business-sidebar" aria-label="945 navigation">
        <button aria-label="945 dashboard" className="business-logo" onClick={() => onNavigate("/")} type="button">
          9
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
              <span className="material-symbols-outlined">{railIcons[route.id]}</span>
            </button>
          ))}
        </nav>
        <a aria-label={t("shell.prototypeReference")} className="prototype-reference-link" href="/prototype" title={t("shell.prototypeReference")}>
          <span className="material-symbols-outlined">layers</span>
        </a>
        <span className="business-avatar" aria-hidden="true" />
      </aside>
      <div className="business-workbench">
        <header className="business-topbar">
          <button className="business-brand-wordmark" onClick={() => onNavigate("/")} type="button">
            945 Workbench
          </button>
          <nav className="top-nav" aria-label="Primary">
            {topNav.map((item) => (
              <button className={item.active ? "active" : ""} key={item.label} onClick={() => onNavigate(item.path)} type="button">
                {item.label}
              </button>
            ))}
          </nav>
          <div className="top-actions">
            <button aria-label="Notifications" className="icon-button" type="button">
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
              Sync Agent
            </button>
          </div>
        </header>
        <section className="business-main">{children}</section>
      </div>
    </div>
  );
}
