import { createTranslator } from "../../i18n";
import { primaryRoutes, type RouteId } from "../../routes";
import type { Locale } from "../../types/domain";
import {
  BrainCircuit,
  CalendarDays,
  Dumbbell,
  HeartPulse,
  LayoutDashboard,
  Lightbulb,
  Settings2,
  UserRoundPlus,
  UtensilsCrossed,
  type LucideIcon
} from "lucide-react";

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
  const railIcons: Record<RouteId, LucideIcon> = {
    today: LayoutDashboard,
    onboarding: UserRoundPlus,
    plan: CalendarDays,
    workout: Dumbbell,
    diet: UtensilsCrossed,
    body: HeartPulse,
    advice: Lightbulb,
    agent: BrainCircuit,
    settings: Settings2
  };

  const topNav = locale === "zh-CN"
    ? [
        { label: "今日", path: "/today", active: activeRoute === "today" },
        { label: "分析", path: "/advice", active: activeRoute === "advice" || activeRoute === "body" || activeRoute === "diet" },
        { label: "计划", path: "/plan", active: activeRoute === "plan" || activeRoute === "workout" },
        { label: "设置", path: "/settings", active: activeRoute === "settings" }
      ]
    : [
        { label: "Dashboard", path: "/today", active: activeRoute === "today" },
        { label: "Analytics", path: "/advice", active: activeRoute === "advice" || activeRoute === "body" || activeRoute === "diet" },
        { label: "Schedule", path: "/plan", active: activeRoute === "plan" || activeRoute === "workout" },
        { label: "Settings", path: "/settings", active: activeRoute === "settings" }
      ];

  return (
    <div className="business-shell">
      <aside className="business-sidebar" aria-label={locale === "zh-CN" ? "945 导航" : "945 navigation"}>
        <button aria-label={locale === "zh-CN" ? "945 今日工作台" : "945 dashboard"} className="business-logo" onClick={() => onNavigate("/")} type="button">
          <span className="rail-icon-base brand-mark" aria-hidden="true">945</span>
          <span aria-hidden="true" className="rail-icon-hover">945</span>
        </button>
        <nav className="business-nav">
          {primaryRoutes.map((route) => (
            <NavButton
              active={route.id === activeRoute}
              icon={railIcons[route.id]}
              key={route.id}
              label={t(route.navKey)}
              onClick={() => onNavigate(route.path)}
            />
          ))}
        </nav>
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
            <button className="sync-agent-button" onClick={() => onNavigate("/")} type="button">
              <span className="material-symbols-outlined">sync</span>
              {locale === "zh-CN" ? "同步教练" : "Sync Agent"}
            </button>
            {onLogout ? (
              <button
                aria-label={locale === "zh-CN" ? "退出登录" : "Sign out"}
                className="logout-button"
                onClick={onLogout}
                title={locale === "zh-CN" ? "退出登录" : "Sign out"}
                type="button"
              >
                <span aria-hidden="true" className="material-symbols-outlined">logout</span>
              </button>
            ) : null}
          </div>
        </header>
        <section className="business-main">{children}</section>
      </div>
    </div>
  );
}

function NavButton({ active, icon: Icon, label, onClick }: { active: boolean; icon: LucideIcon; label: string; onClick: () => void }) {
  return (
    <button aria-label={label} className={active ? "active" : ""} onClick={onClick} title={label} type="button">
      <Icon aria-hidden="true" className="rail-lucide-icon" strokeWidth={2} />
      <span className="sidebar-nav-label">{label}</span>
    </button>
  );
}
