export function resolveAppToday(referenceDate: string | undefined, now = new Date()) {
  return referenceDate ?? now.toISOString().slice(0, 10);
}

export const appToday = resolveAppToday(import.meta.env?.VITE_945_REFERENCE_DATE);
