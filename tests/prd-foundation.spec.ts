import { expect, test } from "@playwright/test";

test.describe("PRD-driven frontend foundation", () => {
  test("renders primary product routes and keeps prototype references accessible", async ({ page }) => {
    const routes = [
      ["/", "早上好，Alex。"],
      ["/workout", "训练计划中心"],
      ["/diet", "饮食"],
      ["/body", "身体数据"],
      ["/advice", "建议"],
      ["/agent", "945 智能教练"],
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
    await page.getByRole("button", { name: "完成训练" }).click();
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
    await expect(page.getByRole("heading", { name: "确认智能教练草稿" })).toBeVisible();
    await page.getByRole("dialog").getByRole("button", { name: "确认" }).click();
    await expect(page.getByText("智能教练草稿已确认")).toBeVisible();

    await page.goto("/settings");
    await page.getByLabel("语言", { exact: true }).selectOption("en-US");
    await expect(page.getByRole("heading", { name: "Settings", exact: true })).toBeVisible();
  });

  test("gives visible feedback for previously static product actions", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "完成", exact: true }).click();
    await expect(page.getByText(/训练状态已更新/)).toBeVisible();
    await page.getByRole("button", { name: "查看原因" }).click();
    await expect(page.getByText("建议原因已展开在卡片内")).toBeVisible();
    await page.getByRole("button", { name: "调整今日计划" }).click();
    await expect(page.getByRole("heading", { name: "945 智能教练" })).toBeVisible();

    await page.goto("/plan");
    await page.getByRole("button", { name: "生成计划" }).click();
    await expect(page.getByText("已基于 demo 资料重新生成计划预览")).toBeVisible();
  });

  test("creates and activates a first plan from the onboarding profile", async ({ page }) => {
    await page.goto("/onboarding");
    await page.getByLabel("体重 kg").fill("68.5");
    await page.getByLabel("目标").selectOption("muscle_gain");
    await page.getByLabel("每周训练天数").fill("3");
    await page.getByLabel("gym").uncheck();
    await page.getByLabel("bodyweight").check();
    await page.getByRole("button", { name: "创建并启用我的计划" }).click();

    await expect(page).toHaveURL(/\/$/);
    await expect(page.getByRole("heading", { name: "早上好，Alex。" })).toBeVisible();
  });

  test("creates a plan adjustment draft from structured desktop controls", async ({ page }) => {
    await page.goto("/plan");
    await page.getByLabel("调整方式").selectOption("skip_workout");
    await page.getByLabel("调整原因").fill("恢复不足，需要跳过今天训练");
    await page.getByRole("button", { name: "生成调整草稿" }).click();

    await expect(page).toHaveURL(/\/agent$/);
    await expect(page.getByRole("heading", { name: "确认智能教练草稿" })).toBeVisible();
    await expect(page.getByRole("dialog").getByText("调整类型: skip_workout")).toBeVisible();
    await page.getByRole("dialog").getByRole("button", { name: "取消" }).click();
  });

  test("exposes desktop client semantics for agent, workout, and settings", async ({ page }) => {
    await page.goto("/agent");
    await expect(page.getByRole("heading", { name: "945 智能教练", exact: true })).toBeVisible();

    await page.goto("/workout");
    await expect(page.getByRole("heading", { name: "训练计划中心", exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { name: "本周训练计划", exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { name: "最近训练记录", exact: true })).toBeVisible();
    await expect(page.getByText("本周完成率")).toBeVisible();
    await expect(page.getByText("训练量摘要")).toBeVisible();

    await page.goto("/settings");
    await page.getByRole("button", { name: "增肌" }).click();
    await expect(page.getByText("设置已保存：训练目标已切换为增肌")).toBeVisible();
    await page.getByLabel("公制单位").click();
    await expect(page.getByText("设置已保存：单位偏好已更新")).toBeVisible();
    await page.getByLabel("推送通知").click();
    await expect(page.getByText("设置已保存：通知偏好已更新")).toBeVisible();
    await page.getByLabel("严格督促").click();
    await expect(page.getByText("设置已保存：教练语气已切换为严格督促")).toBeVisible();
  });

  test("saves personalization profile settings and generates a plan preview", async ({ page }) => {
    await page.goto("/settings");
    await page.getByLabel("每周训练天数").fill("3");
    await page.getByLabel("哑铃").uncheck();
    await page.getByLabel("素食").check();
    await page.getByLabel("乳制品").check();
    await page.getByRole("button", { name: "保存并生成计划预览" }).click();

    await expect(page.getByText("资料已保存，计划预览已生成。")).toBeVisible();
    await expect(page.getByText("计划预览", { exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { name: "训练安排" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "饮食安排" })).toBeVisible();
    await expect(page.getByRole("button", { name: "接受此计划" })).toBeVisible();
  });

});
