# 今日训练草稿保存 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 Agent 生成的今日训练经一次“确认保存”后成为当天可执行训练，并立即同步到 Today 看板。

**Architecture:** 在既有 `Plan` 版本生命周期内新增 `today_workout_plan` 草稿类型和替换当天训练接口。保存接口复制当前 active 计划、替换当日 `WorkoutPlanDay`、归档旧计划并返回新版本；前端确认控件只调用该接口，并刷新共享计划状态和 Today 数据。

**Tech Stack:** React 19、TypeScript、Vite、FastAPI、Pydantic、LangGraph、Playwright、pytest。

**Spec:** `docs/superpowers/specs/2026-09-20-today-workout-draft-design.md`

## Global Constraints

- 只替换应用当前日期的训练；后续训练、饮食计划和训练历史不变。
- Agent 输出必须先成为 `RecordDraft`；只有用户点击一次“确认保存”后才能结构化写入。
- 不将确认文字作为第二轮聊天消息发送到 `/api/agent/chat`。
- 沿用既有颜色、字体、图标、导航和玻璃视觉风格。
- 不使用真实模型调用、不得清空 MongoDB 或写入真实用户测试数据。
- 未经用户明确要求，不提交、合并或删除分支。

## Review Focus

- 重复点击保存：第一次请求未结束时按钮必须禁用，且只产生一条计划版本。
- 非当天草稿：接口返回验证错误，旧 active 计划保持不变。
- 当前计划不覆盖今天：不展示或保存今日训练草稿。
- 取消草稿：不发送结构化写入请求，Today 看板保持原样。
- 替换后刷新：Today 看板必须显示新训练，后续训练日和饮食计划必须保持一致。

---

## 文件结构

- `backend/app/models/domain.py`：声明草稿类型、今日训练替换请求和动作约束模型。
- `backend/app/services/plan_service.py`：复制并替换当天训练、归档旧版本的领域服务。
- `backend/app/api/routes_plans.py`：暴露已确认的替换接口。
- `backend/app/agents/tools.py`：构建 `today_workout_plan` 草稿。
- `backend/app/agents/tool_registry.py`：约束 Agent 工具参数并执行草稿工具。
- `backend/app/agents/nodes.py`：识别“生成今天训练”请求，并在 fallback 中生成确定性草稿。
- `backend/app/agents/prompts.py`：要求模型只通过草稿工具交付可保存的今日训练。
- `src/types/domain.ts`：镜像草稿和请求数据类型。
- `src/services/httpApi.ts`：调用替换当天训练接口。
- `src/services/recordDraft.ts`：把今日训练草稿映射为该结构化请求。
- `src/pages/AgentPage.tsx`：在原有草稿确认区域中展示一次性“确认保存”并刷新 Today 上下文。
- `backend/tests/test_plans_api.py`、`backend/tests/test_agent_graph.py`、`backend/tests/test_agent_tool_registry.py`：后端、Agent 与草稿验证。
- `tests/http-integration.spec.ts`：真实 HTTP 下单次确认、写入和 Today 看板同步。

### Task 1: 领域模型与计划替换服务

**Files:**
- Modify: `backend/app/models/domain.py`
- Modify: `backend/app/services/plan_service.py`
- Test: `backend/tests/test_plans_api.py`

**Interfaces:**
- Produces: `TodayWorkoutReplaceInput(user_id, confirmed, workout_day)` 和 `replace_today_workout(plan_id, input_data) -> Plan | None`。
- Consumes: `Plan`、`WorkoutPlanDay`、`current_date()`、现有计划保存接口。

- [ ] **Step 1: 写失败的服务/API 测试**

