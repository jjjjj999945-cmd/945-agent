import { expect, test } from "@playwright/test";

test("restores a signed-in HTTP session after a page reload", async ({ page }) => {
  const email = `session-${Date.now()}@example.com`;

  await page.goto("/");
  await page.getByRole("button", { name: "没有账号？创建账号" }).click();
  await page.getByLabel("昵称").fill("Session User");
  await page.getByLabel("邮箱").fill(email);
  await page.getByLabel("密码").fill("secure-pass-945");
  await page.getByRole("button", { name: "注册并开始" }).click();
  await expect(page.getByRole("heading", { name: "创建你的训练档案" })).toBeVisible();

  await page.reload();

  await expect(page.getByRole("heading", { name: "创建你的训练档案" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "登录 945" })).toHaveCount(0);
  await expect(page.evaluate(() => localStorage.getItem("945.auth.token"))).resolves.toBeNull();
});
