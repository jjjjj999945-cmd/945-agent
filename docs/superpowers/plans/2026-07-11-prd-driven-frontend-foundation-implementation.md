# 945 PRD 驱动前端基础实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将当前 Stitch 包装层迁移为 PRD 驱动的真实 React 前端基础，保留 Stitch 到 `/prototype/*` 作为视觉参考。

**Architecture:** 主产品入口由 `src/App.tsx` 和真实 route config 驱动，渲染 `AppShell` 与 `src/pages/*` 页面骨架。Stitch 原型保留在 prototype 命名空间，不再作为主产品路由。Mock API 使用内存状态模拟未来后端边界，页面通过 mock API 呈现和更新 demo 数据。

**Tech Stack:** Vite, React 19, TypeScript 5.8, local CSS, local mock data, no new routing/state/UI/chart dependency.

## Global Constraints

- `PRD.md` 是产品单一事实来源。
- `docs/FRONTEND_REQUIREMENTS.md` 是前端细化依据；与 `PRD.md` 冲突时以 `PRD.md` 为准。
- 当前 Stitch reference screens 是视觉参考，不是长期业务实现。
- 产品名固定为 `945`。
- MVP 使用本地 demo 用户 `demo-user-945`，不做登录注册。
- 前端必须保留 `zh-CN` 和 `en-US` i18n 结构，默认中文。
- Agent Chat 最终位置未定；本阶段实现为独立页面加可复用模块语义。
- 饮食 MVP 只支持计划餐确认和手动输入。
- 不做食物图片识别、条形码扫描、外卖平台接入、自动识别餐盘、穿戴设备、支付、社区、排行榜、医疗诊断或康复处方。
- Agent 不允许静默写入关键数据；记录草稿和计划调整必须经过用户确认。
- 本阶段不新增 routing、状态管理、UI 组件或图表依赖。

---

## File Structure

### Create

```text
src/routes.ts
src/pages/OnboardingPage.tsx
src/pages/PlanPage.tsx
src/pages/WorkoutPage.tsx
src/pages/DietPage.tsx
src/pages/BodyPage.tsx
src/pages/AdvicePage.tsx
src/pages/AgentPage.tsx
src/pages/SettingsPage.tsx
src/prototype/StitchPrototype.tsx
src/prototype/screens.ts
src/prototype/stitchDom.ts
docs/PRD_FRONTEND_FOUNDATION_QA.md
```

### Modify

```text
src/App.tsx
src/components/business/AppShell.tsx
src/data/demoData.ts
src/i18n/types.ts
src/i18n/zh-CN.ts
src/i18n/en-US.ts
src/i18n/index.ts
src/pages/PrototypeRouter.tsx
src/services/mockApi.ts
src/types/domain.ts
src/styles.css
```

### Preserve

```text
stitch-reference/
public/stitch-reference/
qa-shots/
design-qa.md
```

---

## Task 1: 真实路由配置和 App 入口

**Files:**
- Create: `src/routes.ts`
- Modify: `src/App.tsx`
- Modify: `src/components/business/AppShell.tsx`

**Interfaces:**
- Produces: `RouteId`, `AppRoute`, `primaryRoutes`, `prototypeRoutes`, `getRouteByPath(pathname)`
- Consumes: existing `Locale`, `AppShell`, `TodayPage`, `PrototypeRouter`

- [ ] **Step 1: 创建 route config**

Create `src/routes.ts`:

