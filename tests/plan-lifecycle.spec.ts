import { expect, test } from "@playwright/test";
import { resolveAppToday } from "../src/services/dateContext";
import { getMockDietPageData, getMockWorkoutPageData } from "../src/services/mockPlanLifecycle";
import type { CurrentPlanData } from "../src/types/domain";

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

test("refreshes shared plan state after onboarding activates a plan", async ({ page }) => {
  let serveExpiredPlan = true;
  let expiredPlanRequests = 0;
  let refreshedPlanRequests = 0;

  await page.route("**/api/plans/current?*", async (route) => {
    if (serveExpiredPlan) {
      expiredPlanRequests += 1;
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({ data: { plan: null, coverage_status: "expired" }, error: null })
      });
      return;
    }
    refreshedPlanRequests += 1;
    await route.continue();
  });

  await page.goto("/");
  await expect(page.locator(".business-page .page-header h1")).toBeVisible();
  expect(expiredPlanRequests).toBeGreaterThan(0);

  serveExpiredPlan = false;
  await page.locator(".business-page .business-panel button").click();
  await expect(page).toHaveURL(/\/onboarding$/);

  await page.locator('button[type="submit"]').click();
  await expect(page).toHaveURL("/");
  await expect(page.locator(".today-page")).toBeVisible();
  await expect(page.locator(".business-page .page-header h1")).toHaveCount(0);
  expect(refreshedPlanRequests).toBeGreaterThan(0);
});

test("mock workout and diet data reject uncovered plans", () => {
  const uncoveredPlan: CurrentPlanData = { plan: null, coverage_status: "expired" };

  expect(getMockWorkoutPageData(uncoveredPlan)).toMatchObject({
    data: null,
    error: { code: "PLAN_UNAVAILABLE" }
  });
  expect(getMockDietPageData(uncoveredPlan)).toMatchObject({
    data: null,
    error: { code: "PLAN_UNAVAILABLE" }
  });
});

test("resolves the runtime date from the single reference-date source", () => {
  expect(resolveAppToday("2026-07-26", new Date("2030-01-01T00:00:00.000Z"))).toBe("2026-07-26");
  expect(resolveAppToday(undefined, new Date("2030-01-01T23:30:00.000Z"))).toBe("2030-01-01");
});
