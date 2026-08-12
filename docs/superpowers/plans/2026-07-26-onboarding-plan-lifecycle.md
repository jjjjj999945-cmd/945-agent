# 945 首次建档与计划生命周期重构 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为首次和计划过期用户建立从资料建档、计划草稿审阅、显式启用到首日执行的可验证闭环，并将现有页面收敛为明确职责。

**Architecture:** 后端将 Profile 完整度、安全确认和计划覆盖状态作为稳定领域状态返回；前端以 `PlanContext` 统一解析 active plan，路由与页面只消费该状态。`ActionDraftContext` 集中暂存 Agent、建议和计划页产生的待确认草稿，Agent 页是唯一确认写入点，训练和饮食页只写真实执行数据。

**Tech Stack:** React 18 + TypeScript + Vite、FastAPI + Pydantic、Mongo/demo repository、Playwright、pytest。

## Global Constraints

- 桌面端优先；本计划不新增移动端适配。
- 中文为完整体验，保留 `zh-CN` 与 `en-US` i18n 结构；新增可见文案必须进入翻译字典。
- `Plan.status === "active"` 且计划日期覆盖运行日期，才允许进入执行态。
- 计划生成始终返回 `draft`；只有显式 accept 才能使其成为 active。
- Agent、Advice、Plan 生成的训练、饮食和计划调整都只产生 `RecordDraft`；用户确认后才能调用结构化写入 API。
- 不实现医疗诊断、治疗或康复处方；高风险输入只返回安全提醒。
- 不能再使用 `demoPlan.plan_id` 或组件内硬编码日期进行写入；必须使用 `PlanContext` 与统一日期服务。
- 不重做导航视觉风格；仅做满足新流程的必要页面与交互改动。

---

## File Structure

| 文件 | 职责 |
| --- | --- |
| `backend/app/models/domain.py` | Profile 完整度、安全确认、计划覆盖状态的 Pydantic 合约。 |
| `backend/app/services/plan_lifecycle.py` | 当前日期下的 Profile/Plan 生命周期推导，无 HTTP 依赖。 |
| `backend/app/services/plan_service.py` | 使用生命周期服务读取与接受计划，保持 demo/Mongo 双存储行为一致。 |
| `backend/app/api/routes_plans.py` | 返回具备 `coverage_status` 的当前计划查询结果。 |
| `backend/app/api/routes_profile.py` | 保存 Profile 时写入并返回安全确认状态。 |
| `backend/app/services/demo_store.py`、`repository_store.py` | 持久化 Profile 新字段并按日期解析 active plan。 |
| `src/types/domain.ts` | 后端合约、`PlanContextValue` 与 `ActionDraft` 类型。 |
| `src/services/dateContext.ts` | 单一运行日期来源，兼容 `VITE_945_REFERENCE_DATE`。 |
| `src/contexts/PlanContext.tsx` | 获取/刷新当前 Profile 与计划生命周期状态。 |
| `src/contexts/ActionDraftContext.tsx` | 统一的待确认操作队列与状态转换。 |
| `src/App.tsx`、`src/routes.ts` | Context Provider、路由守卫和页面依赖注入。 |
| `src/pages/OnboardingPage.tsx` | 六步资料建档、右侧 945 辅助、生成草稿，不接受计划。 |
| `src/pages/PlanPage.tsx` | 草稿审阅、重新建档、显式启用及计划调整交接。 |
| `src/pages/TodayPage.tsx` | 今日行动队列和无计划空态；不包含完整聊天或草稿确认。 |
| `src/pages/AgentPage.tsx` | 唯一的完整对话与 ActionDraft 确认入口。 |
| `src/pages/WorkoutPage.tsx`、`src/pages/DietPage.tsx` | 活跃计划执行与真实日志输入，不显示静态执行数据。 |
| `src/pages/AdvicePage.tsx`、`src/pages/SettingsPage.tsx` | 仅将草稿加入队列，设置不再直接生成并启用计划。 |
| `backend/tests/test_plan_lifecycle.py` | 生命周期服务与 API 的后端回归。 |
| `tests/plan-lifecycle.spec.ts` | HTTP 前端端到端主路径与空态验证。 |

