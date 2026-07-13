import type { Locale } from "../types/domain";
import { RoutePlaceholderPage } from "./RoutePlaceholderPage";

export function SettingsPage({ locale }: { locale: Locale; onLocaleChange: (locale: Locale) => void }) {
  return <RoutePlaceholderPage locale={locale} titleKey="page.settings.title" descriptionKey="page.settings.description" />;
}
