import type { Locale } from "../types/domain";
import { RoutePlaceholderPage } from "./RoutePlaceholderPage";

export function AdvicePage({ locale }: { locale: Locale }) {
  return <RoutePlaceholderPage locale={locale} name="Advice" />;
}