---

### Task 1: 建立后端计划生命周期合约

**Files:**
- Create: `backend/app/services/plan_lifecycle.py`
- Modify: `backend/app/models/domain.py`
- Modify: `backend/app/services/plan_service.py`
- Modify: `backend/app/api/routes_plans.py`
- Test: `backend/tests/test_plan_lifecycle.py`

**Interfaces:**
- Consumes: `UserProfile | None`、`Plan | None`、`today: str`。
- Produces: `PlanCoverageStatus = Literal["active_today", "expired", "none"]`、`PlanLifecycleState` 和 `get_current_plan_response()`。

- [ ] **Step 1: 写失败的生命周期单元测试**

```python
def test_classify_plan_coverage_returns_active_today_for_active_plan_covering_today():
    plan = make_plan(status="active", start_date="2026-07-26", end_date="2026-08-01")
    assert classify_plan_coverage(plan, "2026-07-26") == "active_today"

def test_classify_plan_coverage_returns_expired_for_active_plan_ending_before_today():
    plan = make_plan(status="active", start_date="2026-07-11", end_date="2026-07-17")
    assert classify_plan_coverage(plan, "2026-07-26") == "expired"

def test_current_plan_endpoint_returns_none_state_instead_of_404_when_user_has_no_plan(client):
    response = client.get("/api/plans/current?user_id=demo-user-945")
    assert response.status_code == 200
    assert response.json()["data"] == {"plan": None, "coverage_status": "none"}
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest backend/tests/test_plan_lifecycle.py -q`  
Expected: FAIL，缺少 `classify_plan_coverage` 或 `/api/plans/current` 仍返回旧的 `Plan` 形状。

- [ ] **Step 3: 定义模型与纯生命周期服务**

在 `domain.py` 新增如下类型，避免将生命周期判断散落在路由和页面：

```python
PlanCoverageStatus = Literal["active_today", "expired", "none"]

class CurrentPlanResponse(ApiModel):
    plan: Plan | None
    coverage_status: PlanCoverageStatus
```

在 `plan_lifecycle.py` 实现：

```python
def classify_plan_coverage(plan: Plan | None, today: str) -> PlanCoverageStatus:
    if plan is None:
        return "none"
    if plan.status == "active" and plan.start_date <= today <= plan.end_date:
        return "active_today"
    return "expired"

def current_plan_state(plan: Plan | None, today: str) -> CurrentPlanResponse:
    return CurrentPlanResponse(plan=plan if classify_plan_coverage(plan, today) == "active_today" else None,
                               coverage_status=classify_plan_coverage(plan, today))
```

使用 `backend.app.core.dates.current_date()` 取得运行日期；`routes_plans.current_plan()` 始终返回 `ok(current_plan_state(...).model_dump())`，未知用户仍保持 `404 NOT_FOUND`。

- [ ] **Step 4: 扩展 API 测试并运行通过**

```python
def test_current_plan_endpoint_returns_expired_state_without_executable_plan(client, monkeypatch):
    monkeypatch.setenv("945_REFERENCE_DATE", "2026-07-26")
    response = client.get("/api/plans/current?user_id=demo-user-945")
    assert response.json()["data"]["coverage_status"] == "expired"
    assert response.json()["data"]["plan"] is None
```

Run: `python -m pytest backend/tests/test_plan_lifecycle.py backend/tests/test_plans_api.py -q`  
Expected: PASS。

- [ ] **Step 5: 提交**

```bash
git add backend/app/models/domain.py backend/app/services/plan_lifecycle.py backend/app/services/plan_service.py backend/app/api/routes_plans.py backend/tests/test_plan_lifecycle.py backend/tests/test_plans_api.py
git commit -m "feat: expose plan coverage lifecycle"
```

### Task 2: 完善 Profile 建档状态与安全确认

**Files:**
- Modify: `backend/app/models/domain.py`
- Modify: `backend/app/services/demo_store.py`
- Modify: `backend/app/services/repository_store.py`
- Modify: `backend/app/api/routes_profile.py`
- Test: `backend/tests/test_profile_settings_advice_api.py`
- Test: `backend/tests/test_plan_lifecycle.py`

