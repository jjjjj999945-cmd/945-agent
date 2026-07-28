import { expect, test } from "@playwright/test";

test("routes an expired-plan user to a clear renewal state", async ({ page }) => {
  await page.route("**/api/plans/current?*", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        data: { plan: null, coverage_status: "expired" },
        error: null
      })
    })
  );

  await page.goto("/");

  await expect(page.getByRole("heading", { name: "当前计划没有覆盖今天" })).toBeVisible();
  await expect(page.getByRole("button", { name: "开始创建计划" })).toBeVisible();

  await page.getByRole("button", { name: "开始创建计划" }).click();
  await expect(page).toHaveURL(/\/onboarding$/);
});
