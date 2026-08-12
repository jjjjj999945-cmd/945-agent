import { expect, test } from "@playwright/test";

const API_BASE_URL = "http://127.0.0.1:8000";
const userId = "demo-user-945";

test.describe("945 real HTTP integration", () => {
  test("loads Today data from FastAPI", async ({ page, request }) => {
    const health = await request.get(`${API_BASE_URL}/health`);
    expect(health.ok()).toBeTruthy();

    const todayRequest = page.waitForResponse((response) => response.url().includes("/api/today") && response.ok());
    await page.goto("/app");
    await todayRequest;
    await expect(page.getByRole("heading", { name: "早上好，Alex。" })).toBeVisible();
  });

  test("persists page mutations through FastAPI", async ({ page, request }) => {
    await page.goto("/app");
    const mealsBefore = await (await request.get(`${API_BASE_URL}/api/meal-logs?user_id=${userId}`)).json();
    await page.getByRole("button", { name: "确认" }).first().click();
    await expect(page.getByText("早餐 已保存")).toBeVisible();
    const mealsAfter = await (await request.get(`${API_BASE_URL}/api/meal-logs?user_id=${userId}`)).json();
    expect(mealsAfter.data).toHaveLength(mealsBefore.data.length + 1);

    await page.getByLabel("体重 kg").fill("75.4");
    await page.getByLabel("睡眠小时").fill("7.5");
    await page.getByRole("button", { name: "保存", exact: true }).click();
    await expect(page.getByText("已保存").first()).toBeVisible();
    const today = await (await request.get(`${API_BASE_URL}/api/today?user_id=${userId}&date=2026-07-11`)).json();
    expect(today.data.daily_checkin).toMatchObject({ weight_kg: 75.4, sleep_hours: 7.5 });

    await page.goto("/body");
    await page.getByLabel("体重 kg").fill("74.9");
    await page.getByRole("button", { name: "保存身体数据" }).click();
    await expect(page.getByText("身体数据已保存")).toBeVisible();
    const metrics = await (await request.get(`${API_BASE_URL}/api/body-metrics?user_id=${userId}`)).json();
    expect(metrics.data.at(-1)).toMatchObject({ weight_kg: 74.9, date: "2026-07-11" });
  });

  test("writes Agent workout drafts only after confirmation", async ({ page, request }) => {
    const before = await (await request.get(`${API_BASE_URL}/api/workout-logs?user_id=${userId}`)).json();
    await page.goto("/agent");
    await page.getByPlaceholder("今天深蹲做了 4 组，每组 8 次，80kg，感觉很累。").fill("今天深蹲做了 4 组，每组 8 次，80kg，感觉很累。");
    await page.getByRole("button", { name: "发送" }).click();
    await expect(page.getByRole("heading", { name: "确认智能教练草稿" })).toBeVisible();
    const beforeConfirmation = await (await request.get(`${API_BASE_URL}/api/workout-logs?user_id=${userId}`)).json();
    expect(beforeConfirmation.data).toHaveLength(before.data.length);

    await page.getByRole("dialog").getByRole("button", { name: "确认" }).click();
    await expect(page.getByText("智能教练草稿已确认")).toBeVisible();
    const after = await (await request.get(`${API_BASE_URL}/api/workout-logs?user_id=${userId}`)).json();
    expect(after.data).toHaveLength(before.data.length + 1);
  });

  test("shows a visible network failure", async ({ page }) => {
    await page.route("**/api/today?*", (route) => route.abort("failed"));
    await page.goto("/app");
    await expect(page.getByRole("status")).toContainText("Unable to reach 945 backend.");
  });
});