```ts
export type RouteId =
  | "today"
  | "onboarding"
  | "plan"
  | "workout"
  | "diet"
  | "body"
  | "advice"
  | "agent"
  | "settings";

export type AppRoute = {
  id: RouteId;
  path: string;
  navKey: string;
  titleKey: string;
  descriptionKey: string;
  primary: boolean;
};

export const primaryRoutes: AppRoute[] = [
  { id: "today", path: "/", navKey: "nav.today", titleKey: "page.today.title", descriptionKey: "page.today.description", primary: true },
  { id: "workout", path: "/workout", navKey: "nav.workout", titleKey: "page.workout.title", descriptionKey: "page.workout.description", primary: true },
  { id: "diet", path: "/diet", navKey: "nav.diet", titleKey: "page.diet.title", descriptionKey: "page.diet.description", primary: true },
  { id: "body", path: "/body", navKey: "nav.body", titleKey: "page.body.title", descriptionKey: "page.body.description", primary: true },
  { id: "advice", path: "/advice", navKey: "nav.advice", titleKey: "page.advice.title", descriptionKey: "page.advice.description", primary: true },
  { id: "agent", path: "/agent", navKey: "nav.agent", titleKey: "page.agent.title", descriptionKey: "page.agent.description", primary: true },
  { id: "settings", path: "/settings", navKey: "nav.settings", titleKey: "page.settings.title", descriptionKey: "page.settings.description", primary: true }
];

export const secondaryRoutes: AppRoute[] = [
  { id: "onboarding", path: "/onboarding", navKey: "nav.onboarding", titleKey: "page.onboarding.title", descriptionKey: "page.onboarding.description", primary: false },
  { id: "plan", path: "/plan", navKey: "nav.plan", titleKey: "page.plan.title", descriptionKey: "page.plan.description", primary: false }
];

export const appRoutes = [...primaryRoutes, ...secondaryRoutes];

export function getRouteByPath(pathname: string) {
  const normalized = pathname === "" ? "/" : pathname.replace(/\/+$/, "") || "/";
  return appRoutes.find((route) => route.path === normalized) ?? primaryRoutes[0];
}

export function isPrototypePath(pathname: string) {
  return pathname === "/prototype" || pathname.startsWith("/prototype/");
}
```

- [ ] **Step 2: 更新 App 入口**

Modify `src/App.tsx` so main product routes are primary and `/prototype/*` renders Stitch:

```tsx
import { useEffect, useState } from "react";
import { AppShell } from "./components/business/AppShell";
import { AgentPage } from "./pages/AgentPage";
import { AdvicePage } from "./pages/AdvicePage";
import { BodyPage } from "./pages/BodyPage";
import { DietPage } from "./pages/DietPage";
import { OnboardingPage } from "./pages/OnboardingPage";
import { PlanPage } from "./pages/PlanPage";
import { PrototypeRouter } from "./pages/PrototypeRouter";
import { SettingsPage } from "./pages/SettingsPage";
import { TodayPage } from "./pages/TodayPage";
import { WorkoutPage } from "./pages/WorkoutPage";
import { getRouteByPath, isPrototypePath, type RouteId } from "./routes";
import type { Locale } from "./types/domain";

export function App() {
  const [locale, setLocale] = useState<Locale>("zh-CN");
  const [path, setPath] = useState(window.location.pathname);

  useEffect(() => {
    const onPopState = () => setPath(window.location.pathname);
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  function navigate(nextPath: string) {
    window.history.pushState({}, "", nextPath);
    setPath(nextPath);
  }

  if (isPrototypePath(path)) {
    return <PrototypeRouter />;
  }

  const route = getRouteByPath(path);

  return (
    <AppShell activeRoute={route.id} locale={locale} onLocaleChange={setLocale} onNavigate={navigate}>
      {renderPage(route.id, locale, navigate)}
    </AppShell>
  );
}

function renderPage(routeId: RouteId, locale: Locale, navigate: (path: string) => void) {
  switch (routeId) {
    case "onboarding":
      return <OnboardingPage locale={locale} onNavigate={navigate} />;
    case "plan":
      return <PlanPage locale={locale} onNavigate={navigate} />;
    case "workout":
      return <WorkoutPage locale={locale} />;
    case "diet":
      return <DietPage locale={locale} />;
    case "body":
      return <BodyPage locale={locale} />;
    case "advice":
      return <AdvicePage locale={locale} />;
    case "agent":
      return <AgentPage locale={locale} />;
    case "settings":
      return <SettingsPage locale={locale} onLocaleChange={() => undefined} />;
    case "today":
    default:
      return <TodayPage locale={locale} onNavigate={navigate} />;
  }
}
```

