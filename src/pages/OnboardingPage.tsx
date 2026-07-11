import type { Locale } from "../types/domain";
import { RoutePlaceholderPage } from "./RoutePlaceholderPage";

export function OnboardingPage({ locale }: { locale: Locale; onNavigate: (path: string) => void }) {
  return <RoutePlaceholderPage locale={locale} name="Onboarding" />;
}
