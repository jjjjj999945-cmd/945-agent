import type { Locale } from "../types/domain";
import { RoutePlaceholderPage } from "./RoutePlaceholderPage";

export function AgentPage({ locale }: { locale: Locale }) {
  return <RoutePlaceholderPage locale={locale} name="Agent" />;
}