- [ ] **Step 3: 更新 AppShell  props 和导航**

Modify `src/components/business/AppShell.tsx` to use `primaryRoutes` and `onNavigate`:

```tsx
import { createTranslator } from "../../i18n";
import { primaryRoutes, type RouteId } from "../../routes";
import type { Locale } from "../../types/domain";

type AppShellProps = {
  activeRoute: RouteId;
  locale: Locale;
  onLocaleChange: (locale: Locale) => void;
  onNavigate: (path: string) => void;
  children: React.ReactNode;
};

export function AppShell({ activeRoute, locale, onLocaleChange, onNavigate, children }: AppShellProps) {
  const t = createTranslator(locale);

  return (
    <div className="business-shell">
      <aside className="business-sidebar" aria-label="945 navigation">
        <div className="business-brand">
          <button className="business-logo" onClick={() => onNavigate("/")} type="button">945</button>
          <span className="business-brand-label">Fitness Agent</span>
        </div>
        <nav className="business-nav">
          {primaryRoutes.map((route) => (
            <button className={route.id === activeRoute ? "active" : ""} key={route.id} onClick={() => onNavigate(route.path)} type="button">
              {t(route.navKey)}
            </button>
          ))}
        </nav>
        <a className="prototype-reference-link" href="/prototype">Stitch reference</a>
        <label className="business-language">
          <span>{t("settings.language")}</span>
          <select value={locale} onChange={(event) => onLocaleChange(event.target.value as Locale)}>
            <option value="zh-CN">中文</option>
            <option value="en-US">English</option>
          </select>
        </label>
      </aside>
      <section className="business-main">{children}</section>
    </div>
  );
}
```

- [ ] **Step 4: 验证构建**

Run: `npm run build`

Expected: TypeScript and Vite build pass.

---

## Task 2: Prototype 命名空间迁移

**Files:**
- Create: `src/prototype/StitchPrototype.tsx`
- Create: `src/prototype/screens.ts`
- Create: `src/prototype/stitchDom.ts`
- Modify: `src/pages/PrototypeRouter.tsx`
- Modify: `src/screens.ts`

**Interfaces:**
- Produces: `/prototype/*` Stitch reference routes
- Consumes: existing Stitch `screens` metadata and HTML extraction logic

- [ ] **Step 1: 移动 Stitch screen metadata**

Move existing `src/screens.ts` contents to `src/prototype/screens.ts`. Leave `src/screens.ts` as a compatibility re-export:

```ts
export { screens } from "./prototype/screens";
export type { StitchScreen } from "./prototype/screens";
```

- [ ] **Step 2: 提取 Stitch DOM helpers**

Create `src/prototype/stitchDom.ts` with the existing helper functions from `PrototypeRouter.tsx`:

```ts
import { screens } from "./screens";

export function extractBody(source: string, folder: string) {
  const parser = new DOMParser();
  const doc = parser.parseFromString(source, "text/html");
  const body = doc.body;
  const styleText = [...doc.querySelectorAll("style")]
    .map((style) => style.textContent ?? "")
    .filter(Boolean)
    .join("\n");

  body.querySelectorAll("script, link[rel='stylesheet']").forEach((node) => node.remove());
  body.querySelectorAll("[src]").forEach((node) => {
    const element = node as HTMLElement;
    const src = element.getAttribute("src");
    if (src?.startsWith("https://lh3.googleusercontent.com")) {
      const local = localAssetFor(src, folder);
      if (local) element.setAttribute("src", local);
    }
  });

  return {
    bodyClass: body.className,
    html: `${styleText ? `<style>${styleText}</style>` : ""}${body.innerHTML}`
  };
}

function localAssetFor(url: string, folder: string) {
  const screen = screens.find((item) => item.folder === folder);
  const asset = screen?.assets.find((item) => item.url === url);
  return asset ? `/stitch-reference/${folder}/${asset.file}` : undefined;
}
```