**Interfaces:**
- Consumes: `ProfileCreateInput`、`ProfilePatchInput`。
- Produces: `UserProfile.safety_confirmed_at`、`UserProfile.profile_completion`、`UserProfile.missing_fields`。

- [ ] **Step 1: 写失败的 Profile 状态测试**

```python
def test_profile_requires_safety_confirmation_before_it_is_complete(client):
    response = client.patch("/api/profile/demo-user-945", json={"safety_confirmed": False})
    data = response.json()["data"]
    assert data["profile_completion"] == "incomplete"
    assert "safety_confirmed" in data["missing_fields"]

def test_profile_returns_complete_after_required_fields_and_safety_confirmation(client):
    response = client.patch("/api/profile/demo-user-945", json={"safety_confirmed": True})
    data = response.json()["data"]
    assert data["profile_completion"] == "complete"
    assert data["safety_confirmed_at"] is not None
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest backend/tests/test_profile_settings_advice_api.py -q`  
Expected: FAIL，`safety_confirmed` 与 Profile 状态字段不存在。

- [ ] **Step 3: 实现 Profile 完整度规则和持久化**

在 `UserProfile`、创建和 PATCH 输入中加入 `safety_confirmed: bool` 与 `safety_confirmed_at: str | None`；响应模型增加只读 `profile_completion: Literal["complete", "incomplete"]` 和 `missing_fields: list[str]`。在新服务函数中固定必填规则：`age`、`height_cm`、`weight_kg`、`goal`、`experience_level`、`training_days_per_week`、`training_duration_minutes`、非空 `equipment`、非空 `dietary_preferences`、`allergies` 已明确提交、`safety_confirmed`。

`safety_confirmed=True` 时使用 `utc_now()` 写入时间；改回 `False` 时清空时间。demo 和 repository store 均应保存同一模型，不应在路由层拼接字段。

- [ ] **Step 4: 阻止未完成 Profile 生成计划**

```python
def test_generate_plan_rejects_incomplete_profile(client):
    client.patch("/api/profile/demo-user-945", json={"safety_confirmed": False})
    response = client.post("/api/plans/generate", json={"user_id": "demo-user-945"})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "PROFILE_INCOMPLETE"
```

在 `plan_service.generate_plan()` 调用 Profile 完整度判断，路由将该业务错误转换为 `409 PROFILE_INCOMPLETE`，错误详情包含 `missing_fields`。

- [ ] **Step 5: 运行回归并提交**

Run: `python -m pytest backend/tests/test_profile_settings_advice_api.py backend/tests/test_plans_api.py backend/tests/test_plan_lifecycle.py -q`  
Expected: PASS。

```bash
git add backend/app/models/domain.py backend/app/services/demo_store.py backend/app/services/repository_store.py backend/app/services/plan_service.py backend/app/api/routes_profile.py backend/app/api/routes_plans.py backend/tests/test_profile_settings_advice_api.py backend/tests/test_plan_lifecycle.py
git commit -m "feat: add onboarding profile completion state"
```

### Task 3: 对齐前端领域类型、日期与 PlanContext

**Files:**
- Create: `src/services/dateContext.ts`
- Create: `src/contexts/PlanContext.tsx`
- Modify: `src/types/domain.ts`
- Modify: `src/services/httpApi.ts`
- Modify: `src/services/mockApi.ts`
- Modify: `src/App.tsx`
- Test: `tests/plan-lifecycle.spec.ts`

**Interfaces:**
- Consumes: `api.getCurrentPlan(userId)`、`api.getProfile(userId)`。
- Produces: `usePlanContext(): { profile; currentPlan; coverageStatus; refreshPlanState; today; isLoading; error }`。

- [ ] **Step 1: 写失败的前端状态测试**

```ts
test("routes an expired-plan user to a clear renewal state", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "当前计划没有覆盖今天" })).toBeVisible();
  await expect(page.getByRole("button", { name: "开始创建计划" })).toBeVisible();
});
```

