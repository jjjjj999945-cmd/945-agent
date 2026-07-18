# 945 Real HTTP Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 945 桌面客户端通过可重复运行的 HTTP 模式连接真实 FastAPI，并端到端证明页面写入、Agent 草稿确认和错误状态符合既定边界。

**Architecture:** 新增独立的 Vite HTTP mode 和 Playwright 双服务配置，测试进程同时启动 FastAPI `:8000` 与 Vite `:5177`。普通开发仍使用 `mockApi`；HTTP QA 使用 demo store 和 deterministic Provider，通过页面操作及后端查询共同验证真实写入。

**Tech Stack:** React 19、TypeScript、Vite 7、Playwright、FastAPI、Pydantic、pytest。

## Global Constraints

- 联调固定使用 `945_STORAGE_BACKEND=demo` 和 `945_LLM_PROVIDER=deterministic`。
- demo 用户固定为 `demo-user-945`，业务日期沿用 `TODAY_DATE=2026-07-11`。
- 只验证桌面 Chrome，不增加移动端配置或样式。
- 普通 `npm run dev` 与 `npm run qa:app` 保持 mock 模式。
- Agent 在用户确认前不得写入训练、饮食或计划数据。
- 计划调整草稿在本阶段不修改计划。
- 不调用真实 OpenAI，不启动 MongoDB，不增加生产鉴权。

---

### Task 1: 建立双服务 HTTP QA 入口

**Files:**
- Create: `.env.http`
- Create: `playwright.http.config.ts`
- Create: `tests/http-integration.spec.ts`
- Modify: `package.json`

**Interfaces:**
- Consumes: `VITE_945_API_MODE`、`VITE_945_API_BASE_URL`、FastAPI `/health`、现有 `/app` 页面。
- Produces: `npm run dev:http` 与 `npm run qa:http`，后续任务在 `tests/http-integration.spec.ts` 中追加场景。

- [ ] **Step 1: 写入首个真实链路测试**

在 `tests/http-integration.spec.ts` 创建：

```ts
import { expect, test } from "@playwright/test";

const API_BASE_URL = "http://127.0.0.1:8000";

test.describe.serial("945 real HTTP integration", () => {
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
});
```

- [ ] **Step 2: 运行测试并确认入口缺失**

Run: `npm run qa:http`

Expected: FAIL with `Missing script: "qa:http"`。

- [ ] **Step 3: 添加 HTTP mode 与 Playwright 双服务配置**

创建 `.env.http`：

```dotenv
VITE_945_API_MODE=http
VITE_945_API_BASE_URL=http://127.0.0.1:8000
```

创建 `playwright.http.config.ts`：

```ts
import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  testMatch: "http-integration.spec.ts",
  timeout: 30_000,
  expect: { timeout: 10_000 },
  workers: 1,
  use: {
    baseURL: "http://127.0.0.1:5177",
    channel: "chrome",
    headless: true,
    trace: "retain-on-failure"
  },
  projects: [
    {
      name: "chrome-desktop-http",
      use: { ...devices["Desktop Chrome"], channel: "chrome" }
    }
  ],
  webServer: [
    {
      command: "python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000",
      url: "http://127.0.0.1:8000/health",
      reuseExistingServer: false,
      timeout: 60_000
    },
    {
      command: "npm run dev:http",
      url: "http://127.0.0.1:5177/app",
      reuseExistingServer: false,
      timeout: 60_000
    }
  ]
});
```

在 `package.json` 的 `scripts` 中加入：

```json
"dev:http": "vite --host 127.0.0.1 --port 5177 --mode http",
"qa:http": "playwright test --config=playwright.http.config.ts"
```

- [ ] **Step 4: 运行真实链路测试**

Run: `npm run qa:http`

Expected: PASS, `1 passed`，并且请求命中 `http://127.0.0.1:8000/api/today`。

- [ ] **Step 5: 提交运行入口**

```powershell
git add .env.http package.json playwright.http.config.ts tests/http-integration.spec.ts
git commit -m "test: add real http integration harness"
```

---

### Task 2: 归一化 HTTP 错误并让加载失败可见

**Files:**
- Create: `src/components/business/PageLoadState.tsx`
- Modify: `src/services/httpApi.ts`
- Modify: `src/pages/TodayPage.tsx`
- Modify: `src/pages/WorkoutPage.tsx`
- Modify: `src/pages/DietPage.tsx`
- Modify: `src/pages/BodyPage.tsx`
- Modify: `src/pages/AdvicePage.tsx`
- Modify: `src/pages/SettingsPage.tsx`
- Modify: `tests/http-integration.spec.ts`

