import { expect, test } from "@playwright/test";

test.describe("945 business Today page smoke QA", () => {
  test("verifies meal confirmation, daily check-in, Agent draft confirmation, and language switching", async ({ page }) => {
    await page.goto("/app");

    await expect(page.getByRole("heading", { name: "早上好，Alex。" })).toBeVisible();
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

    await page
      .getByPlaceholder("今天深蹲做了 4 组，每组 8 次，80kg，感觉很累。")
      .fill("今天深蹲做了 4 组，每组 8 次，80kg，感觉很累。");
    await page.getByRole("button", { name: "发送" }).click();
    await expect(page.getByRole("heading", { name: "确认智能教练草稿" })).toBeVisible();
    await expect(page.getByText("动作名称: 深蹲")).toBeVisible();
    await page.getByRole("dialog").getByRole("button", { name: "确认" }).click();
    await expect(page.getByRole("heading", { name: "确认智能教练草稿" })).toBeHidden();

    await page.getByRole("combobox").first().selectOption("en-US");
    await expect(page.getByRole("button", { name: "Today", exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "Save" })).toBeVisible();
  });
});
