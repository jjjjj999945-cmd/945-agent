import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  testMatch: ["http-integration.spec.ts", "agent-workflow.spec.ts", "plan-lifecycle.spec.ts"],
  timeout: 30_000,
  expect: { timeout: 10_000 },
  workers: 1,
  use: {
    baseURL: "http://127.0.0.1:5177",
    channel: "chrome",
    headless: true,
    trace: "retain-on-failure"
  },
  projects: [
    {
      name: "chrome-desktop-http",
      use: { ...devices["Desktop Chrome"], channel: "chrome" }
    }
  ],
  webServer: [
    {
      command: "python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000",
      url: "http://127.0.0.1:8000/health",
      env: {
        "945_STORAGE_BACKEND": "demo",
        "945_LLM_PROVIDER": "deterministic",
        "945_APP_ENV": "development",
        "945_REFERENCE_DATE": "2026-07-11"
      },
      reuseExistingServer: false,
      timeout: 60_000
    },
    {
      command: "npm run dev:http",
      url: "http://127.0.0.1:5177/app",
      env: { "VITE_945_API_MODE": "http", "VITE_945_AUTH_ENABLED": "false", "VITE_945_REFERENCE_DATE": "2026-07-11" },
      reuseExistingServer: false,
      timeout: 60_000
    }
  ]
});
