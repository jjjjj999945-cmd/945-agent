import { expect, test } from "@playwright/test";

async function registerThroughAuthPage(page: import("@playwright/test").Page) {
  const email = `session-${Date.now()}@example.com`;
  const password = "secure-pass-945";

  await page.goto("/");
  await page.getByRole("button", { name: "没有账号？创建账号" }).click();
  await page.getByLabel("昵称").fill("Session User");
  await page.getByLabel("邮箱").fill(email);
  await page.getByLabel("密码").fill(password);
  await page.getByRole("button", { name: "注册并开始" }).click();
  await expect(page.getByRole("heading", { name: "创建你的训练档案" })).toBeVisible();
  return { email, password };
}

test("restores a signed-in HTTP session after a page reload", async ({ page }) => {
  await registerThroughAuthPage(page);

  await page.reload();

  await expect(page.getByRole("heading", { name: "创建你的训练档案" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "登录 945" })).toHaveCount(0);
  await expect(page.evaluate(() => localStorage.getItem("945.auth.token"))).resolves.toBeNull();
});

test("refreshes once and retries a protected request", async ({ page }) => {
  await registerThroughAuthPage(page);
  let refreshRequests = 0;
  page.on("request", (request) => {
    if (request.url().endsWith("/api/auth/refresh")) refreshRequests += 1;
  });
  await page.route("**/api/plans/current?*", async (route) => {
    await route.fulfill({
      status: 401,
      contentType: "application/json",
      headers: {
        "Access-Control-Allow-Origin": "http://127.0.0.1:5177",
        "Access-Control-Allow-Credentials": "true"
      },
      body: JSON.stringify({ data: null, error: { code: "UNAUTHORIZED", message: "expired", details: {} } })
    });
  }, { times: 1 });

  await page.goto("/today");

  await expect(page.getByRole("heading", { name: "登录 945" })).toHaveCount(0);
  await expect.poll(() => refreshRequests).toBe(2);
});

test("returns to login when retry is unauthorized", async ({ page }) => {
  await registerThroughAuthPage(page);
  let refreshRequests = 0;
  await page.route("**/api/auth/refresh", async (route) => {
    refreshRequests += 1;
    if (refreshRequests === 1) {
      await route.continue();
      return;
    }
    await route.fulfill({
      status: 401,
      contentType: "application/json",
      headers: {
        "Access-Control-Allow-Origin": "http://127.0.0.1:5177",
        "Access-Control-Allow-Credentials": "true"
      },
      body: JSON.stringify({ data: null, error: { code: "UNAUTHORIZED", message: "expired", details: {} } })
    });
  });
  await page.route("**/api/plans/current?*", async (route) => {
    await route.fulfill({
      status: 401,
      contentType: "application/json",
      headers: {
        "Access-Control-Allow-Origin": "http://127.0.0.1:5177",
        "Access-Control-Allow-Credentials": "true"
      },
      body: JSON.stringify({ data: null, error: { code: "UNAUTHORIZED", message: "expired", details: {} } })
    });
  });

  await page.goto("/today");

  await expect(page.getByRole("heading", { name: "登录 945" })).toBeVisible();
  expect(refreshRequests).toBe(2);
});

test("shows and revokes another signed-in device", async ({ page, browser }) => {
  const credentials = await registerThroughAuthPage(page);
  const otherContext = await browser.newContext({ baseURL: "http://127.0.0.1:5177" });
  try {
    const otherPage = await otherContext.newPage();
    await otherPage.goto("/");
    await otherPage.getByLabel("邮箱").fill(credentials.email);
    await otherPage.getByLabel("密码").fill(credentials.password);
    await otherPage.getByRole("button", { name: "登录", exact: true }).click();
    await expect(otherPage.getByRole("heading", { name: "创建你的训练档案" })).toBeVisible();

    await page.goto("/settings");
    await expect(page.getByRole("button", { name: "退出此设备", exact: true })).toHaveCount(1);
    await page.getByRole("button", { name: "退出此设备", exact: true }).click();
    await expect(page.getByText("设备已退出。", { exact: true })).toBeVisible();

    await otherPage.reload();
    await expect(otherPage.getByRole("heading", { name: "登录 945" })).toBeVisible();
  } finally {
    await otherContext.close();
  }
});
