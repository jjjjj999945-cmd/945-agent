import { expect, test } from "@playwright/test";

test.describe("PRD-driven frontend foundation", () => {
  test("renders primary product routes and keeps prototype references accessible", async ({ page }) => {
    const routes = [
      ["/", "Good morning, Alex."],
      ["/workout", "Upper Body Power"],
      ["/diet", "饮食"],
      ["/body", "身体数据"],
      ["/advice", "建议"],
      ["/agent", "Recovery Ride"],
      ["/settings", "设置"]
    ] as const;

    for (const [path, heading] of routes) {
      await page.goto(path);
      await expect(page.getByRole("heading", { name: heading, exact: true })).toBeVisible();
    }

    await page.goto("/prototype");
    await expect(page.getByText("Stitch reference").first()).toBeVisible();

    await page.goto("/prototype/diet");
    await expect(page.getByText("Stitch reference: Diet Tracker v2")).toBeVisible();
  });

  test("supports core mock interactions across product pages", async ({ page }) => {
    await page.goto("/workout");
    await page.getByRole("button", { name: "Finish" }).click();
    await expect(page.getByText("训练记录已保存")).toBeVisible();

    await page.goto("/diet");
    await page.getByRole("button", { name: "确认计划餐" }).first().click();
    await expect(page.getByText("计划餐已确认")).toBeVisible();
    await page.getByLabel("手动餐食名称").fill("鸡胸肉沙拉");
    await page.getByRole("button", { name: "保存手动餐食" }).click();
    await expect(page.getByText("手动餐食已保存")).toBeVisible();

    await page.goto("/body");
    await page.getByLabel("体重 kg").fill("75.2");
    await page.getByRole("button", { name: "保存身体数据" }).click();
    await expect(page.getByText("身体数据已保存")).toBeVisible();

    await page.goto("/advice");
    await page.getByRole("button", { name: "采纳" }).first().click();
    await expect(page.getByText("建议状态已更新")).toBeVisible();
    await page.getByRole("button", { name: "忽略" }).first().click();
    await expect(page.getByText("建议状态已更新")).toBeVisible();

    await page.goto("/agent");
    await page.getByPlaceholder("今天深蹲做了 4 组，每组 8 次，80kg，感觉很累。").fill("今天深蹲做了 4 组，每组 8 次，80kg。");
    await page.getByRole("button", { name: "发送" }).click();
    await expect(page.getByRole("heading", { name: "确认 Agent 草稿" })).toBeVisible();
    await page.getByRole("dialog").getByRole("button", { name: "确认" }).click();
    await expect(page.getByText("Agent 草稿已确认")).toBeVisible();

    await page.goto("/settings");
    await page.getByLabel("settings language").selectOption("en-US");
    await expect(page.getByRole("heading", { name: "Settings", exact: true })).toBeVisible();
  });

  test("gives visible feedback for previously static product actions", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "完成", exact: true }).click();
    await expect(page.getByText(/训练状态已更新/)).toBeVisible();
    await page.getByRole("button", { name: "查看原因" }).click();
    await expect(page.getByText("建议原因已展开在卡片内")).toBeVisible();
    await page.getByRole("button", { name: "调整今日计划" }).click();
    await expect(page.getByText("Plan Draft")).toBeVisible();

    await page.goto("/plan");
    await page.getByRole("button", { name: "生成计划" }).click();
    await expect(page.getByText("已基于 demo 资料重新生成计划预览")).toBeVisible();
  });
});