- [ ] **Step 3: 更新 prototype route path parsing**

Modify `src/pages/PrototypeRouter.tsx` so `/prototype` maps to the first Stitch screen and `/prototype/diet` maps to the Stitch diet screen:

```ts
function getCurrentScreen(): StitchScreen {
  const path = window.location.pathname.replace(/^\/+/, "").replace(/^prototype\/?/, "");
  const match = screens.find((screen) => screen.route === path);
  return match ?? screens[0];
}

function prototypeHref(screen: StitchScreen) {
  return screen.route ? `/prototype/${screen.route}` : "/prototype";
}
```

Use `prototypeHref` anywhere `navigate` currently writes `/${screen.route}`.

- [ ] **Step 4: 保留原型交互但标记 reference**

Add a visible but compact prototype label in `PrototypeRouter`:

```tsx
<div className="prototype-reference-badge">Stitch reference</div>
```

Style it in `src/styles.css` with fixed positioning and low visual weight.

- [ ] **Step 5: 验证**

Run: `npm run build`

Manual/browser checks:

```text
http://localhost:5173/               -> real Today page
http://localhost:5173/prototype      -> Stitch Today reference
http://localhost:5173/prototype/diet -> Stitch Diet reference
```

---

## Task 3: Mock API 和领域类型补全

**Files:**
- Modify: `src/types/domain.ts`
- Modify: `src/data/demoData.ts`
- Modify: `src/services/mockApi.ts`

**Interfaces:**
- Produces: `WorkoutPageData`, `DietPageData`, `BodyPageData`, `AdvicePageData`, `SettingsData`
- Produces API: `getWorkout`, `getDiet`, `getBodyMetrics`, `saveBodyMetric`, `getAdvice`, `updateAdviceStatus`, `getSettings`, `saveSettings`

- [ ] **Step 1: 增加页面数据类型**

Append to `src/types/domain.ts`:

```ts
export type WorkoutPageData = {
  plan: Plan;
  selected_day: WorkoutPlanDay;
  logs: WorkoutLog[];
  completion_rate: number;
  weekly_volume_sets: number;
};

export type DietPageData = {
  plan: Plan;
  selected_day: MealPlanDay;
  logs: MealLog[];
  targets: MacroTargets;
};

export type BodyPageData = {
  profile: UserProfile;
  metrics: BodyMetric[];
  latest_metric: BodyMetric;
  trend_7_day_kg: number;
  trend_30_day_kg: number;
  trend_90_day_kg: number;
};

export type AdvicePageData = {
  daily: AgentAdvice | null;
  weekly: AgentAdvice | null;
  adjustments: AgentAdvice[];
};

export type SettingsData = {
  user: User;
  profile: UserProfile;
  language: Locale;
  unit_system: UnitSystem;
};
```

- [ ] **Step 2: 补 demo 数据**

Update `src/data/demoData.ts` with:

```ts
export const demoBodyMetrics: BodyMetric[] = [
  { metric_id: "body-2026-07-05", user_id: DEMO_USER_ID, date: "2026-07-05", weight_kg: 76.4, bmi: 23.6, created_at: "2026-07-05T08:00:00.000Z" },
  { metric_id: "body-2026-07-08", user_id: DEMO_USER_ID, date: "2026-07-08", weight_kg: 75.9, bmi: 23.4, created_at: "2026-07-08T08:00:00.000Z" },
  { metric_id: "body-2026-07-11", user_id: DEMO_USER_ID, date: TODAY_DATE, weight_kg: 75.6, bmi: 23.3, created_at: "2026-07-11T08:00:00.000Z" }
];

export const demoWeeklyAdvice: AgentAdvice = {
  advice_id: "advice-weekly-001",
  user_id: DEMO_USER_ID,
  date: TODAY_DATE,
  type: "weekly_summary",
  title: "本周执行稳定，但恢复信号偏疲劳",
  content: "你完成了大部分训练计划，饮食蛋白质基本达标。建议下周保留力量训练频率，但降低一次高强度腿部训练量。",
  reason: "训练完成率较好，但疲劳和酸痛评分连续两天偏高。",
  related_data: ["weekly_workouts_completed", "fatigue_level", "soreness_level"],
  recommended_actions: ["下周腿部训练减少 2 组", "保持每日蛋白质目标", "睡眠低于 7 小时时降低训练强度"],
  risk_level: "medium",
  accepted_status: "pending",
  created_at: "2026-07-11T09:00:00.000Z"
};
```

- [ ] **Step 3: 补 mock API**

Add methods to `api` in `src/services/mockApi.ts`:

```ts
async getWorkout(user_id = DEMO_USER_ID): Promise<ApiResponse<WorkoutPageData>> {
  const user = ensureDemoUser(user_id);
  if (user.error) return user;
  return ok({
    plan: demoPlan,
    selected_day: demoPlan.workout_plan.days[0],
    logs: workoutLogs,
    completion_rate: todayData.status_summary.weekly_workouts_completed / todayData.status_summary.weekly_workouts_planned,
    weekly_volume_sets: demoPlan.workout_plan.days.reduce((sum, day) => sum + day.exercises.reduce((inner, exercise) => inner + exercise.sets, 0), 0)
  });
},

async getDiet(user_id = DEMO_USER_ID): Promise<ApiResponse<DietPageData>> {
  const user = ensureDemoUser(user_id);
  if (user.error) return user;
  return ok({
    plan: demoPlan,
    selected_day: demoPlan.meal_plan.days[0],
    logs: mealLogs,
    targets: demoPlan.meal_plan.daily_targets
  });
},
```

Also add `getBodyMetrics`, `saveBodyMetric`, `getAdvice`, `updateAdviceStatus`, `getSettings`, and `saveSettings` using the same `ensureDemoUser` pattern.

- [ ] **Step 4: 验证**

Run: `npm run build`

Expected: all new domain imports compile.

---

## Task 4: PRD 页面骨架

**Files:**
- Create: all missing files under `src/pages/`
- Modify: `src/pages/TodayPage.tsx`

**Interfaces:**
- Consumes: `locale`, `api`, `createTranslator`
- Produces: real skeletons for `/onboarding`, `/plan`, `/workout`, `/diet`, `/body`, `/advice`, `/agent`, `/settings`

- [ ] **Step 1: 创建通用页面骨架模式**

Each page should follow this shape:

```tsx
import { useEffect, useState } from "react";
import { createTranslator } from "../i18n";
import type { Locale } from "../types/domain";

type PageProps = { locale: Locale };

export function ExamplePage({ locale }: PageProps) {
  const t = createTranslator(locale);
  const [notice, setNotice] = useState("");

  useEffect(() => {
    document.title = `${t("page.example.title")} - 945`;
  }, [t]);

  return (
    <div className="business-page">
      <header className="page-header">
        <p>945</p>
        <h1>{t("page.example.title")}</h1>
        <span>{t("page.example.description")}</span>
      </header>
      {notice ? <div className="business-notice">{notice}</div> : null}
    </div>
  );
}
```

- [ ] **Step 2: OnboardingPage**

Create `src/pages/OnboardingPage.tsx` with fields from PRD:

```tsx
type OnboardingPageProps = { locale: Locale; onNavigate: (path: string) => void };
```

Show nickname, age, height, weight, goal, training days, dietary preference, constraints. `Initialize demo profile` calls `onNavigate("/plan")`.

- [ ] **Step 3: PlanPage**

