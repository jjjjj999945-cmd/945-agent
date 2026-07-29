import { expect, test } from "@playwright/test";

test("shows an observable coach status while an agent request is running", async ({ page }) => {
  await page.route("**/api/agent/chat", async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 400));
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        data: {
          message_id: "agent-workflow-test",
          user_id: "demo-user-945",
          role: "agent",
          content: "我已整理好你的训练建议。",
          locale: "zh-CN",
          created_at: "2026-07-26T09:00:00Z"
        },
        error: null
      })
    });
  });

  await page.goto("/");
  const input = page.getByPlaceholder(/深蹲/);
  await input.fill("今天想调整训练强度");
  await page.getByRole("button", { name: "发送" }).click();

  await expect(page.getByRole("status")).toContainText("正在读取当前上下文并生成建议");
  await expect(page.getByRole("status")).toContainText("分析中");
  await expect(page.getByText("我已整理好你的训练建议。")).toBeVisible();
  await expect(page.getByRole("status")).toContainText("在线");
});

test("opens the profile setup form inside the coach workspace", async ({ page }) => {
  await page.route("**/api/plans/current?*", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ data: { plan: null, coverage_status: "expired" }, error: null })
    })
  );

  await page.goto("/");
  await page.getByRole("button", { name: "开始创建计划" }).click();

  await expect(page).toHaveURL("/");
  await expect(page.getByRole("heading", { name: "身体与目标" })).toBeVisible();
});

test("refreshes the shared plan state after confirming an agent plan adjustment", async ({ page }) => {
  let adjustmentConfirmed = false;
  await page.route("**/api/plans/current?*", (route) => {
    if (!adjustmentConfirmed) return route.continue();
    return route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ data: { plan: null, coverage_status: "none" }, error: null })
    });
  });
  await page.route("**/api/plans/*/adjust", async (route) => {
    adjustmentConfirmed = true;
    await route.continue();
  });
  await page.route("**/api/agent/chat", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        data: {
          message_id: "plan-adjustment-test",
          user_id: "demo-user-945",
          role: "agent",
          content: "请确认计划调整。",
          locale: "zh-CN",
          record_draft: {
            type: "plan_adjustment",
            requires_confirmation: true,
            payload: { adjustment_type: "reduce_intensity", reason: "恢复不足", target_date: "2026-07-26" }
          },
          created_at: "2026-07-26T09:00:00Z"
        },
        error: null
      })
    })
  );

  await page.goto("/");
  await page.getByPlaceholder(/深蹲/).fill("今天太累了，帮我调整计划");
  await page.getByRole("button", { name: "发送" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "确认" }).click();

  await expect(page.getByText("当前没有可执行的训练与饮食计划")).toBeVisible();
});
