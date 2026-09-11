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
  const send = page.getByRole("button", { name: "发送" }).click();
  const requestStatus = page.locator(".agent-status-panel").getByRole("status").filter({ hasText: "本次请求" });

  await expect(requestStatus).toContainText("正在读取当前上下文并生成建议");
  await expect(requestStatus).toContainText("分析中");
  await send;
  await expect(page.getByText("我已整理好你的训练建议。")).toBeVisible();
  await expect(page.locator(".agent-status-panel").getByRole("status").filter({ hasText: "教练状态" })).toContainText("在线");
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

test("takes an active-plan user from the coach workspace to today's execution page", async ({ page }) => {
  await page.goto("/");

  await page.getByRole("button", { name: "查看今日执行" }).click();
  await expect(page).toHaveURL("/today");
});

test("manually resumes an interrupted run exactly once", async ({ page }) => {
  let status: "interrupted" | "completed" = "interrupted";
  let resumeCalls = 0;
  let markResumeRequested = () => {};
  const resumeRequested = new Promise<void>((resolve) => {
    markResumeRequested = resolve;
  });
  let releaseResumeResponse = () => {};
  const resumeResponseReleased = new Promise<void>((resolve) => {
    releaseResumeResponse = resolve;
  });
  await page.route("**/api/agent/runs?*", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        data: [{
          agent_run_id: "run-interrupted",
          user_id: "demo-user-945",
          status,
          started_at: "2026-07-11T09:00:00Z",
          updated_at: "2026-07-11T09:00:01Z",
          completed_at: status === "completed" ? "2026-07-11T09:00:02Z" : null,
          duration_ms: 1000,
          degraded: false,
          input_tokens: 0,
          output_tokens: 0,
          logical_generations: 0,
          http_attempts: 0,
          resume_count: status === "completed" ? 1 : 0
        }],
        error: null
      })
    })
  );
  await page.route("**/api/agent/runs/run-interrupted/resume", async (route) => {
    resumeCalls += 1;
    markResumeRequested();
    await resumeResponseReleased;
    status = "completed";
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        data: {
          message_id: "msg-agent-run-interrupted",
          user_id: "demo-user-945",
          role: "agent",
          content: "恢复后的回复",
          locale: "zh-CN",
          created_at: "2026-07-11T09:00:02Z"
        },
        error: null
      })
    });
  });

  await page.goto("/agent");
  const requestStatus = page.getByRole("status").filter({ hasText: "本次请求" });
  const resume = page.getByRole("button", { name: "继续任务" });
  await expect(requestStatus).toContainText("任务中断");
  const click = resume.click();
  await resumeRequested;
  await expect(page.getByRole("button", { name: "恢复中" })).toBeDisabled();
  releaseResumeResponse();
  await click;
  await expect(page.getByText("恢复后的回复")).toBeVisible();
  await expect(requestStatus).toContainText("已完成");
  expect(resumeCalls).toBe(1);
});

test("polls a running request until completion and restores only its new draft", async ({ page }) => {
  let runReads = 0;
  let completed = false;
  await page.route("**/api/agent/runs?*", async (route) => {
    runReads += 1;
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        data: [{
          agent_run_id: "run-polling",
          user_id: "demo-user-945",
          status: completed ? "completed" : "running",
          started_at: "2026-07-11T09:00:00Z",
          updated_at: "2026-07-11T09:00:02Z",
          completed_at: completed ? "2026-07-11T09:00:02Z" : null,
          duration_ms: completed ? 2000 : 0,
          degraded: false,
          input_tokens: 0,
          output_tokens: 0,
          logical_generations: completed ? 1 : 0,
          http_attempts: 0,
          resume_count: 0
        }],
        error: null
      })
    });
  });
  await page.route("**/api/agent/messages?*", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        data: completed ? [{
          message_id: "msg-agent-run-polling",
          user_id: "demo-user-945",
          role: "agent",
          content: "轮询完成",
          locale: "zh-CN",
          record_draft: {
            type: "workout_log",
            requires_confirmation: true,
            payload: { exercise_name: "深蹲", sets: 4, reps: 8 }
          },
          created_at: "2026-07-11T09:00:02Z"
        }] : [],
        error: null
      })
    })
  );

  await page.clock.install();
  await page.goto("/agent");
  const requestStatus = page.getByRole("status").filter({ hasText: "本次请求" });
  await expect(requestStatus).toContainText("执行中");
  completed = true;
  await page.clock.fastForward(2000);
  await expect(requestStatus).toContainText("已完成", { timeout: 5000 });
  await expect(page.getByText("轮询完成")).toBeVisible();
  await expect(page.getByRole("heading", { name: "确认智能教练草稿" })).toBeVisible();
  const completedReadCount = runReads;
  await page.clock.fastForward(2300);
  expect(runReads).toBe(completedReadCount);
});

test("shows a resume error and moves a missing checkpoint to retry", async ({ page }) => {
  let status: "interrupted" | "failed" = "interrupted";
  await page.route("**/api/agent/runs?*", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        data: [{
          agent_run_id: "run-resume-error",
          user_id: "demo-user-945",
          status,
          started_at: "2026-07-11T09:00:00Z",
          updated_at: "2026-07-11T09:00:01Z",
          duration_ms: 0,
          degraded: false,
          input_tokens: 0,
          output_tokens: 0,
          logical_generations: 0,
          http_attempts: 0,
          resume_count: 0
        }],
        error: null
      })
    })
  );
  await page.route("**/api/agent/runs/run-resume-error/resume", (route) => {
    status = "failed";
    return route.fulfill({
      status: 409,
      contentType: "application/json",
      body: JSON.stringify({
        data: null,
        error: {
          code: "AGENT_CHECKPOINT_MISSING",
          message: "Agent checkpoint is missing.",
          details: { agent_run_id: "run-resume-error" }
        }
      })
    });
  });

  await page.goto("/agent");
  await page.getByRole("button", { name: "继续任务" }).click();

  await expect(page.getByText("Agent checkpoint is missing.")).toBeVisible();
  await expect(page.getByRole("button", { name: "重试此请求" })).toBeVisible();
});
