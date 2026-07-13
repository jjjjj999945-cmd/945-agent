import type { Locale } from "../types/domain";
import { RoutePlaceholderPage } from "./RoutePlaceholderPage";

export function WorkoutPage({ locale }: { locale: Locale }) {
  return <RoutePlaceholderPage locale={locale} titleKey="page.workout.title" descriptionKey="page.workout.description" />;
}
