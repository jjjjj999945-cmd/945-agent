import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  testMatch: ["auth-session.spec.ts"],
  timeout: 60_000,
  retries: 1,
  expect: { timeout: 10_000 },
  workers: 1,
  use: {
    baseURL: "http://127.0.0.1:5177",
    channel: "chrome",
    headless: true,
    trace: "retain-on-failure"
  },
  projects: [{ name: "chrome-desktop-auth", use: { ...devices["Desktop Chrome"], channel: "chrome" } }],
  webServer: [
    {
      command: "python backend/scripts/run_http_qa_server.py",
      url: "http://127.0.0.1:8000/health",
      reuseExistingServer: false,
      timeout: 60_000
    },
    {
      command: "vite --host 127.0.0.1 --port 5177 --mode http",
      url: "http://127.0.0.1:5177/app",
      env: {
        VITE_945_API_MODE: "http",
        VITE_945_AUTH_ENABLED: "true",
        VITE_945_REFERENCE_DATE: "2026-07-11"
      },
      reuseExistingServer: false,
      timeout: 60_000
    }
  ]
});
