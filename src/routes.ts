import type { MessageKey } from "./i18n";

export type RouteId =
  | "today"
  | "onboarding"
  | "plan"
  | "workout"
  | "diet"
  | "body"
  | "advice"
  | "agent"
  | "settings";

export type AppRoute = {
  id: RouteId;
  path: string;
  navKey: MessageKey;
  titleKey: MessageKey;
  descriptionKey: MessageKey;
  primary: boolean;
};

export const primaryRoutes: AppRoute[] = [
  { id: "agent", path: "/", navKey: "nav.agent", titleKey: "page.agent.title", descriptionKey: "page.agent.description", primary: true },
  { id: "today", path: "/today", navKey: "nav.today", titleKey: "page.today.title", descriptionKey: "page.today.description", primary: true },
  { id: "workout", path: "/workout", navKey: "nav.workout", titleKey: "page.workout.title", descriptionKey: "page.workout.description", primary: true },
  { id: "diet", path: "/diet", navKey: "nav.diet", titleKey: "page.diet.title", descriptionKey: "page.diet.description", primary: true },
  { id: "body", path: "/body", navKey: "nav.body", titleKey: "page.body.title", descriptionKey: "page.body.description", primary: true },
  { id: "advice", path: "/advice", navKey: "nav.advice", titleKey: "page.advice.title", descriptionKey: "page.advice.description", primary: true },
  { id: "settings", path: "/settings", navKey: "nav.settings", titleKey: "page.settings.title", descriptionKey: "page.settings.description", primary: true }
];

export const secondaryRoutes: AppRoute[] = [
  { id: "onboarding", path: "/onboarding", navKey: "nav.onboarding", titleKey: "page.onboarding.title", descriptionKey: "page.onboarding.description", primary: false },
  { id: "plan", path: "/plan", navKey: "nav.plan", titleKey: "page.plan.title", descriptionKey: "page.plan.description", primary: false }
];

export const appRoutes = [...primaryRoutes, ...secondaryRoutes];

export function getRouteByPath(pathname: string) {
  const rawPath = pathname === "" ? "/" : pathname.replace(/\/+$/, "") || "/";
  const normalized = rawPath === "/agent" ? "/" : rawPath;
  return appRoutes.find((route) => route.path === normalized) ?? primaryRoutes[0];
}

export function isPrototypePath(pathname: string) {
  return pathname === "/prototype" || pathname.startsWith("/prototype/");
}
