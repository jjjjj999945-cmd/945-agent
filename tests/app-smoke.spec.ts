import { expect, test } from "@playwright/test";

test.describe("945 business Today page smoke QA", () => {
  test("keeps the desktop workbench in the grid column beside the fixed navigation", async ({ page }) => {
    await page.setViewportSize({ width: 1200, height: 900 });
    await page.goto("/today");

    const layout = await page.evaluate(() => {
      const shell = document.querySelector<HTMLElement>(".business-shell")!;
      const sidebar = document.querySelector<HTMLElement>(".business-sidebar")!;
      const workbench = document.querySelector<HTMLElement>(".business-workbench")!;

      return {
        shell: shell.getBoundingClientRect(),
        sidebar: sidebar.getBoundingClientRect(),
        workbench: workbench.getBoundingClientRect()
      };
    });

    expect(layout.sidebar.width).toBe(72);
    expect(layout.workbench.x).toBe(layout.sidebar.width);
    expect(layout.workbench.width).toBe(layout.shell.width - layout.sidebar.width);
  });

  test("verifies meal confirmation, daily check-in, and language switching", async ({ page }) => {
    await page.goto("/today");

    await expect(page.getByRole("heading", { name: "你好，Alex。" })).toBeVisible();
    await expect(page.getByText("1480 / 2300")).toBeVisible();

    const firstMealConfirm = page.getByRole("button", { name: "确认" }).first();
    await firstMealConfirm.click();
    await expect(page.getByText("早餐 已保存")).toBeVisible();

    await firstMealConfirm.click();
    await firstMealConfirm.click();
    await firstMealConfirm.click();
    await expect(page.getByText("1548 / 2300")).toBeVisible();

    await page.getByLabel("体重 kg").fill("75.4");
    await page.getByLabel("睡眠小时").fill("7.5");
    await page.getByRole("button", { name: "保存" }).click();
    await expect(page.getByText("已保存").first()).toBeVisible();

    await page.getByRole("combobox").first().selectOption("en-US");
    await expect(page.getByRole("button", { name: "Today", exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "Save" })).toBeVisible();
  });

  test("keeps the Today page focused on execution while the coach owns chat", async ({ page }) => {
    await page.goto("/today");
    await expect(page.locator(".agent-mini-input")).toHaveCount(0);
    await page.getByRole("button", { name: "智能教练" }).click();
    await expect(page).toHaveURL(/\/$/);
    await expect(page.getByRole("heading", { name: "945 智能教练" })).toBeVisible();
  });

  test("focuses manual meal entry from the Diet-page add action", async ({ page }) => {
    await page.goto("/diet");
    const mealInput = page.getByLabel("餐食名称");
    await page.getByRole("button", { name: "+ 添加餐食" }).click();
    await expect(mealInput).toBeFocused();
  });

  test("uses API data rather than fixed coach and diet suggestions", async ({ page }) => {
    await page.goto("/today");
    await expect(page.getByText("-18%")).toHaveCount(0);
    await expect(page.getByText("强度 7")).toHaveCount(0);

    await page.goto("/diet");
    await expect(page.getByText("智能饮食调整")).toHaveCount(0);
    await expect(page.getByText("采购清单")).toHaveCount(0);
  });

  test("gives the brand and Agent shortcut separate navigation roles", async ({ page }) => {
    await page.goto("/");
    await page.getByLabel("945 今日工作台").click();
    await expect(page).toHaveURL(/\/today$/);

    await page.getByRole("button", { name: "同步教练" }).click();
    await expect(page).toHaveURL(/\/$/);
    await expect(page.getByRole("heading", { name: "945 智能教练" })).toBeVisible();
  });
});
