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
import { AuthPage } from "./pages/AuthPage";
import { getRouteByPath, isPrototypePath, type RouteId } from "./routes";
import type { Locale, RecordDraft } from "./types/domain";
import { authApi, clearSession, hasSession } from "./services/authSession";

export function App() {
  const [locale, setLocale] = useState<Locale>("zh-CN");
  const [path, setPath] = useState(window.location.pathname);
  const [agentDraft, setAgentDraft] = useState<RecordDraft | null>(null);
  const httpMode = import.meta.env.VITE_945_API_MODE === "http" && import.meta.env.VITE_945_AUTH_ENABLED !== "false";
  const [sessionReady, setSessionReady] = useState(!httpMode);
  const [authenticated, setAuthenticated] = useState(!httpMode || hasSession());

  useEffect(() => {
    const onPopState = () => setPath(window.location.pathname);
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  useEffect(() => {
    if (!httpMode) return;
    if (!hasSession()) {
      setAuthenticated(false);
      setSessionReady(true);
      return;
    }
    authApi.me().then((result) => {
      if (result.error) {
        clearSession();
        setAuthenticated(false);
      }
      setSessionReady(true);
    });
  }, [httpMode]);

  function navigate(nextPath: string) {
    window.history.pushState({}, "", nextPath);
    setPath(nextPath);
  }

  async function logout() {
    await authApi.logout();
    clearSession();
    setAuthenticated(false);
    window.history.replaceState({}, "", "/");
    setPath("/");
  }

  if (isPrototypePath(path)) return <PrototypeRouter />;
  if (!sessionReady) return null;
  if (!authenticated) return <AuthPage onAuthenticated={() => window.location.replace("/onboarding")} />;

  const route = getRouteByPath(path);

  return (
    <AppShell activeRoute={route.id} locale={locale} onLocaleChange={setLocale} onNavigate={navigate} onLogout={httpMode ? logout : undefined}>
      {renderPage(route.id, locale, navigate, setLocale, agentDraft, setAgentDraft)}
    </AppShell>
  );
}

function renderPage(
  routeId: RouteId,
  locale: Locale,
  navigate: (path: string) => void,
  onLocaleChange: (locale: Locale) => void,
  agentDraft: RecordDraft | null,
  onAgentDraftChange: (draft: RecordDraft | null) => void,
) {
  switch (routeId) {
    case "onboarding":
      return <OnboardingPage locale={locale} onNavigate={navigate} />;
    case "plan":
      return <PlanPage locale={locale} onNavigate={navigate} onAgentDraft={onAgentDraftChange} />;
    case "workout":
      return <WorkoutPage locale={locale} />;
    case "diet":
      return <DietPage locale={locale} />;
    case "body":
      return <BodyPage locale={locale} />;
    case "advice":
      return <AdvicePage locale={locale} onNavigate={navigate} onAgentDraft={onAgentDraftChange} />;
    case "agent":
      return <AgentPage locale={locale} pendingDraft={agentDraft} onDraftHandled={() => onAgentDraftChange(null)} />;
    case "settings":
      return <SettingsPage locale={locale} onLocaleChange={onLocaleChange} />;
    case "today":
    default:
      return <TodayPage locale={locale} onNavigate={navigate} />;
  }
}
