import { createTranslator, type MessageKey } from "../i18n";
import type { Locale } from "../types/domain";

type RoutePlaceholderPageProps = {
  locale: Locale;
  titleKey: MessageKey;
  descriptionKey: MessageKey;
};

export function RoutePlaceholderPage({ locale, titleKey, descriptionKey }: RoutePlaceholderPageProps) {
  const t = createTranslator(locale);

  return (
    <div className="business-placeholder" data-locale={locale}>
      <p>945</p>
      <h1>{t(titleKey)}</h1>
      <span>{t(descriptionKey)}</span>
    </div>
  );
}
