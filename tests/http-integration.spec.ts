import { expect, test } from "@playwright/test";

const API_BASE_URL = "http://127.0.0.1:8000";

test.describe.serial("945 real HTTP integration", () => {
  test.beforeEach(({}, testInfo) => {
    test.skip(testInfo.project.name !== "chrome-desktop-http", "requires the HTTP Playwright project");
  });

  test("loads the Today page through FastAPI", async ({ page, request }) => {
    const health = await request.get(`${API_BASE_URL}/health`);
    expect(health.ok()).toBeTruthy();
    const healthBody = await health.json();
    expect(healthBody).toMatchObject({
      data: { status: "ok", service: "945-backend" },
      error: null
    });

    const todayResponse = page.waitForResponse(
      (response) => response.url().includes("/api/today") && response.request().method() === "GET"
    );
    await page.goto("/app");
    await expect(page.getByRole("heading", { name: "早上好，Alex。" })).toBeVisible();
    expect((await todayResponse).status()).toBe(200);
  });

  test("shows normalized validation errors", async ({ page }) => {
    await page.route("**/api/today?*", (route) =>
      route.fulfill({
        status: 422,
        contentType: "application/json",
        body: JSON.stringify({ detail: [{ loc: ["query", "date"], msg: "Invalid date", type: "value_error" }] })
      })
    );
    await page.goto("/app");
    await expect(page.getByRole("status")).toContainText("Request validation failed.");
  });

  test("shows protocol errors for malformed 422 responses", async ({ page }) => {
    await page.route("**/api/today?*", (route) =>
      route.fulfill({ status: 422, contentType: "application/json", body: "null" })
    );
    await page.goto("/app");
    await expect(page.getByRole("status")).toContainText("945 backend returned an invalid response.");
  });

  test("shows protocol errors for non-JSON responses", async ({ page }) => {
    await page.route("**/api/today?*", (route) =>
      route.fulfill({ status: 502, contentType: "text/html", body: "Bad gateway" })
    );
    await page.goto("/app");
    await expect(page.getByRole("status")).toContainText("945 backend returned an invalid response.");
  });

  test("shows network errors when the API request is aborted", async ({ page }) => {
    await page.route("**/api/today?*", (route) => route.abort("failed"));
    await page.goto("/app");
    await expect(page.getByRole("status")).toContainText("Unable to reach 945 backend.");
  });
});