- [ ] **Step 2: 运行测试确认失败**

Run: `npx playwright test tests/plan-lifecycle.spec.ts --project=http`  
Expected: FAIL，API 类型仍直接返回 `Plan` 或页面没有稳定空态。

- [ ] **Step 3: 添加统一日期和计划状态 Context**

```ts
export const appToday = import.meta.env.VITE_945_REFERENCE_DATE ?? new Date().toISOString().slice(0, 10);

export type CurrentPlanData = {
  plan: Plan | null;
  coverage_status: "active_today" | "expired" | "none";
};
```

`PlanContext` 在用户身份可用后并发读取 Profile 和 CurrentPlan，提供 `refreshPlanState()`；`App.tsx` 用 Provider 包裹业务页面。更新 HTTP/mock API 让 `getCurrentPlan` 返回 `CurrentPlanData`，逐一修正已有调用方，不允许以 `demoPlan` 回退写入。

- [ ] **Step 4: 增加 Context 行为断言并运行通过**

```ts
await page.getByRole("button", { name: "开始创建计划" }).click();
await expect(page).toHaveURL(/\/onboarding$/);
```

Run: `npm run build && npx playwright test tests/plan-lifecycle.spec.ts --project=http`  
Expected: PASS。

- [ ] **Step 5: 提交**

```bash
git add src/services/dateContext.ts src/contexts/PlanContext.tsx src/types/domain.ts src/services/httpApi.ts src/services/mockApi.ts src/App.tsx tests/plan-lifecycle.spec.ts
git commit -m "feat: add shared active plan context"
```

### Task 4: 将建档改为六步表单和 Agent 辅助面板

**Files:**
- Create: `src/components/onboarding/OnboardingAssistant.tsx`
- Create: `src/components/onboarding/OnboardingStepForm.tsx`
- Modify: `src/pages/OnboardingPage.tsx`
- Modify: `src/i18n.ts`
- Modify: `src/styles.css`
- Test: `tests/plan-lifecycle.spec.ts`

**Interfaces:**
- Consumes: `usePlanContext()`、`api.updateProfile()`、`api.generatePlan()`。
- Produces: 经 Profile 保存后创建的 `draft Plan`，并导航 `/plan?draft=<plan_id>`。

- [ ] **Step 1: 写失败的分步流程测试**

```ts
test("creates a draft but does not activate it from onboarding", async ({ page, request }) => {
  await page.goto("/onboarding");
  await page.getByRole("button", { name: "下一步" }).click();
  await expect(page.getByText("请填写昵称")).toBeVisible();
  // Fill all six steps, including the safety checkbox.
  await page.getByRole("button", { name: "生成计划草稿" }).click();
  await expect(page).toHaveURL(/\/plan\?draft=/);
  const current = await (await request.get(`${API_BASE_URL}/api/plans/current?user_id=demo-user-945`)).json();
  expect(current.data.coverage_status).not.toBe("active_today");
});
```

- [ ] **Step 2: 运行测试确认失败**

Run: `npx playwright test tests/plan-lifecycle.spec.ts --project=http -g "creates a draft"`  
Expected: FAIL，现有建档页会直接 accept 并跳转今日页。

- [ ] **Step 3: 实现六步表单与本地草稿**

维护 `OnboardingDraft`，字段严格对应后端 Profile 合约，包含 `display_name`、`unit_system`、`goal_timeframe_weeks`、`training_windows`、`meal_count`、`cooking_preference`、`budget_preference` 和 `safety_confirmed`；没有后端持久化字段的偏好先映射进 `constraints` 的稳定前缀，例如 `meal_count:3`。

每一步只校验本步骤字段；“下一步”失败时渲染字段错误。第六步的生成操作按顺序执行：

```ts
await api.updateProfile(toProfilePatch(draft));
const generated = await api.generatePlan({ user_id, goal: draft.goal });
if (!generated.error) navigate(`/plan?draft=${generated.data.plan_id}`);
```

删除任何 `acceptPlan()` 调用。右侧 `OnboardingAssistant` 只显示当前步骤解释、已填摘要和安全提示；“问 945”链接跳转 `/agent?source=onboarding&step=<number>`，不直接写 Profile。

