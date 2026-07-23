import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  testMatch: "http-integration.spec.ts",
  timeout: 30_000,
  expect: { timeout: 10_000 },
  workers: 1,
  use: { baseURL: "http://127.0.0.1:5177", channel: "chrome", headless: true, trace: "retain-on-failure" },
  projects: [{ name: "chrome-desktop-http", use: { ...devices["Desktop Chrome"], channel: "chrome" } }],
  webServer: [
    {
      command: "python backend/scripts/reset_mongo_database.py && python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000",
      url: "http://127.0.0.1:8000/health",
      env: {
        "945_STORAGE_BACKEND": "mongo",
        "945_MONGODB_URI": "mongodb://127.0.0.1:27017",
        "945_MONGODB_DATABASE": "945_mongo_qa",
        "945_LLM_PROVIDER": "deterministic",
        "945_APP_ENV": "development"
      },
      reuseExistingServer: false,
      timeout: 60_000
    },
    {
      command: "npm run dev:http",
      url: "http://127.0.0.1:5177/app",
      env: { "VITE_945_AUTH_ENABLED": "false" },
      reuseExistingServer: false,
      timeout: 60_000
    }
  ]
});
