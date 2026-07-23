import { expect, test } from "@playwright/test";

const API_BASE_URL = "http://127.0.0.1:8000";

test.describe.serial("945 real HTTP integration", () => {
  test.beforeEach(({}, testInfo) => {
    test.skip(testInfo.project.name !== "chrome-desktop-http", "requires the HTTP Playwright project");
  });

  test("loads the Today page through FastAPI", async ({ page, request }) => {
    const health = await request.get(`${API_BASE_URL}/health`);
    expect(health.ok()).toBeTruthy();
    const healthBody = await health.json();
    expect(healthBody).toMatchObject({
      data: { status: "ok", service: "945-backend" },
      error: null
    });

    const todayResponse = page.waitForResponse(
      (response) => response.url().includes("/api/today") && response.request().method() === "GET"
    );
    await page.goto("/app");
    await expect(page.getByRole("heading", { name: "早上好，Alex。" })).toBeVisible();
    expect((await todayResponse).status()).toBe(200);
  });

  test("persists page mutations through FastAPI", async ({ page, request }) => {
    await page.goto("/app");

    const mealLogsBefore = await (await request.get(`${API_BASE_URL}/api/meal-logs?user_id=demo-user-945`)).json();
    await page.getByRole("button", { name: "确认" }).first().click();
    await expect(page.getByText("早餐 已保存")).toBeVisible();
    const mealLogsAfter = await (await request.get(`${API_BASE_URL}/api/meal-logs?user_id=demo-user-945`)).json();
    expect(mealLogsAfter.data).toHaveLength(mealLogsBefore.data.length + 1);

    await page.getByLabel("体重 kg").fill("75.4");
    await page.getByLabel("睡眠小时").fill("7.5");
    const dailyCheckinResponse = page.waitForResponse(
      (response) =>
        response.url() === `${API_BASE_URL}/api/daily-checkins` &&
        response.request().method() === "POST" &&
        response.status() === 200
    );
    await page.getByRole("button", { name: "保存", exact: true }).click();
    await dailyCheckinResponse;
    const today = await (await request.get(`${API_BASE_URL}/api/today?user_id=demo-user-945&date=2026-07-11`)).json();
    expect(today.data.daily_checkin).toMatchObject({ weight_kg: 75.4, sleep_hours: 7.5 });

    await page.goto("/body");
    await page.getByLabel("体重 kg").fill("74.9");
    const bodyMetricResponse = page.waitForResponse(
      (response) =>
        response.url() === `${API_BASE_URL}/api/body-metrics` &&
        response.request().method() === "POST" &&
        response.status() === 200
    );
    await page.getByRole("button", { name: "保存身体数据" }).click();
    await bodyMetricResponse;
    const metrics = await (await request.get(`${API_BASE_URL}/api/body-metrics?user_id=demo-user-945`)).json();
    expect(metrics.data.at(-1)).toMatchObject({ weight_kg: 74.9, date: "2026-07-11" });

    await page.goto("/workout");
    const workoutLogsBefore = await (await request.get(`${API_BASE_URL}/api/workout-logs?user_id=demo-user-945`)).json();
    await page.getByRole("button", { name: "完成训练" }).click();
    await expect(page.getByText("训练记录已保存")).toBeVisible();
    const workoutLogsAfter = await (await request.get(`${API_BASE_URL}/api/workout-logs?user_id=demo-user-945`)).json();
    expect(workoutLogsAfter.data).toHaveLength(workoutLogsBefore.data.length + 1);
  });

  test("writes Agent workout and meal drafts only after confirmation", async ({ page, request }) => {
    await page.goto("/agent");
    const input = page.getByPlaceholder("今天深蹲做了 4 组，每组 8 次，80kg，感觉很累。");

    const workoutBefore = await (await request.get(`${API_BASE_URL}/api/workout-logs?user_id=demo-user-945`)).json();
    await input.fill("今天深蹲做了 4 组，每组 8 次，80kg，感觉很累。");
    await page.getByRole("button", { name: "发送" }).click();
    await expect(page.getByRole("heading", { name: "确认智能教练草稿" })).toBeVisible();
    const workoutUnconfirmed = await (await request.get(`${API_BASE_URL}/api/workout-logs?user_id=demo-user-945`)).json();
    expect(workoutUnconfirmed.data).toHaveLength(workoutBefore.data.length);

    const workoutWriteResponse = page.waitForResponse(
      (response) =>
        response.url() === `${API_BASE_URL}/api/workout-logs` &&
        response.request().method() === "POST",
      { timeout: 5_000 }
    );
    await page.getByRole("dialog").getByRole("button", { name: "确认" }).click();
    expect((await workoutWriteResponse).status()).toBe(200);
    const workoutConfirmed = await (await request.get(`${API_BASE_URL}/api/workout-logs?user_id=demo-user-945`)).json();
    expect(workoutConfirmed.data).toHaveLength(workoutBefore.data.length + 1);

    const mealBefore = await (await request.get(`${API_BASE_URL}/api/meal-logs?user_id=demo-user-945`)).json();
    await input.fill("我中午吃了鸡胸肉饭，可以帮我记录吗？");
    await page.getByRole("button", { name: "发送" }).click();
    await expect(page.getByRole("heading", { name: "确认智能教练草稿" })).toBeVisible();
    const mealUnconfirmed = await (await request.get(`${API_BASE_URL}/api/meal-logs?user_id=demo-user-945`)).json();
    expect(mealUnconfirmed.data).toHaveLength(mealBefore.data.length);

    const mealWriteResponse = page.waitForResponse(
      (response) =>
        response.url() === `${API_BASE_URL}/api/meal-logs` &&
        response.request().method() === "POST",
      { timeout: 5_000 }
    );
    await page.getByRole("dialog").getByRole("button", { name: "确认" }).click();
    expect((await mealWriteResponse).status()).toBe(200);
    const mealConfirmed = await (await request.get(`${API_BASE_URL}/api/meal-logs?user_id=demo-user-945`)).json();
    expect(mealConfirmed.data).toHaveLength(mealBefore.data.length + 1);
    expect(mealConfirmed.data.at(-1)).toMatchObject({
      foods: [],
      notes: "我中午吃了鸡胸肉饭，可以帮我记录吗？"
    });
  });

  test("generates a plan draft and activates it only after acceptance", async ({ page, request }) => {
    const activeBefore = await (await request.get(`${API_BASE_URL}/api/plans/current?user_id=demo-user-945`)).json();
    await page.goto("/plan");
    await page.getByRole("button", { name: "生成计划" }).click();
    await expect(page.getByText("Draft", { exact: true })).toBeVisible();
    const activeDuringDraft = await (await request.get(`${API_BASE_URL}/api/plans/current?user_id=demo-user-945`)).json();
    expect(activeDuringDraft.data.plan_id).toBe(activeBefore.data.plan_id);

    const acceptResponse = page.waitForResponse((response) =>
      response.url().includes("/api/plans/") && response.url().endsWith("/accept") && response.request().method() === "POST"
    );
    await page.getByRole("button", { name: "接受计划" }).click();
    expect((await acceptResponse).status()).toBe(200);
    const activeAfter = await (await request.get(`${API_BASE_URL}/api/plans/current?user_id=demo-user-945`)).json();
    expect(activeAfter.data.plan_id).not.toBe(activeBefore.data.plan_id);
    expect(activeAfter.data.status).toBe("active");
  });

  test("writes an Agent plan adjustment only after confirmation", async ({ page, request }) => {
    await page.goto("/agent");
    const before = await (await request.get(`${API_BASE_URL}/api/plans/current?user_id=demo-user-945`)).json();
    await page.getByPlaceholder("今天深蹲做了 4 组，每组 8 次，80kg，感觉很累。").fill("今天太累了，帮我调整计划。");
    await page.getByRole("button", { name: "发送" }).click();
    await expect(page.getByRole("heading", { name: "确认智能教练草稿" })).toBeVisible();
    const unconfirmed = await (await request.get(`${API_BASE_URL}/api/plans/current?user_id=demo-user-945`)).json();
    expect(unconfirmed.data.plan_id).toBe(before.data.plan_id);
    const adjustResponse = page.waitForResponse((response) => response.url().includes("/adjust") && response.request().method() === "POST");
    await page.getByRole("dialog").getByRole("button", { name: "确认" }).click();
    expect((await adjustResponse).status()).toBe(200);
    const after = await (await request.get(`${API_BASE_URL}/api/plans/current?user_id=demo-user-945`)).json();
    expect(after.data.plan_id).not.toBe(before.data.plan_id);
    expect(after.data.generated_by).toBe("agent");
  });

  test("writes a structured plan-page adjustment only after Agent confirmation", async ({ page, request }) => {
    const before = await (await request.get(`${API_BASE_URL}/api/plans/current?user_id=demo-user-945`)).json();
    await page.goto("/plan");
    await page.getByLabel("调整方式").selectOption("skip_workout");
    await page.getByLabel("调整原因").fill("恢复不足，需要跳过今天训练");
    await page.getByRole("button", { name: "生成调整草稿" }).click();
    await expect(page.getByRole("heading", { name: "确认智能教练草稿" })).toBeVisible();

    const unconfirmed = await (await request.get(`${API_BASE_URL}/api/plans/current?user_id=demo-user-945`)).json();
    expect(unconfirmed.data.plan_id).toBe(before.data.plan_id);

    const adjustResponse = page.waitForResponse((response) => response.url().includes("/adjust") && response.request().method() === "POST");
    await page.getByRole("dialog").getByRole("button", { name: "确认" }).click();
    expect((await adjustResponse).status()).toBe(200);
    const after = await (await request.get(`${API_BASE_URL}/api/plans/current?user_id=demo-user-945`)).json();
    expect(after.data.plan_id).not.toBe(before.data.plan_id);
    expect(after.data.workout_plan.days[0].exercises).toEqual([]);
  });

  test("keeps high-risk Agent input out of draft confirmation", async ({ page }) => {
    await page.goto("/agent");
    await page.getByPlaceholder("今天深蹲做了 4 组，每组 8 次，80kg，感觉很累。")
      .fill("我训练时胸闷眩晕，还能继续冲重量吗？");
    await page.getByRole("button", { name: "发送" }).click();
    await expect(page.getByText(/暂停训练/).last()).toBeVisible();
    await expect(page.getByRole("heading", { name: "确认智能教练草稿" })).toBeHidden();
  });

  test("rejects malformed and unsupported Agent workout drafts without writes", async ({ page, request }) => {
    const drafts = [
      { type: "workout_log", payload: { exercise_name: "深蹲", sets: 0, reps: 8 } },
      { type: "workout_log", payload: { exercise_name: "深蹲", sets: 4, reps: 8.5 } },
      { type: "workout_log", payload: { exercise_name: "深蹲", sets: 4, reps: 8, weight_kg: -1 } },
      { type: "workout_log", payload: { exercise_name: "深蹲", sets: 4_294_967_296, reps: 8 } },
      { type: "daily_checkin", payload: { fatigue_level: 4 } },
      { type: "plan_adjustment", payload: { adjustment_type: "reduce_intensity" } }
    ];
    let draftIndex = 0;
    await page.route("**/api/agent/chat", async (route) => {
      const draft = drafts[draftIndex++];
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          data: {
            message_id: `agent-test-${draftIndex}`,
            user_id: "demo-user-945",
            role: "agent",
            content: "请确认草稿。",
            locale: "zh-CN",
            record_draft: { ...draft, requires_confirmation: true },
            created_at: "2026-07-11T09:00:00Z"
          },
          error: null
        })
      });
    });

    await page.goto("/agent");
    const input = page.getByPlaceholder("今天深蹲做了 4 组，每组 8 次，80kg，感觉很累。");
    const workoutBefore = await (await request.get(`${API_BASE_URL}/api/workout-logs?user_id=demo-user-945`)).json();
    const mealBefore = await (await request.get(`${API_BASE_URL}/api/meal-logs?user_id=demo-user-945`)).json();
    let structuredWriteCount = 0;
    page.on("request", (outgoing) => {
      if (
        outgoing.method() === "POST" &&
        [`${API_BASE_URL}/api/workout-logs`, `${API_BASE_URL}/api/meal-logs`].includes(outgoing.url())
      ) {
        structuredWriteCount += 1;
      }
    });

    for (let index = 0; index < drafts.length; index += 1) {
      await input.fill(`草稿测试 ${index}`);
      await page.getByRole("button", { name: "发送" }).click();
      await expect(page.getByRole("heading", { name: "确认智能教练草稿" })).toBeVisible();
      await page.getByRole("dialog").getByRole("button", { name: "确认" }).click();
      await expect(page.getByText(
        index === drafts.length - 2
          ? "This draft type cannot be saved yet."
          : index === drafts.length - 1
            ? "Plan adjustment draft is invalid."
            : "Workout draft is invalid."
      )).toBeVisible();
      await page.getByRole("dialog").getByRole("button", { name: "取消" }).click();
    }

    expect(structuredWriteCount).toBe(0);
    const workoutAfter = await (await request.get(`${API_BASE_URL}/api/workout-logs?user_id=demo-user-945`)).json();
    const mealAfter = await (await request.get(`${API_BASE_URL}/api/meal-logs?user_id=demo-user-945`)).json();
    expect(workoutAfter.data).toHaveLength(workoutBefore.data.length);
    expect(mealAfter.data).toHaveLength(mealBefore.data.length);
  });

  test("shows normalized validation errors", async ({ page }) => {
    await page.route("**/api/today?*", (route) =>
      route.fulfill({
        status: 422,
        contentType: "application/json",
        body: JSON.stringify({ detail: [{ loc: ["query", "date"], msg: "Invalid date", type: "value_error" }] })
      })
    );
    await page.goto("/app");
    await expect(page.getByRole("status")).toContainText("Request validation failed.");
  });

  test("shows protocol errors for malformed 422 responses", async ({ page }) => {
    await page.route("**/api/today?*", (route) =>
      route.fulfill({ status: 422, contentType: "application/json", body: "null" })
    );
    await page.goto("/app");
    await expect(page.getByRole("status")).toContainText("945 backend returned an invalid response.");
  });

  test("shows protocol errors for non-JSON responses", async ({ page }) => {
    await page.route("**/api/today?*", (route) =>
      route.fulfill({ status: 502, contentType: "text/html", body: "Bad gateway" })
    );
    await page.goto("/app");
    await expect(page.getByRole("status")).toContainText("945 backend returned an invalid response.");
  });

  test("shows network errors when the API request is aborted", async ({ page }) => {
    await page.route("**/api/today?*", (route) => route.abort("failed"));
    await page.goto("/app");
    await expect(page.getByRole("status")).toContainText("Unable to reach 945 backend.");
  });
});