- [ ] **Step 4: 覆盖校验、草稿和辅助入口**

```ts
await expect(page.getByRole("button", { name: "生成计划草稿" })).toBeDisabled();
await page.getByLabel("我理解 945 不提供医疗诊断或治疗建议").check();
await expect(page.getByRole("link", { name: "向 945 提问" })).toHaveAttribute("href", /source=onboarding/);
```

Run: `npm run build && npx playwright test tests/plan-lifecycle.spec.ts --project=http -g "onboarding"`  
Expected: PASS。

- [ ] **Step 5: 提交**

```bash
git add src/components/onboarding src/pages/OnboardingPage.tsx src/i18n.ts src/styles.css tests/plan-lifecycle.spec.ts
git commit -m "feat: add guided onboarding plan draft flow"
```

### Task 5: 收敛计划页与今日页职责

**Files:**
- Modify: `src/pages/PlanPage.tsx`
- Modify: `src/pages/TodayPage.tsx`
- Modify: `src/routes.ts`
- Modify: `src/i18n.ts`
- Modify: `src/styles.css`
- Test: `tests/plan-lifecycle.spec.ts`

**Interfaces:**
- Consumes: `usePlanContext()`、URL `draft` 查询参数、`api.acceptPlan()`。
- Produces: 明确的 `needs_onboarding`、`needs_plan`、`reviewing_draft` 和 `active_today` 页面状态。

- [ ] **Step 1: 写失败的职责边界测试**

```ts
test("shows only plan renewal actions on Today when no active plan covers today", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("button", { name: "开始创建计划" })).toBeVisible();
  await expect(page.getByText("确认智能教练草稿")).toHaveCount(0);
  await expect(page.getByPlaceholder("今天深蹲做了 4 组，每组 8 次，80kg，感觉很累。")).toHaveCount(0);
});
```

- [ ] **Step 2: 运行测试确认失败**

Run: `npx playwright test tests/plan-lifecycle.spec.ts --project=http -g "renewal actions"`  
Expected: FAIL，Today 仍存在聊天输入或记录草稿弹窗。

- [ ] **Step 3: 精简两个页面**

`TodayPage` 使用 `coverageStatus` 分支：无有效计划时仅显示“开始创建计划”和“查看旧计划”；有效计划时展示下一项训练、下一餐、打卡与建议摘要。删除 `agentMessage`、`agentReply`、`recordDraft`、`sendAgentMessage()`、`confirmRecordDraft()` 和 Today 直接保存训练的逻辑；训练 CTA 跳转 `/workout`。

`PlanPage` 使用 query 参数优先加载草稿，再显示 active plan。草稿页只提供“修改资料”“询问 945”“启用计划”；`accept()` 成功后执行 `await refreshPlanState()` 并导航 `/`。将计划调整按钮改为入队 `ActionDraft`，不直接弹出确认对话框。

- [ ] **Step 4: 运行接受后跳转回归**

```ts
await page.goto("/plan?draft=plan-draft-id");
await page.getByRole("button", { name: "启用计划" }).click();
await expect(page).toHaveURL("/");
await expect(page.getByRole("heading", { name: /今日/ })).toBeVisible();
```

Run: `npm run build && npx playwright test tests/plan-lifecycle.spec.ts --project=http -g "renewal|activate"`  
Expected: PASS。

- [ ] **Step 5: 提交**

```bash
git add src/pages/PlanPage.tsx src/pages/TodayPage.tsx src/routes.ts src/i18n.ts src/styles.css tests/plan-lifecycle.spec.ts
git commit -m "feat: separate plan lifecycle from today actions"
```

### Task 6: 实现全局 ActionDraft 队列并收敛 Agent 确认

**Files:**
- Create: `src/contexts/ActionDraftContext.tsx`
- Modify: `src/App.tsx`
- Modify: `src/pages/AgentPage.tsx`
- Modify: `src/pages/AdvicePage.tsx`
- Modify: `src/pages/PlanPage.tsx`
- Modify: `src/types/domain.ts`
- Modify: `src/services/recordDraft.ts`
- Test: `tests/plan-lifecycle.spec.ts`

