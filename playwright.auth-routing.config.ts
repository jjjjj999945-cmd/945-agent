import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  testMatch: ["onboarding-auth-routing.spec.ts"],
  timeout: 30_000,
  use: {
    baseURL: "http://127.0.0.1:5178",
    channel: "chrome",
    headless: true
  },
  projects: [{ name: "chrome-auth-routing", use: { ...devices["Desktop Chrome"], channel: "chrome" } }],
  webServer: {
    command: "npx vite --host 127.0.0.1 --port 5178 --mode http",
    url: "http://127.0.0.1:5178/onboarding",
    env: {
      VITE_945_API_MODE: "http",
      VITE_945_AUTH_ENABLED: "true",
      VITE_945_REFERENCE_DATE: "2026-07-11"
    },
    reuseExistingServer: false,
    timeout: 60_000
  }
});
