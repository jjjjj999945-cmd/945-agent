import { expect, test } from "@playwright/test";
import { resolveAppToday } from "../src/services/dateContext";
import { getMockDietPageData, getMockWorkoutPageData } from "../src/services/mockPlanLifecycle";
import type { CurrentPlanData } from "../src/types/domain";

test("keeps an expired-plan user in the coach workspace with a plan creation entry", async ({ page }) => {
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

  await expect(page.getByRole("heading", { name: "945 \u667a\u80fd\u6559\u7ec3" })).toBeVisible();
  await expect(page.getByText("\u5f53\u524d\u6ca1\u6709\u53ef\u6267\u884c\u7684\u8bad\u7ec3\u4e0e\u996e\u98df\u8ba1\u5212")).toBeVisible();
  await expect(page.getByRole("button", { name: "\u5f00\u59cb\u521b\u5efa\u8ba1\u5212" })).toBeVisible();

  await page.getByRole("button", { name: "\u5f00\u59cb\u521b\u5efa\u8ba1\u5212" }).click();
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
  await expect(page.getByRole("heading", { name: "945 \u667a\u80fd\u6559\u7ec3" })).toBeVisible();
  expect(expiredPlanRequests).toBeGreaterThan(0);

  serveExpiredPlan = false;
  await page.getByRole("button", { name: "\u5f00\u59cb\u521b\u5efa\u8ba1\u5212" }).click();
  await expect(page).toHaveURL(/\/onboarding$/);

  await page.locator('button[type="submit"]').click();
  await expect(page).toHaveURL("/");
  await expect(page.getByRole("heading", { name: "945 \u667a\u80fd\u6559\u7ec3" })).toBeVisible();
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