**Interfaces:**
- Produces: `useActionDrafts(): { drafts; enqueue; dismiss; confirm; retry }`。
- `confirm(draftId)` 只在 `saveRecordDraft()` 返回无错误时把状态改为 `confirmed`。

- [ ] **Step 1: 写失败的队列行为测试**

```ts
test("keeps a plan adjustment pending until Agent confirmation", async ({ page, request }) => {
  await page.goto("/advice");
  await page.getByRole("button", { name: "生成调整草稿" }).click();
  await expect(page).toHaveURL(/\/agent\?draft=/);
  const before = await currentPlanId(request);
  await page.getByRole("button", { name: "确认" }).click();
  await expect.poll(() => currentPlanId(request)).not.toBe(before);
});
```

- [ ] **Step 2: 运行测试确认失败**

Run: `npx playwright test tests/plan-lifecycle.spec.ts --project=http -g "pending until Agent"`  
Expected: FAIL，现有 `agentDraft` 只能传递单项且 Advice/Plan 各自管理状态。

- [ ] **Step 3: 实现队列、确认和失败重试**

在 `domain.ts` 添加：

```ts
export type ActionDraft = {
  draft_id: string;
  source: "agent" | "advice" | "plan";
  record_draft: RecordDraft;
  context: { user_id: string; plan_id?: string; date: string; source_page: RouteId };
  status: "pending" | "confirmed" | "dismissed" | "failed";
  created_at: string;
  error_message?: string;
};
```

`ActionDraftContext` 将队列写入 `sessionStorage` 键 `945.action-drafts.v1`，以便页面刷新不丢失；Agent 消息载有草稿时去重入队。`AgentPage` 逐项展示摘要、影响范围、确认、取消和失败重试。`PlanPage`、`AdvicePage` 只调用 `enqueue()` 后导航 Agent；移除 `App.tsx` 的 `agentDraft` state 和跨页面 props。

- [ ] **Step 4: 验证没有确认时无写入且失败项可重试**

```ts
await expect(page.getByText("待确认操作")).toBeVisible();
await page.getByRole("button", { name: "取消" }).click();
expect(await countWorkoutLogs(request)).toBe(beforeCount);
```

Run: `npm run build && npx playwright test tests/plan-lifecycle.spec.ts --project=http -g "Agent|pending"`  
Expected: PASS。

- [ ] **Step 5: 提交**

```bash
git add src/contexts/ActionDraftContext.tsx src/App.tsx src/pages/AgentPage.tsx src/pages/AdvicePage.tsx src/pages/PlanPage.tsx src/types/domain.ts src/services/recordDraft.ts tests/plan-lifecycle.spec.ts
git commit -m "feat: centralize confirmation-required agent drafts"
```

### Task 7: 让训练与饮食执行页仅使用真实计划和日志

**Files:**
- Modify: `src/pages/WorkoutPage.tsx`
- Modify: `src/pages/DietPage.tsx`
- Modify: `src/services/httpApi.ts`
- Modify: `src/services/mockApi.ts`
- Modify: `src/i18n.ts`
- Test: `tests/plan-lifecycle.spec.ts`
- Test: `tests/http-integration.spec.ts`

**Interfaces:**
- Consumes: `usePlanContext().currentPlan`、计划日、现有 `saveWorkoutLog` 与 `saveManualMeal` 接口。
- Produces: 每组由受控状态生成 `WorkoutLog.exercises`；每份手动食物由用户输入生成 `MealLog.foods`。

- [ ] **Step 1: 写失败的执行页测试**

```ts
test("does not show a synthetic workout when no plan is active", async ({ page }) => {
  await page.goto("/workout");
  await expect(page.getByText("没有可执行的训练计划")).toBeVisible();
  await expect(page.getByRole("button", { name: "完成训练" })).toHaveCount(0);
});

test("writes the edited set values instead of defaults", async ({ page, request }) => {
  await activatePlan(request);
  await page.goto("/workout");
  await page.getByLabel("深蹲 第 1 组重量").fill("82.5");
  await page.getByLabel("深蹲 第 1 组次数").fill("7");
  await page.getByRole("button", { name: "保存训练记录" }).click();
  expect((await latestWorkoutLog(request)).exercises[0].sets[0]).toMatchObject({ weight_kg: 82.5, reps: 7 });
});
```