**Interfaces:**
- Consumes: FastAPI 默认 `422 { detail: [...] }` 与统一 `{ data, error }` 响应。
- Produces: `httpApi` 稳定错误码 `NETWORK_ERROR`、`VALIDATION_ERROR`、`HTTP_ERROR`；`PageLoadState({ message })` 显示初始加载失败。

- [ ] **Step 1: 添加三个失败响应测试**

在 HTTP describe 中追加：

```ts
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
```

- [ ] **Step 2: 运行测试并确认当前页面停留在 Loading**

Run: `npm run qa:http -- --grep "errors|non-JSON|aborted"`

Expected: FAIL，因为 `request()` 强制把响应转换成 `ApiResponse<T>`，且数据为空时页面不显示 `notice`。

- [ ] **Step 3: 实现响应形状检查与错误归一化**

在 `src/services/httpApi.ts` 中加入并替换 `request()`：

```ts
function isApiResponse<T>(value: unknown): value is ApiResponse<T> {
  if (!value || typeof value !== "object") return false;
  const candidate = value as { data?: unknown; error?: unknown };
  if (!("data" in candidate) || !("error" in candidate)) return false;
  if (candidate.error === null) return candidate.data !== null;
  if (candidate.data !== null || !candidate.error || typeof candidate.error !== "object") return false;
  const errorValue = candidate.error as { code?: unknown; message?: unknown };
  return typeof errorValue.code === "string" && typeof errorValue.message === "string";
}

async function request<T>(path: string, init?: RequestInit): Promise<ApiResponse<T>> {
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers }
    });

    let body: unknown;
    try {
      body = await response.json();
    } catch {
      return fail("HTTP_ERROR", "945 backend returned an invalid response.", {
        status: response.status,
        path
      });
    }

    if (isApiResponse<T>(body)) return body;
    if (response.status === 422) {
      return fail("VALIDATION_ERROR", "Request validation failed.", {
        status: response.status,
        detail: (body as { detail?: unknown }).detail
      });
    }
    return fail("HTTP_ERROR", "945 backend returned an invalid response.", {
      status: response.status,
      path
    });
  } catch (error) {
    return fail("NETWORK_ERROR", "Unable to reach 945 backend.", {
      base_url: API_BASE_URL,
      message: error instanceof Error ? error.message : String(error)
    });
  }
}
```

创建 `src/components/business/PageLoadState.tsx`：

```tsx
export function PageLoadState({ message }: { message: string }) {
  return <div className="business-placeholder" role="status">{message}</div>;
}
```

在六个数据页面导入 `PageLoadState`，并将空数据 guard 分别改为：

```tsx
// TodayPage.tsx
if (!today || !summary) return <PageLoadState message={notice || t("status.loading")} />;

// WorkoutPage.tsx, DietPage.tsx, BodyPage.tsx, AdvicePage.tsx, SettingsPage.tsx
if (!data) return <PageLoadState message={notice || t("status.loading")} />;
```

- [ ] **Step 4: 验证错误测试与 mock 回归**

Run: `npm run qa:http -- --grep "errors|non-JSON|aborted"`

Expected: PASS, `3 passed`。

Run: `npm run qa:app`

Expected: PASS, 现有 mock 测试数量不减少。

- [ ] **Step 5: 提交错误边界**

```powershell
git add src/components/business/PageLoadState.tsx src/services/httpApi.ts src/pages tests/http-integration.spec.ts
git commit -m "fix: normalize frontend http errors"
```

---

### Task 3: 证明页面结构化写入经过 FastAPI

**Files:**
- Modify: `tests/http-integration.spec.ts`
- Modify only if a failing assertion exposes a contract defect: `src/pages/TodayPage.tsx`
- Modify only if a failing assertion exposes a contract defect: `src/pages/WorkoutPage.tsx`
- Modify only if a failing assertion exposes a contract defect: `src/pages/BodyPage.tsx`
- Modify only if a failing assertion exposes a contract defect: `src/services/httpApi.ts`

**Interfaces:**
- Consumes: `POST /api/meal-logs/confirm-planned-meal`、`POST /api/daily-checkins`、`POST /api/body-metrics`、`POST /api/workout-logs`。
- Produces: 由浏览器操作触发且可从 FastAPI GET 接口读回的结构化事实。

- [ ] **Step 1: 添加真实写入测试**