```python
def test_replace_today_workout_creates_a_new_active_version_and_preserves_future_days():
    original = client.get("/api/plans/current", params={"user_id": "demo-user-945"}).json()["data"]["plan"]
    replacement = {
        "date": "2026-07-11", "name": "背部训练", "focus": "back",
        "duration_minutes": 50,
        "exercises": [{
            "exercise_id": "agent-row", "name": "杠铃划船", "target_muscles": ["背部"],
            "sets": 4, "reps": "8-10", "target_weight": None, "rest_seconds": 90, "notes": None,
        }],
    }
    response = client.post(
        f"/api/plans/{original['plan_id']}/replace-today-workout",
        json={"user_id": "demo-user-945", "confirmed": True, "workout_day": replacement},
    )
    assert response.status_code == 200
    assert response.json()["data"]["workout_plan"]["days"][0] == replacement
    assert response.json()["data"]["meal_plan"] == original["meal_plan"]
    assert client.get("/api/plans/current", params={"user_id": "demo-user-945"}).json()["data"]["plan"]["plan_id"] != original["plan_id"]


def test_replace_today_workout_rejects_a_non_current_date_without_archiving_plan():
    original = client.get("/api/plans/current", params={"user_id": "demo-user-945"}).json()["data"]["plan"]
    invalid_day = {
        "date": "2026-07-12", "name": "背部训练", "focus": "back",
        "duration_minutes": 50,
        "exercises": [{
            "exercise_id": "agent-row", "name": "杠铃划船", "target_muscles": ["背部"],
            "sets": 4, "reps": "8-10", "target_weight": None, "rest_seconds": 90, "notes": None,
        }],
    }
    response = client.post(
        f"/api/plans/{original['plan_id']}/replace-today-workout",
        json={"user_id": "demo-user-945", "confirmed": True, "workout_day": invalid_day},
    )
    assert response.status_code == 422
    assert client.get("/api/plans/current", params={"user_id": "demo-user-945"}).json()["data"]["plan"]["plan_id"] == original["plan_id"]
```

- [ ] **Step 2: 运行失败测试**

Run: `D:\Codex\945\.venv\Scripts\python.exe -m pytest backend/tests/test_plans_api.py -q`

Expected: FAIL，因为请求模型、路由和替换服务尚不存在。

- [ ] **Step 3: 添加最小模型、服务和路由实现**

```python
class TodayWorkoutReplaceInput(ApiModel):
    user_id: str
    confirmed: Literal[True]
    workout_day: WorkoutPlanDay


def replace_today_workout(plan_id: str, input_data: TodayWorkoutReplaceInput) -> Plan | None:
    current = get_current_plan(input_data.user_id)
    if current is None or current.plan_id != plan_id:
        return None
    if input_data.workout_day.date != current_date().isoformat():
        raise ValueError("Today workout date must match the current application date.")
    days = [
        input_data.workout_day if day.date == input_data.workout_day.date else day
        for day in current.workout_plan.days
    ]
    if not any(day.date == input_data.workout_day.date for day in current.workout_plan.days):
        return None
    archive = current.model_copy(update={"status": "archived", "updated_at": timestamp()})
    replacement = current.model_copy(update={
        "plan_id": _plan_id("today-workout"),
        "status": "active",
        "workout_plan": WorkoutPlan(days=days),
        "updated_at": timestamp(),
    })
    writer = store.save_plan if (store := _active_repository_store()) else save_plan
    writer(archive)
    return writer(replacement)
```

路由将 `ValueError` 转为 422；用户不匹配或 active 计划不存在维持现有 404 契约。

- [ ] **Step 4: 运行服务/API 测试**

Run: `D:\Codex\945\.venv\Scripts\python.exe -m pytest backend/tests/test_plans_api.py -q`

Expected: PASS。

### Task 2: Agent 今日训练草稿

**Files:**
- Modify: `backend/app/models/domain.py`
- Modify: `backend/app/agents/tools.py`
- Modify: `backend/app/agents/tool_registry.py`
- Modify: `backend/app/agents/nodes.py`
- Modify: `backend/app/agents/prompts.py`
- Test: `backend/tests/test_agent_tool_registry.py`
- Test: `backend/tests/test_agent_graph.py`

**Interfaces:**
- Consumes: `WorkoutPlanDay` 与当前应用日期。
- Produces: `RecordDraft(type="today_workout_plan", requires_confirmation=True, payload={"workout_day": ...})`。

- [ ] **Step 1: 写失败的工具与图测试**

```python
def test_today_workout_tool_returns_a_confirmation_required_structured_draft():
    workout_day = {
        "date": "2026-07-11", "name": "背部训练", "focus": "back",
        "duration_minutes": 50,
        "exercises": [{
            "exercise_id": "agent-row", "name": "杠铃划船", "target_muscles": ["背部"],
            "sets": 4, "reps": "8-10", "target_weight": None, "rest_seconds": 90, "notes": None,
        }],
    }
    result = execute_agent_tool(
        ToolCallProposal(call_id="today-1", name="create_today_workout_plan_draft", arguments=workout_day),
        AgentToolContext(user_id="demo-user-945", date="2026-07-11", locale="zh-CN", message="今天练什么？"),
    )
    assert result.record_draft.type == "today_workout_plan"
    assert result.record_draft.payload["workout_day"]["date"] == "2026-07-11"


def test_agent_graph_returns_today_workout_draft_for_an_explicit_today_workout_request():
    result = asyncio.run(run_agent_graph(
        user_id=DEMO_USER_ID, locale="zh-CN", message="帮我生成今天的训练安排",
        context={"date": "2026-07-11"}, provider_router=router,
    ))
    assert result.record_draft.type == "today_workout_plan"
    assert result.record_draft.requires_confirmation is True
```