- [ ] **Step 2: 运行测试确认失败**

Run: `npx playwright test tests/plan-lifecycle.spec.ts --project=http -g "synthetic workout|edited set"`  
Expected: FAIL，当前页面仍使用默认输入和 `demoPlan.plan_id`。

- [ ] **Step 3: 实现真实训练、餐食和统一空态**

训练页用 selected plan day 初始化 `ExerciseSetLog[][]` 受控 state；label 固定为 `${exercise.name} 第 ${setIndex + 1} 组重量` 与 `${exercise.name} 第 ${setIndex + 1} 组次数`。保存时只发送用户当前值和 completion 状态；没有 active plan 时展示引导 `/plan` 的空态。

饮食页以 `currentPlan.plan_id` 和选中日期确认计划餐；手动餐食 UI 至少有食物名、份量、热量、蛋白、碳水、脂肪输入并支持添加/删除行。删除静态饮食调整卡、静态采购清单和固定宏量食物。没有 active plan 时只展示计划续建入口。

- [ ] **Step 4: 验证真实数据与日志回归**

```ts
await page.getByRole("button", { name: "添加食物" }).click();
await page.getByLabel("食物 1 热量").fill("510");
await page.getByRole("button", { name: "保存手动餐食" }).click();
expect((await latestMealLog(request)).foods[0].calories).toBe(510);
```

Run: `npm run build && npx playwright test tests/plan-lifecycle.spec.ts tests/http-integration.spec.ts --project=http`  
Expected: PASS。

- [ ] **Step 5: 提交**

```bash
git add src/pages/WorkoutPage.tsx src/pages/DietPage.tsx src/services/httpApi.ts src/services/mockApi.ts src/i18n.ts tests/plan-lifecycle.spec.ts tests/http-integration.spec.ts
git commit -m "feat: record real workout and meal execution data"
```

### Task 8: 调整路由守卫、建议和设置入口

**Files:**
- Modify: `src/App.tsx`
- Modify: `src/routes.ts`
- Modify: `src/pages/AdvicePage.tsx`
- Modify: `src/pages/SettingsPage.tsx`
- Modify: `src/components/business/AppShell.tsx`
- Modify: `src/i18n.ts`
- Test: `tests/plan-lifecycle.spec.ts`

**Interfaces:**
- Consumes: `PlanContext.coverageStatus` 与 `profile.profile_completion`。
- Produces: 从任意执行入口回到正确的建档、计划审阅或今日状态，不产生页面内的第二套生成/接受流程。

- [ ] **Step 1: 写失败的入口一致性测试**

```ts
test("sends incomplete users from execution routes to onboarding", async ({ page }) => {
  await page.goto("/diet");
  await expect(page.getByRole("link", { name: "开始创建计划" })).toHaveAttribute("href", "/onboarding");
});

test("does not offer direct plan acceptance from settings", async ({ page }) => {
  await page.goto("/settings");
  await expect(page.getByRole("button", { name: /接受计划|启用计划/ })).toHaveCount(0);
});
```

- [ ] **Step 2: 运行测试确认失败**

Run: `npx playwright test tests/plan-lifecycle.spec.ts --project=http -g "incomplete users|settings"`  
Expected: FAIL，设置页还包含计划预览和接受路径。

- [ ] **Step 3: 实现唯一入口规则**

在 `App` 页面层创建 `resolveProductEntry(profile, coverageStatus, routeId)`：

```ts
if (profile.profile_completion === "incomplete" && ["today", "workout", "diet"].includes(routeId)) return "/onboarding";
if (coverageStatus !== "active_today" && ["workout", "diet"].includes(routeId)) return "/plan";
return null;
```