在 HTTP describe 中追加一个顺序测试：

```ts
  test("persists page mutations through FastAPI", async ({ page, request }) => {
    await page.goto("/app");

    const mealLogsBefore = await (await request.get(`${API_BASE_URL}/api/meal-logs?user_id=demo-user-945`)).json();
    await page.getByRole("button", { name: "确认" }).first().click();
    await expect(page.getByText("早餐 已保存")).toBeVisible();
    const mealLogsAfter = await (await request.get(`${API_BASE_URL}/api/meal-logs?user_id=demo-user-945`)).json();
    expect(mealLogsAfter.data).toHaveLength(mealLogsBefore.data.length + 1);

    await page.getByLabel("体重 kg").fill("75.4");
    await page.getByLabel("睡眠小时").fill("7.5");
    await page.getByRole("button", { name: "保存", exact: true }).click();
    const today = await (await request.get(`${API_BASE_URL}/api/today?user_id=demo-user-945&date=2026-07-11`)).json();
    expect(today.data.daily_checkin).toMatchObject({ weight_kg: 75.4, sleep_hours: 7.5 });

    await page.goto("/body");
    await page.getByLabel("体重 kg").fill("74.9");
    await page.getByRole("button", { name: "保存身体数据" }).click();
    const metrics = await (await request.get(`${API_BASE_URL}/api/body-metrics?user_id=demo-user-945`)).json();
    expect(metrics.data.at(-1)).toMatchObject({ weight_kg: 74.9, date: "2026-07-11" });

    await page.goto("/workout");
    const workoutLogsBefore = await (await request.get(`${API_BASE_URL}/api/workout-logs?user_id=demo-user-945`)).json();
    await page.getByRole("button", { name: "完成训练" }).click();
    await expect(page.getByText("训练记录已保存")).toBeVisible();
    const workoutLogsAfter = await (await request.get(`${API_BASE_URL}/api/workout-logs?user_id=demo-user-945`)).json();
    expect(workoutLogsAfter.data).toHaveLength(workoutLogsBefore.data.length + 1);
  });
```

- [ ] **Step 2: 运行测试并记录首个真实契约失败**

Run: `npm run qa:http -- --grep "persists page mutations"`

Expected: 测试必须命中四个真实 POST；若失败，输出应明确指出字段、页面刷新或 locator 的首个不一致。禁止把断言改成只检查 notice。

- [ ] **Step 3: 只修复测试暴露的契约缺陷**

修复规则：

```ts
// 页面成功分支必须等待真实响应并刷新数据
if (response.error) {
  setNotice(response.error.message);
  return;
}
setNotice(successMessage);
await loadCurrentPageData();
```

请求字段必须保持 `src/types/domain.ts` 与 `backend/app/models/domain.py` 的现有名称，不添加前端别名层。

- [ ] **Step 4: 再次运行结构化写入测试**

Run: `npm run qa:http -- --grep "persists page mutations"`

Expected: PASS，且四个 GET 验证都读到新增事实。

- [ ] **Step 5: 提交页面联调修复**

```powershell
git add tests/http-integration.spec.ts src/pages src/services/httpApi.ts
git commit -m "test: verify real structured writes"
```

---

### Task 4: 实现 Agent 草稿确认后的结构化写入

**Files:**
- Create: `src/services/recordDraft.ts`
- Modify: `src/pages/TodayPage.tsx`
- Modify: `src/pages/AgentPage.tsx`
- Modify: `tests/http-integration.spec.ts`

**Interfaces:**
- Consumes: `RecordDraft`、`api.saveWorkoutLog()`、`api.saveManualMeal()`、`DEMO_USER_ID`、`TODAY_DATE`。
- Produces: `saveRecordDraft(draft, context): Promise<ApiResponse<WorkoutLog | MealLog>>`；不支持的草稿返回 `DRAFT_TYPE_UNSUPPORTED`。

- [ ] **Step 1: 添加确认前后写入与安全输入测试**

在 HTTP describe 中追加：

