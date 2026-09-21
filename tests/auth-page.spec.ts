import { expect, test } from "@playwright/test";

test("uses the 945 workbench visual surface for unauthenticated entry", async ({ page }) => {
  await page.route("**/api/auth/refresh", (route) => route.fulfill({
    status: 401,
    contentType: "application/json",
    body: JSON.stringify({ data: null, error: { code: "UNAUTHORIZED", message: "expired", details: {} } })
  }));
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "登录 945" })).toBeVisible();
  await expect(page.getByLabel("邮箱")).toBeVisible();
  await expect(page.getByLabel("密码")).toBeVisible();

  await expect(page.locator(".auth-page")).toHaveCSS("background-color", "rgb(13, 18, 27)");
  await expect(page.locator(".auth-panel")).toHaveCSS("backdrop-filter", /blur/);
});
