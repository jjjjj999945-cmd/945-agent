import { useEffect, useState } from "react";
import { AppShell } from "./components/business/AppShell";
import { AgentPage } from "./pages/AgentPage";
import { AdvicePage } from "./pages/AdvicePage";
import { BodyPage } from "./pages/BodyPage";
import { DietPage } from "./pages/DietPage";
import { OnboardingPage } from "./pages/OnboardingPage";
import { PlanPage } from "./pages/PlanPage";
import { PrototypeRouter } from "./pages/PrototypeRouter";
import { SettingsPage } from "./pages/SettingsPage";
import { TodayPage } from "./pages/TodayPage";
import { WorkoutPage } from "./pages/WorkoutPage";
import { getRouteByPath, isPrototypePath, type RouteId } from "./routes";
import type { Locale } from "./types/domain";

export function App() {
  const [locale, setLocale] = useState<Locale>("zh-CN");
  const [path, setPath] = useState(window.location.pathname);

  useEffect(() => {
    const onPopState = () => setPath(window.location.pathname);
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  function navigate(nextPath: string) {
    window.history.pushState({}, "", nextPath);
    setPath(nextPath);
  }

  if (isPrototypePath(path)) return <PrototypeRouter />;

  const route = getRouteByPath(path);

  return (
    <AppShell activeRoute={route.id} locale={locale} onLocaleChange={setLocale} onNavigate={navigate}>
      {renderPage(route.id, locale, navigate, setLocale)}
    </AppShell>
  );
}

function renderPage(
  routeId: RouteId,
  locale: Locale,
  navigate: (path: string) => void,
  onLocaleChange: (locale: Locale) => void
) {
  switch (routeId) {
    case "onboarding":
      return <OnboardingPage locale={locale} onNavigate={navigate} />;
    case "plan":
      return <PlanPage locale={locale} onNavigate={navigate} />;
    case "workout":
      return <WorkoutPage locale={locale} />;
    case "diet":
      return <DietPage locale={locale} />;
    case "body":
      return <BodyPage locale={locale} />;
    case "advice":
      return <AdvicePage locale={locale} />;
    case "agent":
      return <AgentPage locale={locale} />;
    case "settings":
      return <SettingsPage locale={locale} onLocaleChange={onLocaleChange} />;
    case "today":
    default:
      return <TodayPage locale={locale} />;
  }
}
