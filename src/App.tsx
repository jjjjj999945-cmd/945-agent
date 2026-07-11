import { useState } from "react";
import { AppShell } from "./components/business/AppShell";
import { PrototypeRouter } from "./pages/PrototypeRouter";
import { TodayPage } from "./pages/TodayPage";
import type { Locale } from "./types/domain";

export function App() {
  const [locale, setLocale] = useState<Locale>("zh-CN");

  if (window.location.pathname.replace(/^\/+/, "") === "app") {
    return (
      <AppShell locale={locale} onLocaleChange={setLocale}>
        <TodayPage locale={locale} />
      </AppShell>
    );
  }

  return <PrototypeRouter />;
}
