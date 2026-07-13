import type { Locale } from "../types/domain";
import { RoutePlaceholderPage } from "./RoutePlaceholderPage";

export function AgentPage({ locale }: { locale: Locale }) {
  return <RoutePlaceholderPage locale={locale} titleKey="page.agent.title" descriptionKey="page.agent.description" />;
}