Create `src/pages/PlanPage.tsx`:

- user goal summary
- training settings summary
- diet settings summary
- generated workout preview
- generated meal preview
- buttons: generate, accept, ask Agent

`Accept plan` navigates to `/`.

- [ ] **Step 4: WorkoutPage**

Create `src/pages/WorkoutPage.tsx`:

- load `api.getWorkout`
- render weekly plan
- render selected day exercise list
- set completion buttons mutate local UI state
- save workout log via `api.saveWorkoutLog`

- [ ] **Step 5: DietPage**

Create `src/pages/DietPage.tsx`:

- load `api.getDiet`
- render macro progress
- render planned meals
- confirm planned meal via `api.confirmPlannedMeal`
- manual meal mini form via `api.saveManualMeal`

- [ ] **Step 6: BodyPage**

Create `src/pages/BodyPage.tsx`:

- load `api.getBodyMetrics`
- render latest weight and BMI
- render 7/30/90 day trend text
- save weight input through `api.saveBodyMetric`

- [ ] **Step 7: AdvicePage**

Create `src/pages/AdvicePage.tsx`:

- load `api.getAdvice`
- render daily advice, weekly summary, and plan adjustment cards
- accept/dismiss/defer actions call `api.updateAdviceStatus`
- Weekly Summary appears here, not under Schedule.

- [ ] **Step 8: AgentPage**

Create `src/pages/AgentPage.tsx`:

- load existing messages with `api.getAgentMessages`
- send prompt with `api.sendAgentMessage`
- show confirmation dialog when `record_draft.requires_confirmation`
- confirmation shows notice but does not silently write data.

- [ ] **Step 9: SettingsPage**

Create `src/pages/SettingsPage.tsx`:

- load `api.getSettings`
- show demo profile, unit system, language, safety disclaimer
- language select calls parent `onLocaleChange`
- export data button is disabled and labelled as future capability.

- [ ] **Step 10: TodayPage navigation prop**

Modify `src/pages/TodayPage.tsx` props:

```ts
type TodayPageProps = {
  locale: Locale;
  onNavigate?: (path: string) => void;
};
```

Change the Stitch link to:

```tsx
<button className="prototype-link" onClick={() => onNavigate?.("/prototype")} type="button">
  Stitch reference
</button>
```

- [ ] **Step 11: 验证**

Run: `npm run build`

Expected: all route page imports compile.

---

## Task 5: i18n 和样式收口

**Files:**
- Modify: `src/i18n/types.ts`
- Modify: `src/i18n/zh-CN.ts`
- Modify: `src/i18n/en-US.ts`
- Modify: `src/styles.css`

**Interfaces:**
- Produces: all keys used by new routes
- Produces: responsive product shell styles

- [ ] **Step 1: 增加 i18n keys**

Add page keys:

```ts
"nav.onboarding": string;
"nav.plan": string;
"page.today.title": string;
"page.today.description": string;
"page.onboarding.title": string;
"page.onboarding.description": string;
"page.plan.title": string;
"page.plan.description": string;
"page.workout.title": string;
"page.workout.description": string;
"page.diet.title": string;
"page.diet.description": string;
"page.body.title": string;
"page.body.description": string;
"page.advice.title": string;
"page.advice.description": string;
"page.agent.title": string;
"page.agent.description": string;
"page.settings.title": string;
"page.settings.description": string;
```

Add action/status keys for save, confirm, dismiss, defer, generate, accept, future capability, and mock saved notices.

- [ ] **Step 2: 补中文词典**

Use Chinese as the primary MVP copy. Examples:

```ts
"page.body.title": "身体数据",
"page.body.description": "查看体重、BMI 和近期趋势，理解它们和当前目标的关系。",
"page.advice.title": "建议",
"page.advice.description": "集中查看 Agent 今日建议、周总结和计划调整原因。",
"status.futureCapability": "后续能力",
```

