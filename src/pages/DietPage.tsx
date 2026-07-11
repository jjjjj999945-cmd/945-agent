import type { Locale } from "../types/domain";
import { RoutePlaceholderPage } from "./RoutePlaceholderPage";

export function DietPage({ locale }: { locale: Locale }) {
  return <RoutePlaceholderPage locale={locale} name="Diet" />;
}
