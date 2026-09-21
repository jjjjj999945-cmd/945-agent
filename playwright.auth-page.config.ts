import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  testMatch: ["auth-page.spec.ts"],
  timeout: 30_000,
  use: {
    baseURL: "http://127.0.0.1:5177",
    channel: "chrome",
    headless: true
  },
  projects: [{ name: "chrome-auth-page", use: { ...devices["Desktop Chrome"], channel: "chrome" } }]
});