- [ ] **Step 3: 补英文词典**

Keep English structurally complete:

```ts
"page.body.title": "Body Data",
"page.body.description": "Review weight, BMI, and recent trends in the context of the current goal.",
"page.advice.title": "Advice",
"page.advice.description": "Review Agent daily advice, weekly summaries, and plan adjustment reasons.",
"status.futureCapability": "Future capability",
```

- [ ] **Step 4: 样式补齐**

Add CSS classes:

```css
.business-page {}
.page-header {}
.page-grid {}
.business-panel {}
.business-panel.compact {}
.prototype-reference-link {}
.prototype-reference-badge {}
.mobile-bottom-nav {}
```

Responsive rules:

```css
@media (max-width: 860px) {
  .business-shell { grid-template-columns: 1fr; }
  .business-sidebar { display: none; }
  .mobile-bottom-nav { display: grid; }
  .business-main { padding-bottom: 84px; }
}
```

- [ ] **Step 5: 验证**

Run: `npm run build`

Open desktop and mobile widths in browser automation.

---

## Task 6: 验收 QA 和文档

**Files:**
- Create: `docs/PRD_FRONTEND_FOUNDATION_QA.md`
- Modify: `design-qa.md` only if needed to clarify Stitch-specific QA remains historical

**Interfaces:**
- Produces: QA evidence for build, routes, interactions, prototype access

- [ ] **Step 1: 构建验证**

Run:

```powershell
npm run build
```

Expected: exit code 0.

- [ ] **Step 2: 启动本地服务**

Run:

```powershell
npm run dev -- --port 5173 --strictPort
```

If port 5173 is already listening, reuse it.

- [ ] **Step 3: Browser route smoke**

Use Chrome/Playwright to verify:

```text
/ -> Today
/workout -> Workout
/diet -> Diet
/body -> Body
/advice -> Advice
/agent -> Agent
/settings -> Settings
/prototype -> Stitch reference
/prototype/diet -> Stitch Diet reference
```

Expected: 0 console errors.

- [ ] **Step 4: Interaction smoke**

Verify at least:

```text
Today: save check-in
Workout: save workout log
Diet: confirm planned meal and save manual meal
Body: save weight metric
Advice: accept/dismiss/defer advice
Agent: send message and confirm draft
Settings: switch language
```

Expected: visible notice or state change for each.

- [ ] **Step 5: 写 QA 文档**

Create `docs/PRD_FRONTEND_FOUNDATION_QA.md`:

```md
# PRD Frontend Foundation QA

final result: passed

## Scope

This QA validates the first PRD-driven functional foundation. It is not a full Stitch pixel-match pass.

## Evidence

- `npm run build` passed.
- Primary product routes render without console errors.
- `/prototype/*` routes remain available for Stitch reference.
- Main navigation no longer exposes Schedule as a misleading top-level route.
- Core mock interactions were checked on Today, Workout, Diet, Body, Advice, Agent, and Settings.

## Remaining Work

- Convert each page from information-architecture skeleton to high-fidelity React components using Stitch references.
- Replace in-memory mock API with backend/API integration when ready.
- Expand automated tests when a test framework is added.
```

- [ ] **Step 6: 最终状态检查**

Run:

```powershell
git status --short
```

Report changed files and verification evidence.

---

## Self-Review

### Spec Coverage

- App Shell and PRD primary routes: Task 1
- Prototype route namespace: Task 2
- Typed demo data and mock API boundaries: Task 3
- All primary page skeletons: Task 4
- i18n and responsive shell styling: Task 5
- Build/browser/interaction QA: Task 6

### Known Non-Goals

- This plan does not complete full Stitch pixel migration.
- This plan does not add backend persistence.
- This plan does not add a routing library; routing remains lightweight and pathname-based.

### 空缺项扫描

实施步骤不应包含未定项或待补项。空状态 UI 是明确产品行为，不是缺失实现。
