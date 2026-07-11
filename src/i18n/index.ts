import type { Locale } from "../types/domain";
import { enUS } from "./en-US";
import type { MessageKey, Messages } from "./types";
import { zhCN } from "./zh-CN";

export type { MessageKey, Messages } from "./types";

export const bundles = {
  "zh-CN": zhCN,
  "en-US": enUS
} satisfies Record<Locale, { locale: Locale; messages: Messages }>;

export function getMessages(locale: Locale): Messages {
  return bundles[locale]?.messages ?? bundles["zh-CN"].messages;
}

export function createTranslator(locale: Locale) {
  const messages = getMessages(locale);
  return function t(key: MessageKey): string {
    return messages[key];
  };
}
