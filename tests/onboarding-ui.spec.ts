import { expect, test } from "@playwright/test";

test("renders localized and horizontally aligned onboarding choices", async ({ page }) => {
  await page.goto("/onboarding");

  await expect(page.getByLabel("健身房")).toBeVisible();
  await expect(page.getByLabel("高蛋白")).toBeVisible();
  await expect(page.getByLabel("工作日繁忙")).toBeVisible();
  await expect(page.getByText("high_protein", { exact: true })).toHaveCount(0);

  const scheduleChoice = page.getByText("工作日繁忙", { exact: true }).locator("..");
  const box = await scheduleChoice.boundingBox();
  expect(box?.width).toBeGreaterThan(90);
});

test("toggles onboarding equipment choices", async ({ page }) => {
  await page.goto("/onboarding");

  const gym = page.getByLabel("健身房");
  await expect(gym).toBeChecked();
  await gym.uncheck();
  await expect(gym).not.toBeChecked();
  await gym.check();
  await expect(gym).toBeChecked();

  await expect(gym).toHaveCSS("accent-color", "rgb(142, 170, 221)");
});
