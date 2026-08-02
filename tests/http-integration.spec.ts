import { expect, test } from "@playwright/test";

const API_BASE_URL = "http://127.0.0.1:8000";

test.describe.serial("945 real HTTP integration", () => {
  test.beforeEach(({}, testInfo) => {
    test.skip(testInfo.project.name !== "chrome-desktop-http", "requires the HTTP Playwright project");
  });

  test("uses the demo account when unauthenticated mode has a stale saved user", async ({ page }) => {
    await page.addInitScript(() => {
      window.localStorage.setItem("945.auth.user_id", "stale-user-id");
    });

    await page.goto("/agent");
    await page.getByPlaceholder("\u4eca\u5929\u6df1\u8e72\u505a\u4e86 4 \u7ec4\uff0c\u6bcf\u7ec4 8 \u6b21\uff0c80kg\uff0c\u611f\u89c9\u5f88\u7d2f\u3002").fill("\u4f60\u597d");
    await page.getByRole("button", { name: "\u53d1\u9001" }).click();

    await expect(page.getByText("Demo user not found.")).toBeHidden();
    await expect(page.getByText("\u6211\u5df2\u8bfb\u53d6\u4f60\u7684\u95ee\u9898\u3002\u5f53\u524d demo \u4f1a\u4f18\u5148\u57fa\u4e8e\u4eca\u65e5\u8ba1\u5212\u3001\u8bb0\u5f55\u548c\u5efa\u8bae\u56de\u7b54\u3002")).toBeVisible();
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
    await page.goto("/today");
    await expect(page.getByRole("heading", { name: "早上好，Alex。" })).toBeVisible();
    expect((await todayResponse).status()).toBe(200);
  });

  test("guides the user to renew an expired plan when Today has no scheduled content", async ({ page }) => {
    await page.route("**/api/today?*", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          data: {
            date: "2026-07-11",
            user: { user_id: "demo-user-945", display_name: "Alex", goal: "body_recomposition" },
            status_summary: {
              weekly_workouts_completed: 0,
              weekly_workouts_planned: 4,
              calories_target: 2300,
              calories_logged: 0,
              protein_target_g: 160,
              protein_logged_g: 0,
              weight_7_day_delta_kg: 0,
              recovery_status: "normal"
            },
            today_workout: null,
            today_meals: [],
            daily_checkin: null,
            latest_advice: null
          },
          error: null
        })
      })
    );

    await page.goto("/today");
    await expect(page.getByText("当前计划没有覆盖今天")).toBeVisible();
    await page.getByRole("button", { name: "生成新计划" }).click();
    await expect(page).toHaveURL(/\/plan$/);
  });

  test("persists page mutations through FastAPI", async ({ page, request }) => {
    await page.goto("/today");

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

  test("persists a completed workout from the Today page", async ({ page, request }) => {
    await page.goto("/today");
    const before = await (await request.get(`${API_BASE_URL}/api/workout-logs?user_id=demo-user-945`)).json();
    const writeResponse = page.waitForResponse(
      (response) => response.url() === `${API_BASE_URL}/api/workout-logs` && response.request().method() === "POST"
    );

    await page.getByRole("button", { name: "完成", exact: true }).click();

    expect((await writeResponse).status()).toBe(200);
    await expect(page.getByText("训练记录已保存")).toBeVisible();
    const after = await (await request.get(`${API_BASE_URL}/api/workout-logs?user_id=demo-user-945`)).json();
    expect(after.data).toHaveLength(before.data.length + 1);
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
    expect(activeDuringDraft.data.plan.plan_id).toBe(activeBefore.data.plan.plan_id);

    const acceptResponse = page.waitForResponse((response) =>
      response.url().includes("/api/plans/") && response.url().endsWith("/accept") && response.request().method() === "POST"
    );
    await page.getByRole("button", { name: "接受计划" }).click();
    expect((await acceptResponse).status()).toBe(200);
    const activeAfter = await (await request.get(`${API_BASE_URL}/api/plans/current?user_id=demo-user-945`)).json();
    expect(activeAfter.data.plan.plan_id).not.toBe(activeBefore.data.plan.plan_id);
    expect(activeAfter.data.plan.status).toBe("active");
  });

  test("writes an Agent plan adjustment only after confirmation", async ({ page, request }) => {
    await page.goto("/agent");
    const before = await (await request.get(`${API_BASE_URL}/api/plans/current?user_id=demo-user-945`)).json();
    await page.getByPlaceholder("今天深蹲做了 4 组，每组 8 次，80kg，感觉很累。").fill("今天太累了，帮我调整计划。");
    await page.getByRole("button", { name: "发送" }).click();
    await expect(page.getByRole("heading", { name: "确认智能教练草稿" })).toBeVisible();
    const unconfirmed = await (await request.get(`${API_BASE_URL}/api/plans/current?user_id=demo-user-945`)).json();
    expect(unconfirmed.data.plan.plan_id).toBe(before.data.plan.plan_id);
    const adjustResponse = page.waitForResponse((response) => response.url().includes("/adjust") && response.request().method() === "POST");
    await page.getByRole("dialog").getByRole("button", { name: "确认" }).click();
    expect((await adjustResponse).status()).toBe(200);
    const after = await (await request.get(`${API_BASE_URL}/api/plans/current?user_id=demo-user-945`)).json();
    expect(after.data.plan.plan_id).not.toBe(before.data.plan.plan_id);
    expect(after.data.plan.generated_by).toBe("agent");
  });

  test("writes a structured plan-page adjustment only after Agent confirmation", async ({ page, request }) => {
    const before = await (await request.get(`${API_BASE_URL}/api/plans/current?user_id=demo-user-945`)).json();
    await page.goto("/plan");
    await page.getByLabel("调整方式").selectOption("skip_workout");
    await page.getByLabel("调整原因").fill("恢复不足，需要跳过今天训练");
    await page.getByRole("button", { name: "生成调整草稿" }).click();
    await expect(page.getByRole("heading", { name: "确认智能教练草稿" })).toBeVisible();

    const unconfirmed = await (await request.get(`${API_BASE_URL}/api/plans/current?user_id=demo-user-945`)).json();
    expect(unconfirmed.data.plan.plan_id).toBe(before.data.plan.plan_id);

    const adjustResponse = page.waitForResponse((response) => response.url().includes("/adjust") && response.request().method() === "POST");
    await page.getByRole("dialog").getByRole("button", { name: "确认" }).click();
    expect((await adjustResponse).status()).toBe(200);
    const after = await (await request.get(`${API_BASE_URL}/api/plans/current?user_id=demo-user-945`)).json();
    expect(after.data.plan.plan_id).not.toBe(before.data.plan.plan_id);
    expect(after.data.plan.workout_plan.days[0].exercises).toEqual([]);
  });

  test("persists personalization settings before generating a tailored plan preview", async ({ page, request }) => {
    await page.goto("/settings");
    await page.getByLabel("每周训练天数").fill("3");
    await page.getByLabel("单次训练分钟").fill("45");
    await page.getByLabel("健身房").uncheck();
    await page.getByLabel("哑铃").uncheck();
    await page.getByLabel("徒手").check();
    await page.getByLabel("素食").check();
    await page.getByLabel("乳制品").check();
    await page.getByLabel("工作日繁忙").check();
    const settingsResponse = page.waitForResponse((response) => response.url().endsWith("/api/settings") && response.request().method() === "PATCH");
    const generatedResponse = page.waitForResponse((response) => response.url().endsWith("/api/plans/generate") && response.request().method() === "POST");
    await page.getByRole("button", { name: "保存并生成计划预览" }).click();

    expect((await settingsResponse).status()).toBe(200);
    const planResponse = await generatedResponse;
    expect(planResponse.status()).toBe(200);
    const plan = (await planResponse.json()).data;
    expect(plan.workout_plan.days).toHaveLength(3);
    const exerciseNames = plan.workout_plan.days.flatMap((day: { exercises: Array<{ name: string }> }) => day.exercises.map((exercise) => exercise.name));
    expect(exerciseNames).toContain("徒手深蹲");
    expect(plan.meal_plan.days[0].meals[0].foods.map((food: { name: string }) => food.name)).toContain("无糖豆乳酸奶");
    const settings = await (await request.get(`${API_BASE_URL}/api/settings?user_id=demo-user-945`)).json();
    expect(settings.data.profile).toMatchObject({ training_days_per_week: 3, training_duration_minutes: 45, equipment: ["bodyweight"] });
  });

  test("turns execution feedback into a confirmation-required adjustment draft", async ({ page, request }) => {
    await request.post(`${API_BASE_URL}/api/daily-checkins`, {
      data: { user_id: "demo-user-945", date: "2026-07-11", fatigue_level: 4, sleep_hours: 6.5 },
    });
    const before = await (await request.get(`${API_BASE_URL}/api/plans/current?user_id=demo-user-945`)).json();
    await page.goto("/advice");
    const feedbackResponse = page.waitForResponse((response) => response.url().endsWith("/api/advice/generate") && response.request().method() === "POST");
    await page.getByRole("button", { name: "刷新执行反馈" }).click();
    expect((await feedbackResponse).status()).toBe(200);
    await expect(page.getByText("恢复优先，今天降低训练强度")).toBeVisible();
    await page.getByRole("button", { name: "生成调整草稿" }).click();
    await expect(page.getByRole("heading", { name: "确认智能教练草稿" })).toBeVisible();
    const unconfirmed = await (await request.get(`${API_BASE_URL}/api/plans/current?user_id=demo-user-945`)).json();
    expect(unconfirmed.data.plan.plan_id).toBe(before.data.plan.plan_id);
  });

  test("keeps high-risk Agent input out of draft confirmation", async ({ page }) => {
    await page.goto("/agent");
    await page.getByPlaceholder("今天深蹲做了 4 组，每组 8 次，80kg，感觉很累。")
      .fill("我训练时胸闷眩晕，还能继续冲重量吗？");
    await page.getByRole("button", { name: "发送" }).click();
    await expect(page.getByText(/暂停训练/).last()).toBeVisible();
    await expect(page.getByRole("heading", { name: "确认智能教练草稿" })).toBeHidden();
  });

  test("shows a failed Agent run and retries only when the user requests it", async ({ page }) => {
    let hasRetried = false;
    await page.route("**/api/agent/runs?*", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          data: [
            {
              agent_run_id: "run-failed",
              user_id: "demo-user-945",
              status: hasRetried ? "completed" : "failed",
              started_at: "2026-07-11T09:00:00Z",
              completed_at: "2026-07-11T09:00:01Z",
              duration_ms: 1000,
              error_code: hasRetried ? null : "LLM_TIMEOUT"
            }
          ],
          error: null
        })
      })
    );
    await page.route("**/api/agent/runs/run-failed/retry", async (route) => {
      expect(route.request().method()).toBe("POST");
      hasRetried = true;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          data: {
            message_id: "retry-agent-message",
            user_id: "demo-user-945",
            role: "agent",
            content: "重试完成。",
            locale: "zh-CN",
            created_at: "2026-07-11T09:00:02Z"
          },
          error: null
        })
      });
    });

    await page.goto("/agent");
    await expect(page.getByText("上次请求未完成")).toBeVisible();
    await page.getByRole("button", { name: "重试此请求" }).click();
    await expect(page.getByRole("status").filter({ hasText: "本次请求已完成" })).toBeVisible();
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
    await page.goto("/today");
    await expect(page.getByRole("status")).toContainText("Request validation failed.");
  });

  test("shows protocol errors for malformed 422 responses", async ({ page }) => {
    await page.route("**/api/today?*", (route) =>
      route.fulfill({ status: 422, contentType: "application/json", body: "null" })
    );
    await page.goto("/today");
    await expect(page.getByRole("status")).toContainText("945 backend returned an invalid response.");
  });

  test("shows protocol errors for non-JSON responses", async ({ page }) => {
    await page.route("**/api/today?*", (route) =>
      route.fulfill({ status: 502, contentType: "text/html", body: "Bad gateway" })
    );
    await page.goto("/today");
    await expect(page.getByRole("status")).toContainText("945 backend returned an invalid response.");
  });

  test("shows network errors when the API request is aborted", async ({ page }) => {
    await page.route("**/api/today?*", (route) => route.abort("failed"));
    await page.goto("/today");
    await expect(page.getByRole("status")).toContainText("Unable to reach 945 backend.");
  });
});
