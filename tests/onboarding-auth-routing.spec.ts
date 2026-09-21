import { expect, test } from "@playwright/test";

const authenticatedUser = {
  user_id: "user-onboarding-routing",
  display_name: "Routing Test",
  locale: "zh-CN",
  unit_system: "metric",
  created_at: "2026-07-11T00:00:00.000Z",
  updated_at: "2026-07-11T00:00:00.000Z"
};

test("sends onboarding profile changes to the signed-in user's profile path", async ({ page }) => {
  await page.route("**/api/auth/refresh", (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({
      data: { access_token: "test-access-token", session_id: "test-session", token_type: "bearer", user: authenticatedUser },
      error: null
    })
  }));
  await page.route("**/api/profile/**", (route) => route.abort());

  await page.goto("/onboarding");
  await expect(page.getByRole("heading", { name: "创建你的训练档案" })).toBeVisible();
  await page.getByLabel("我已了解健康与训练安全提示").check();

  const profileRequest = page.waitForRequest((request) => request.url().includes("/api/profile/") && request.method() === "PATCH");
  await page.getByRole("button", { name: "创建并启用我的计划" }).click();

  const request = await profileRequest;
  expect(request.url()).toBe("http://127.0.0.1:8000/api/profile/user-onboarding-routing");
  expect(JSON.parse(request.postData() ?? "{}")).toMatchObject({ safety_confirmed: true });
});

test("clicking the safety acknowledgement text enables plan creation", async ({ page }) => {
  await page.route("**/api/auth/refresh", (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({
      data: { access_token: "test-access-token", session_id: "test-session", token_type: "bearer", user: authenticatedUser },
      error: null
    })
  }));

  await page.goto("/onboarding");
  const safetyConfirmation = page.getByLabel("我已了解健康与训练安全提示");
  const createPlan = page.getByRole("button", { name: "创建并启用我的计划" });

  await expect(safetyConfirmation).not.toBeChecked();
  await expect(createPlan).toBeDisabled();
  await page.getByText("我已了解健康与训练安全提示", { exact: true }).click();
  await expect(safetyConfirmation).toBeChecked();
  await expect(createPlan).toBeEnabled();
});