将 Settings 的“保存并生成计划预览/接受”替换为“更新长期偏好”和“重新建立资料”链接；Advice 的每个计划改变建议只进入 `ActionDraftContext`。AppShell 保持现有导航样式，只根据状态提供状态标签和正确跳转。

- [ ] **Step 4: 运行路由与建议回归**

Run: `npm run build && npx playwright test tests/plan-lifecycle.spec.ts --project=http -g "incomplete users|settings|advice"`  
Expected: PASS。

- [ ] **Step 5: 提交**

```bash
git add src/App.tsx src/routes.ts src/pages/AdvicePage.tsx src/pages/SettingsPage.tsx src/components/business/AppShell.tsx src/i18n.ts tests/plan-lifecycle.spec.ts
git commit -m "feat: unify product entry and plan adjustment routes"
```

### Task 9: 更新接口文档、全量回归与手工验收

**Files:**
- Modify: `docs/API_CONTRACT.md`
- Modify: `backend/README.md`
- Modify: `docs/superpowers/specs/2026-07-26-onboarding-plan-lifecycle-design.md`
- Test: `backend/tests/test_plan_lifecycle.py`
- Test: `tests/plan-lifecycle.spec.ts`

**Interfaces:**
- Documents: `CurrentPlanResponse`、Profile completion、安全确认、ActionDraft 确认边界。

- [ ] **Step 1: 补充文档的可验证接口示例**

在 `API_CONTRACT.md` 用下列形状替换旧的 `GET /api/plans/current` 响应说明：

```json
{
  "data": {
    "plan": null,
    "coverage_status": "expired"
  },
  "error": null
}
```

记录 `PROFILE_INCOMPLETE` 的 409 响应、`safety_confirmed` 字段、以及所有 RecordDraft 必须确认后才写入的规则。`backend/README.md` 说明 demo 与 Mongo 模式都遵守相同生命周期。

- [ ] **Step 2: 运行完整后端和前端验证**

Run: `python -m pytest backend/tests -q`  
Expected: PASS。

Run: `npm run build`  
Expected: PASS。

Run: `npm run qa:http`  
Expected: PASS，包含新增首次建档、计划过期、草稿启用、Agent 确认、训练与饮食执行场景。

- [ ] **Step 3: 手工浏览器验收**

在 HTTP 模式下验证以下链路，记录截图或失败原因：

1. 过期计划打开 `/`，仅看到续建入口。
2. 六步建档完成安全确认，生成草稿后停留计划页。
3. 未点击启用时，`/workout` 与 `/diet` 不展示执行数据。
4. 启用后回到 `/`，今日训练和餐食来自新的 active plan。
5. Advice 生成调整草稿，Agent 取消时没有计划写入，确认时才产生调整后的 active plan。
6. 训练和饮食手动编辑后，重新加载仍显示 API 保存的日志。

- [ ] **Step 4: 代码卫生检查与提交**

Run: `git diff --check`  
Expected: 无输出。

```bash
git add docs/API_CONTRACT.md backend/README.md docs/superpowers/specs/2026-07-26-onboarding-plan-lifecycle-design.md backend/tests/test_plan_lifecycle.py tests/plan-lifecycle.spec.ts
git commit -m "docs: document onboarding plan lifecycle"
```

## Plan Self-Review

- **规格覆盖**：Task 1-2 覆盖生命周期、Profile 完整度和安全确认；Task 3-5 覆盖统一数据、建档、审阅与今日职责；Task 6-8 覆盖草稿确认、执行页去静态化和页面入口；Task 9 覆盖文档、自动化与手工验收。
- **范围控制**：没有加入移动端、鉴权重做、视觉导航重做、医疗能力或新的外部模型依赖。
- **类型一致性**：后端 `CurrentPlanResponse` 对应前端 `CurrentPlanData`；`ActionDraft` 的 `record_draft` 保持既有 `RecordDraft` 合约；所有日志写入从 `PlanContext.currentPlan.plan_id` 取得计划 ID。
- **无占位检查**：计划没有 `TODO`、`TBD` 或“稍后实现”条目；每项任务给出失败测试、实现接口、运行命令和提交范围。