```ts
  test("writes Agent workout and meal drafts only after confirmation", async ({ page, request }) => {
    await page.goto("/agent");
    const input = page.getByPlaceholder("今天深蹲做了 4 组，每组 8 次，80kg，感觉很累。");

    const workoutBefore = await (await request.get(`${API_BASE_URL}/api/workout-logs?user_id=demo-user-945`)).json();
    await input.fill("今天深蹲做了 4 组，每组 8 次，80kg，感觉很累。");
    await page.getByRole("button", { name: "发送" }).click();
    await expect(page.getByRole("heading", { name: "确认智能教练草稿" })).toBeVisible();
    const workoutUnconfirmed = await (await request.get(`${API_BASE_URL}/api/workout-logs?user_id=demo-user-945`)).json();
    expect(workoutUnconfirmed.data).toHaveLength(workoutBefore.data.length);
    await page.getByRole("dialog").getByRole("button", { name: "确认" }).click();
    await expect(page.getByText("智能教练草稿已确认")).toBeVisible();
    const workoutConfirmed = await (await request.get(`${API_BASE_URL}/api/workout-logs?user_id=demo-user-945`)).json();
    expect(workoutConfirmed.data).toHaveLength(workoutBefore.data.length + 1);

    const mealBefore = await (await request.get(`${API_BASE_URL}/api/meal-logs?user_id=demo-user-945`)).json();
    await input.fill("我中午吃了鸡胸肉饭，可以帮我记录吗？");
    await page.getByRole("button", { name: "发送" }).click();
    await expect(page.getByRole("heading", { name: "确认智能教练草稿" })).toBeVisible();
    const mealUnconfirmed = await (await request.get(`${API_BASE_URL}/api/meal-logs?user_id=demo-user-945`)).json();
    expect(mealUnconfirmed.data).toHaveLength(mealBefore.data.length);
    await page.getByRole("dialog").getByRole("button", { name: "确认" }).click();
    await expect(page.getByText("智能教练草稿已确认")).toBeVisible();
    const mealConfirmed = await (await request.get(`${API_BASE_URL}/api/meal-logs?user_id=demo-user-945`)).json();
    expect(mealConfirmed.data).toHaveLength(mealBefore.data.length + 1);
  });

  test("keeps high-risk Agent input out of draft confirmation", async ({ page }) => {
    await page.goto("/agent");
    await page.getByPlaceholder("今天深蹲做了 4 组，每组 8 次，80kg，感觉很累。")
      .fill("我训练时胸闷眩晕，还能继续冲重量吗？");
    await page.getByRole("button", { name: "发送" }).click();
    await expect(page.getByText(/暂停训练/).last()).toBeVisible();
    await expect(page.getByRole("heading", { name: "确认智能教练草稿" })).toBeHidden();
  });
```

- [ ] **Step 2: 运行测试并确认草稿未写入**

Run: `npm run qa:http -- --grep "Agent workout|high-risk"`

Expected: workout/meal 确认测试 FAIL，因为两个页面当前只关闭弹窗；高风险测试 PASS。

- [ ] **Step 3: 创建草稿转换服务**

创建 `src/services/recordDraft.ts`：

```ts
import type { MealLog, RecordDraft, WorkoutLog } from "../types/domain";
import { api } from "./apiClient";
import { fail, type ApiResponse } from "./apiTypes";

type DraftContext = { user_id: string; date: string; plan_id?: string };

function numberField(payload: Record<string, unknown>, key: string) {
  const value = payload[key];
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

export async function saveRecordDraft(
  draft: RecordDraft,
  context: DraftContext
): Promise<ApiResponse<WorkoutLog | MealLog>> {
  const payload = draft.payload;
  if (draft.type === "workout_log") {
    const exerciseName = typeof payload.exercise_name === "string" ? payload.exercise_name : "";
    const sets = numberField(payload, "sets");
    const reps = numberField(payload, "reps");
    const weight = numberField(payload, "weight_kg");
    if (!exerciseName || !sets || !reps) {
      return fail("INVALID_DRAFT", "Workout draft is missing required fields.");
    }
    return api.saveWorkoutLog({
      user_id: context.user_id,
      plan_id: context.plan_id,
      date: context.date,
      status: "completed",
      exercises: [{
        name: exerciseName,
        sets: Array.from({ length: sets }, () => ({ reps, weight_kg: weight ?? undefined, completed: true }))
      }],
      notes: typeof payload.effort_note === "string" ? payload.effort_note : undefined
    });
  }
  if (draft.type === "meal_log") {
    const mealName = typeof payload.meal_name === "string" ? payload.meal_name : "";
    if (!mealName) return fail("INVALID_DRAFT", "Meal draft is missing a meal name.");
    return api.saveManualMeal({
      user_id: context.user_id,
      plan_id: context.plan_id,
      date: context.date,
      meal_name: mealName,
      foods: [],
      notes: typeof payload.note === "string" ? payload.note : undefined
    });
  }
  return fail("DRAFT_TYPE_UNSUPPORTED", "This draft type cannot be saved yet.", { type: draft.type });
}
```

