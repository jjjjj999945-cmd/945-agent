import type { Locale } from "../types/domain";
import { RoutePlaceholderPage } from "./RoutePlaceholderPage";

export function BodyPage({ locale }: { locale: Locale }) {
  return <RoutePlaceholderPage locale={locale} name="Body" />;
}
