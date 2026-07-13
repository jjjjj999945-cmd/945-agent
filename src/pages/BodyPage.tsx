import type { Locale } from "../types/domain";
import { RoutePlaceholderPage } from "./RoutePlaceholderPage";

export function BodyPage({ locale }: { locale: Locale }) {
  return <RoutePlaceholderPage locale={locale} titleKey="page.body.title" descriptionKey="page.body.description" />;
}

