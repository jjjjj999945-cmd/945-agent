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

  test("persists page mutations through FastAPI", async ({ page, request }) => {
    await page.goto("/app");

    const mealLogsBefore = await (await request.get(`${API_BASE_URL}/api/meal-logs?user_id=demo-user-945`)).json();
    await page.getByRole("button", { name: "确认" }).first().click();
    await expect(page.getByText("早餐 已保存")).toBeVisible();
    const mealLogsAfter = await (await request.get(`${API_BASE_URL}/api/meal-logs?user_id=demo-user-945`)).json();
    expect(mealLogsAfter.data).toHaveLength(mealLogsBefore.data.length + 1);

    await page.getByLabel("体重 kg").fill("75.4");
    await page.getByLabel("睡眠小时").fill("7.5");
    await page.getByRole("button", { name: "保存", exact: true }).click();
    const today = await (await request.get(`${API_BASE_URL}/api/today?user_id=demo-user-945&date=2026-07-11`)).json();
    expect(today.data.daily_checkin).toMatchObject({ weight_kg: 75.4, sleep_hours: 7.5 });

    await page.goto("/body");
    await page.getByLabel("体重 kg").fill("74.9");
    await page.getByRole("button", { name: "保存身体数据" }).click();
    const metrics = await (await request.get(`${API_BASE_URL}/api/body-metrics?user_id=demo-user-945`)).json();
    expect(metrics.data.at(-1)).toMatchObject({ weight_kg: 74.9, date: "2026-07-11" });

    await page.goto("/workout");
    const workoutLogsBefore = await (await request.get(`${API_BASE_URL}/api/workout-logs?user_id=demo-user-945`)).json();
    await page.getByRole("button", { name: "完成训练" }).click();
    await expect(page.getByText("训练记录已保存")).toBeVisible();
    const workoutLogsAfter = await (await request.get(`${API_BASE_URL}/api/workout-logs?user_id=demo-user-945`)).json();
    expect(workoutLogsAfter.data).toHaveLength(workoutLogsBefore.data.length + 1);
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