- [ ] **Step 2: 运行失败测试**

Run: `D:\Codex\945\.venv\Scripts\python.exe -m pytest backend/tests/test_agent_tool_registry.py backend/tests/test_agent_graph.py -q -k "today_workout"`

Expected: FAIL，因为草稿类型和工具尚不存在。

- [ ] **Step 3: 实现草稿构建、工具验证和 fallback**

```python
def build_today_workout_plan_draft(workout_day: WorkoutPlanDay) -> RecordDraft:
    return RecordDraft(
        type="today_workout_plan",
        requires_confirmation=True,
        payload={"workout_day": workout_day.model_dump(mode="json")},
    )
```

在 `tool_registry.py` 新增严格 Pydantic 参数模型，字段与 `WorkoutPlanDay` 对齐，拒绝额外字段。新增 `create_today_workout_plan_draft`，其描述必须说明仅生成预览、不能保存。`nodes.py` 只对“生成今天训练/今天练什么/today workout plan”等明确请求走该草稿 fallback；高风险输入继续由安全节点提前返回。

Prompt 明确：若生成可保存的今日训练，必须调用该草稿工具；无草稿时不得要求用户确认保存。

- [ ] **Step 4: 运行 Agent 测试**

Run: `D:\Codex\945\.venv\Scripts\python.exe -m pytest backend/tests/test_agent_tool_registry.py backend/tests/test_agent_graph.py backend/tests/test_agent_prompts.py -q`

Expected: PASS。

### Task 3: 前端单次确认与 Today 数据刷新

**Files:**
- Modify: `src/types/domain.ts`
- Modify: `src/services/httpApi.ts`
- Modify: `src/services/recordDraft.ts`
- Modify: `src/pages/AgentPage.tsx`
- Test: `tests/agent-workflow.spec.ts`

**Interfaces:**
- Consumes: `RecordDraft.type === "today_workout_plan"`、`api.replaceTodayWorkout(...)`。
- Produces: 一次 `POST /api/plans/{plan_id}/replace-today-workout`，随后 `refreshPlanState()` 与 `loadTodayContext()`。

- [ ] **Step 1: 写失败的浏览器回归测试**

```ts
test("saves a today workout draft once without starting another agent chat", async ({ page }) => {
  let saveCalls = 0;
  let chatCalls = 0;
  const workoutDay = { date: "2026-07-11", name: "背部训练", focus: "back", duration_minutes: 50, exercises: [] };
  const draftResponse = JSON.stringify({ data: {
    message_id: "today-draft", user_id: "demo-user-945", role: "agent", locale: "zh-CN",
    content: "已整理今天的训练安排。", created_at: "2026-07-11T09:00:00Z",
    record_draft: { type: "today_workout_plan", requires_confirmation: true, payload: { workout_day: workoutDay } }
  }, error: null });
  await page.route("**/api/agent/chat", (route) => { chatCalls += 1; return route.fulfill({ contentType: "application/json", body: draftResponse }); });
  await page.route("**/api/plans/*/replace-today-workout", (route) => {
    saveCalls += 1;
    return route.fulfill({ contentType: "application/json", body: JSON.stringify({ data: { plan_id: "plan-replaced", workout_plan: { days: [workoutDay] } }, error: null }) });
  });
  await page.goto("/agent");
  await page.getByPlaceholder(/深蹲/).fill("帮我生成今天的训练安排");
  await page.getByRole("button", { name: "发送" }).click();
  await page.getByRole("button", { name: "确认保存" }).click();
  expect(saveCalls).toBe(1);
  expect(chatCalls).toBe(1);
});

test("cancelling a today workout draft does not write or send a confirmation message", async ({ page }) => {
  let writes = 0;
  const workoutDay = { date: "2026-07-11", name: "背部训练", focus: "back", duration_minutes: 50, exercises: [] };
  await page.route("**/api/agent/chat", (route) => route.fulfill({
    contentType: "application/json",
    body: JSON.stringify({ data: {
      message_id: "today-draft-cancel", user_id: "demo-user-945", role: "agent", locale: "zh-CN",
      content: "已整理今天的训练安排。", created_at: "2026-07-11T09:00:00Z",
      record_draft: { type: "today_workout_plan", requires_confirmation: true, payload: { workout_day: workoutDay } }
    }, error: null })
  }));
  await page.route("**/api/plans/*/replace-today-workout", (route) => { writes += 1; return route.abort(); });
  await page.goto("/agent");
  await page.getByPlaceholder(/深蹲/).fill("帮我生成今天的训练安排");
  await page.getByRole("button", { name: "发送" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "取消" }).click();
  expect(writes).toBe(0);
});
```

