import type { Locale } from "../types/domain";
import { RoutePlaceholderPage } from "./RoutePlaceholderPage";

export function AdvicePage({ locale }: { locale: Locale }) {
  return <RoutePlaceholderPage locale={locale} titleKey="page.advice.title" descriptionKey="page.advice.description" />;
}
