import type { Locale } from "../types/domain";
import { RoutePlaceholderPage } from "./RoutePlaceholderPage";

export function WorkoutPage({ locale }: { locale: Locale }) {
  return <RoutePlaceholderPage locale={locale} name="Workout" />;
}
