import type { Locale } from "../../types/domain";
import { createTranslator } from "../../i18n";

type AppShellProps = {
  locale: Locale;
  onLocaleChange: (locale: Locale) => void;
  children: React.ReactNode;
};

const navKeys = [
  "nav.today",
  "nav.workout",
  "nav.diet",
  "nav.body",
  "nav.advice",
  "nav.agent",
  "nav.settings"
] as const;

export function AppShell({ locale, onLocaleChange, children }: AppShellProps) {
  const t = createTranslator(locale);

  return (
    <div className="business-shell">
      <aside className="business-sidebar" aria-label="945 navigation">
        <div className="business-brand">
          <span className="business-logo">945</span>
          <span className="business-brand-label">Fitness Agent</span>
        </div>
        <nav className="business-nav">
          {navKeys.map((key) => (
            <button className={key === "nav.today" ? "active" : ""} key={key}>
              {t(key)}
            </button>
          ))}
        </nav>
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
