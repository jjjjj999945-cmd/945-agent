import type { Locale } from "../types/domain";

type RoutePlaceholderPageProps = {
  locale: Locale;
  name: string;
};

export function RoutePlaceholderPage({ locale, name }: RoutePlaceholderPageProps) {
  return (
    <div className="business-placeholder" data-locale={locale}>
      {name}
    </div>
  );
}
