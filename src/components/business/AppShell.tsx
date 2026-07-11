import { createTranslator, type MessageKey } from "../../i18n";
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

  return (
    <div className="business-shell">
      <aside className="business-sidebar" aria-label="945 navigation">
        <div className="business-brand">
          <button className="business-logo" onClick={() => onNavigate("/")} type="button">
            945
          </button>
          <span className="business-brand-label">Fitness Agent</span>
        </div>
        <nav className="business-nav">
          {primaryRoutes.map((route) => (
            <button className={route.id === activeRoute ? "active" : ""} key={route.id} onClick={() => onNavigate(route.path)} type="button">
              {t(route.navKey as MessageKey)}
            </button>
          ))}
        </nav>
        <a className="prototype-reference-link" href="/prototype">
          Stitch reference
        </a>
        <label className="business-language">
          <span>Language</span>
          <select value={locale} onChange={(event) => onLocaleChange(event.target.value as Locale)}>
            <option value="zh-CN">中文</option>
            <option value="en-US">English</option>
          </select>
        </label>
      </aside>
      <section className="business-main">{children}</section>
    </div>
  );
}
