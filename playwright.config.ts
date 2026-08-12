import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  testIgnore: ["http-integration.spec.ts", "agent-workflow.spec.ts", "plan-lifecycle.spec.ts"],
  timeout: 30_000,
  expect: {
    timeout: 10_000
  },
  use: {
    baseURL: "http://127.0.0.1:5173",
    channel: "chrome",
    headless: true,
    trace: "retain-on-failure"
  },
  projects: [
    {
      name: "chrome-desktop",
      use: {
        ...devices["Desktop Chrome"],
        channel: "chrome"
      }
    }
  ],
  webServer: {
    command: "npm run dev",
    url: "http://127.0.0.1:5173/app",
    reuseExistingServer: true,
    timeout: 60_000
  }
});
