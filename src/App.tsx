import { useState } from "react";
import { AppShell } from "./components/business/AppShell";
import { PrototypeRouter } from "./pages/PrototypeRouter";
import type { Locale } from "./types/domain";

export function App() {
  const [locale, setLocale] = useState<Locale>("zh-CN");

  if (window.location.pathname.replace(/^\/+/, "") === "app") {
    return (
      <AppShell locale={locale} onLocaleChange={setLocale}>
        <div className="business-placeholder">
          <h1>945 MVP App</h1>
          <p>Business-backed Today page will be implemented in the next task.</p>
          <a href="/">Open Stitch prototype</a>
        </div>
      </AppShell>
    );
  }

  return <PrototypeRouter />;
}