- [ ] **Step 2: 运行失败测试**

Run: `npx playwright test --config=playwright.http.config.ts tests/agent-workflow.spec.ts -g "saves a today workout"`

Expected: FAIL，因为前端还不识别此草稿类型或没有保存接口。

- [ ] **Step 3: 实现 API 映射与单次确认控件**

```ts
async replaceTodayWorkout(input: {
  user_id: string;
  plan_id: string;
  workout_day: WorkoutPlanDay;
}): Promise<ApiResponse<Plan>> {
  return post<Plan>(`/api/plans/${input.plan_id}/replace-today-workout`, {
    user_id: input.user_id,
    confirmed: true,
    workout_day: input.workout_day
  });
}
```

`saveRecordDraft()` 解析 `payload.workout_day` 并调用该方法。`AgentPage` 对此草稿在现有确认区域使用唯一文案“确认保存”；确认期间禁用按钮，成功后执行 `await refreshPlanState()`、`await loadTodayContext()` 并清除草稿。不得调用 `send()`、不得追加用户确认消息。

当 `currentPlan` 为空、草稿日期不是 `appToday` 或草稿动作数组为空时，`saveRecordDraft()` 返回本地错误且不发出 HTTP 请求。

- [ ] **Step 4: 运行前端回归测试**

Run: `npx playwright test --config=playwright.http.config.ts tests/agent-workflow.spec.ts -g "saves a today workout"`

Expected: PASS。

### Task 4: 真实 HTTP 验收和 Today 看板回归

**Files:**
- Modify: `tests/http-integration.spec.ts`
- Test: `tests/http-integration.spec.ts`

**Interfaces:**
- Consumes: Task 1 的真实 FastAPI 路由和 Task 3 的确认流程。
- Produces: 对“未确认不写入、单次确认后只替换当天、Today 刷新可见”的端到端证据。

- [ ] **Step 1: 写失败的 HTTP 集成测试**

```ts
test("persists an Agent today-workout draft once and shows it on Today after refresh", async ({ page, request }) => {
  const before = await (await request.get(`${API_BASE_URL}/api/plans/current?user_id=demo-user-945`)).json();
  await page.goto("/agent");
  await page.getByPlaceholder(/深蹲/).fill("帮我生成今天的训练安排");
  await page.getByRole("button", { name: "发送" }).click();
  await expect(page.getByRole("button", { name: "确认保存" })).toBeVisible();
  expect((await request.get(`${API_BASE_URL}/api/plans/current?user_id=demo-user-945`)).json().data.plan.plan_id).toBe(before.data.plan.plan_id);
  const write = page.waitForResponse((response) => response.url().includes("/replace-today-workout") && response.request().method() === "POST");
  await page.getByRole("button", { name: "确认保存" }).click();
  expect((await write).status()).toBe(200);
  await page.goto("/today");
  await expect(page.getByText("背部训练")).toBeVisible();
});

test("does not expose a today workout save control when the current plan is unavailable", async ({ page }) => {
  await page.route("**/api/plans/current?*", (route) => route.fulfill({
    contentType: "application/json", body: JSON.stringify({ data: { plan: null, coverage_status: "none" }, error: null })
  }));
  await page.goto("/agent");
  await expect(page.getByRole("button", { name: "确认保存" })).toBeHidden();
});
```

- [ ] **Step 2: 运行失败测试**

Run: `npx playwright test --config=playwright.http.config.ts tests/http-integration.spec.ts -g "persists an Agent today-workout"`

Expected: FAIL，直到前述接口与前端确认实现完成。

- [ ] **Step 3: 仅为测试所需的确定性 Provider 补齐今日训练草稿输出**

在 `backend/app/llm/deterministic.py` 对明确的今日训练请求返回固定 `create_today_workout_plan_draft` 调用，动作使用稳定中文值，例如“背部训练”和“杠铃划船”。不要修改真实模型 Provider 的默认回答策略以伪造测试结果。

- [ ] **Step 4: 运行严格验收**

Run: `npm run build`

Run: `D:\Codex\945\.venv\Scripts\python.exe -m pytest backend/tests/test_plans_api.py backend/tests/test_agent_tool_registry.py backend/tests/test_agent_graph.py backend/tests/test_agent_prompts.py -q`

Run: `npm run qa:http`

Expected: 构建成功；相关后端测试通过；HTTP 验收显示未确认时没有计划变更，确认一次后 Today 看板显示新训练。