空 `foods` 明确表示 Agent 尚未提供可靠宏量营养信息；本阶段不编造热量和蛋白质。

- [ ] **Step 4: 把 Today 和 Agent 确认按钮接到服务**

两个页面导入：

```ts
import { saveRecordDraft } from "../services/recordDraft";
```

`TodayPage.tsx` 使用：

```ts
async function confirmRecordDraft() {
  if (!recordDraft) return;
  setSaving(true);
  const response = await saveRecordDraft(recordDraft, {
    user_id: DEMO_USER_ID,
    date: TODAY_DATE,
    plan_id: demoPlan.plan_id
  });
  setSaving(false);
  if (response.error) {
    setNotice(response.error.message);
    return;
  }
  setNotice(`${draftTypeLabels[recordDraft.type]} ${t("status.saved")}`);
  setRecordDraft(null);
  await loadToday();
}
```

`AgentPage.tsx` 使用：

```ts
async function confirmDraft() {
  if (!draft) return;
  const response = await saveRecordDraft(draft, {
    user_id: DEMO_USER_ID,
    date: TODAY_DATE
  });
  if (response.error) {
    setNotice(response.error.message);
    return;
  }
  setDraft(null);
  setNotice(t("status.agentDraftConfirmed"));
}
```

两个 `ConfirmDialog` 的 `onConfirm` 保持传入函数引用，React 可以接受 async event handler；静态“同步到 Garmin”按钮不得调用草稿确认函数，改为只显示后续能力提示。

- [ ] **Step 5: 验证 Agent 边界**

Run: `npm run qa:http -- --grep "Agent workout|high-risk"`

Expected: PASS，确认前日志数量不变，确认后只增加一条，高风险输入无 dialog。

- [ ] **Step 6: 提交草稿确认写入**

```powershell
git add src/services/recordDraft.ts src/pages/TodayPage.tsx src/pages/AgentPage.tsx tests/http-integration.spec.ts
git commit -m "feat: persist confirmed agent drafts"
```

---

### Task 5: 更新中文运行文档并做全量回归

**Files:**
- Modify: `README.md`
- Modify: `backend/README.md`
- Modify: `docs/API_CONTRACT.md`

**Interfaces:**
- Consumes: Task 1-4 已通过的命令和行为。
- Produces: mock、HTTP、OpenAI 可选模式的中文运行说明及真实草稿确认契约。

- [ ] **Step 1: 更新根 README 当前阶段**

把“当前仓库还不是完整后端 Agent 系统”改为当前事实，并加入：

````markdown
## 真实 HTTP 联调

默认 mock 开发：

```powershell
npm run dev
```

手动 HTTP 开发需要分别启动后端与前端：

```powershell
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
npm run dev:http
```

自动端到端联调：

```powershell
npm run qa:http
```
````

- [ ] **Step 2: 更新后端 README 与 API contract**

明确写入：

```markdown
- `/api/agent/chat` 只返回草稿。
- 前端确认 workout draft 后调用 `POST /api/workout-logs`。
- 前端确认 meal draft 后调用 `POST /api/meal-logs`。
- plan adjustment draft 暂不写入计划。
- `npm run qa:http` 使用 demo store 和 deterministic Provider，不需要 API Key 或 MongoDB。
```

- [ ] **Step 3: 运行完整后端测试**

Run: `python -m pytest backend/tests -q`

Expected: `104 passed, 2 skipped` 或更多通过用例，0 failed。

- [ ] **Step 4: 运行前端构建与两套 QA**

Run: `npm run build`

Expected: exit 0。

Run: `npm run qa:app`

Expected: 现有 mock 测试全部通过。

Run: `npm run qa:http`

Expected: HTTP 测试全部通过，0 failed。

- [ ] **Step 5: 检查代码卫生并提交文档**

Run: `git diff --check`

Expected: 无输出，exit 0。

Run: `git status --short`

Expected: 仅包含本任务三份文档。

```powershell
git add README.md backend/README.md docs/API_CONTRACT.md
git commit -m "docs: document real http workflow"
```

---

## Final Verification

依次运行：

```powershell
python -m pytest backend/tests -q
npm run build
npm run qa:app
npm run qa:http
git diff --check
git status --short --branch
```

完成标准：后端、构建、mock QA、HTTP QA 全部通过；工作树干净；未调用 OpenAI；未依赖 MongoDB。
