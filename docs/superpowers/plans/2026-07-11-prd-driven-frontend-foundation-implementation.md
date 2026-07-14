# 945 PRD 驱动前端基础实施计划

> **给 agentic worker：** 必须使用子技能：推荐 `superpowers:subagent-driven-development`，或使用 `superpowers:executing-plans`，按任务逐步执行本计划。步骤使用 checkbox（`- [ ]`）语法跟踪。

**目标：** 将当前 Stitch 包装层迁移为 PRD 驱动的真实 React 前端基础，保留 Stitch 到 `/prototype/*` 作为视觉参考。

**架构：** 主产品入口由 `src/App.tsx` 和真实 route config 驱动，渲染 `AppShell` 与 `src/pages/*` 页面骨架。Stitch 原型保留在 prototype 命名空间，不再作为主产品路由。Mock API 使用内存状态模拟未来后端边界，页面通过 mock API 呈现和更新 demo 数据。

**技术栈：** Vite、React 19、TypeScript 5.8、本地 CSS、本地 mock 数据，不新增 routing、状态管理、UI 或图表依赖。

## 全局约束

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

## 文件结构

### 创建

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

### 修改

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

### 保留

```text
stitch-reference/
public/stitch-reference/
qa-shots/
design-qa.md
```

---

## 任务 1：真实路由配置和 App 入口

**文件：**
- 创建：`src/routes.ts`
- 修改：`src/App.tsx`
- 修改：`src/components/business/AppShell.tsx`

**接口：**
- 产出：`RouteId`、`AppRoute`、`primaryRoutes`、`prototypeRoutes`、`getRouteByPath(pathname)`
- 消费：现有 `Locale`、`AppShell`、`TodayPage`、`PrototypeRouter`

- [ ] **步骤 1：创建 route config**

创建 `src/routes.ts`：

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

- [ ] **步骤 2：更新 App 入口**

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

- [ ] **步骤 3：更新 AppShell props 和导航**

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

- [ ] **步骤 4：验证构建**

运行：`npm run build`

预期：TypeScript 和 Vite 构建通过。

---

## 任务 2：Prototype 命名空间迁移

**文件：**
- 创建：`src/prototype/StitchPrototype.tsx`
- 创建：`src/prototype/screens.ts`
- 创建：`src/prototype/stitchDom.ts`
- 修改：`src/pages/PrototypeRouter.tsx`
- 修改：`src/screens.ts`

**接口：**
- 产出：`/prototype/*` Stitch reference routes
- 消费：现有 Stitch `screens` metadata 和 HTML extraction logic

- [ ] **步骤 1：移动 Stitch screen metadata**

将现有 `src/screens.ts` 内容移动到 `src/prototype/screens.ts`。保留 `src/screens.ts` 作为兼容 re-export：

```ts
export { screens } from "./prototype/screens";
export type { StitchScreen } from "./prototype/screens";
```

- [ ] **步骤 2：提取 Stitch DOM helpers**

创建 `src/prototype/stitchDom.ts`，放入来自 `PrototypeRouter.tsx` 的现有 helper functions：

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

- [ ] **步骤 3：更新 prototype route path parsing**

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

当前 `navigate` 写入 `/${screen.route}` 的位置都改用 `prototypeHref`。

- [ ] **步骤 4：保留原型交互但标记 reference**

在 `PrototypeRouter` 中添加一个可见但紧凑的原型标签：

```tsx
<div className="prototype-reference-badge">Stitch reference</div>
```

在 `src/styles.css` 中设置固定定位和低视觉权重样式。

- [ ] **步骤 5：验证**

运行：`npm run build`

手动/浏览器检查：

```text
http://localhost:5173/               -> real Today page
http://localhost:5173/prototype      -> Stitch Today reference
http://localhost:5173/prototype/diet -> Stitch Diet reference
```

---

## 任务 3：Mock API 和领域类型补全

**文件：**
- 修改：`src/types/domain.ts`
- 修改：`src/data/demoData.ts`
- 修改：`src/services/mockApi.ts`

**接口：**
- 产出：`WorkoutPageData`、`DietPageData`、`BodyPageData`、`AdvicePageData`、`SettingsData`
- 产出 API：`getWorkout`、`getDiet`、`getBodyMetrics`、`saveBodyMetric`、`getAdvice`、`updateAdviceStatus`、`getSettings`、`saveSettings`

- [ ] **步骤 1：增加页面数据类型**

追加到 `src/types/domain.ts`：

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

- [ ] **步骤 2：补 demo 数据**

更新 `src/data/demoData.ts`，增加：

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

- [ ] **步骤 3：补 mock API**

在 `src/services/mockApi.ts` 的 `api` 中添加 methods：

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

同时使用相同的 `ensureDemoUser` 模式添加 `getBodyMetrics`、`saveBodyMetric`、`getAdvice`、`updateAdviceStatus`、`getSettings` 和 `saveSettings`。

- [ ] **步骤 4：验证**

运行：`npm run build`

预期：所有新增 domain import 均可编译。

---

## 任务 4：PRD 页面骨架

**文件：**
- 创建：`src/pages/` 下所有缺失页面文件
- 修改：`src/pages/TodayPage.tsx`

**接口：**
- 消费：`locale`、`api`、`createTranslator`
- 产出：`/onboarding`、`/plan`、`/workout`、`/diet`、`/body`、`/advice`、`/agent`、`/settings` 的真实页面骨架

- [ ] **步骤 1：创建通用页面骨架模式**

每个页面遵循此结构：

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

- [ ] **步骤 2：OnboardingPage**

创建 `src/pages/OnboardingPage.tsx`，包含 PRD 中的字段：

```tsx
type OnboardingPageProps = { locale: Locale; onNavigate: (path: string) => void };
```

展示昵称、年龄、身高、体重、目标、训练天数、饮食偏好和限制条件。`Initialize demo profile` 调用 `onNavigate("/plan")`。

- [ ] **步骤 3：PlanPage**

创建 `src/pages/PlanPage.tsx`：

- 用户目标摘要
- 训练设置摘要
- 饮食设置摘要
- 已生成训练预览
- 已生成餐食预览
- 按钮：generate、accept、ask Agent

`Accept plan` 导航到 `/`。

- [ ] **步骤 4：WorkoutPage**

创建 `src/pages/WorkoutPage.tsx`：

- 加载 `api.getWorkout`
- 渲染周训练计划
- 渲染选中日期的动作列表
- 组完成按钮会改变本地 UI 状态
- 通过 `api.saveWorkoutLog` 保存训练记录

- [ ] **步骤 5：DietPage**

创建 `src/pages/DietPage.tsx`：

- 加载 `api.getDiet`
- 渲染宏量营养进度
- 渲染计划餐
- 通过 `api.confirmPlannedMeal` 确认计划餐
- 通过 `api.saveManualMeal` 实现手动餐食 mini form

- [ ] **步骤 6：BodyPage**

创建 `src/pages/BodyPage.tsx`：

- 加载 `api.getBodyMetrics`
- 渲染最新体重和 BMI
- 渲染 7/30/90 天趋势文案
- 通过 `api.saveBodyMetric` 保存体重输入

- [ ] **步骤 7：AdvicePage**

创建 `src/pages/AdvicePage.tsx`：

- 加载 `api.getAdvice`
- 渲染每日建议、周总结和计划调整卡片
- accept/dismiss/defer 操作调用 `api.updateAdviceStatus`
- Weekly Summary 显示在这里，不放在 Schedule 下。

- [ ] **步骤 8：AgentPage**

创建 `src/pages/AgentPage.tsx`：

- 通过 `api.getAgentMessages` 加载已有消息
- 通过 `api.sendAgentMessage` 发送 prompt
- 当 `record_draft.requires_confirmation` 为真时显示确认弹窗
- 确认只显示 notice，不静默写入数据。

- [ ] **步骤 9：SettingsPage**

创建 `src/pages/SettingsPage.tsx`：

- 加载 `api.getSettings`
- 展示 demo profile、unit system、language 和 safety disclaimer
- 语言选择调用父级 `onLocaleChange`
- 数据导出按钮禁用，并标记为未来能力。

- [ ] **步骤 10：TodayPage navigation prop**

修改 `src/pages/TodayPage.tsx` props：

```ts
type TodayPageProps = {
  locale: Locale;
  onNavigate?: (path: string) => void;
};
```

将 Stitch 链接改为：

```tsx
<button className="prototype-link" onClick={() => onNavigate?.("/prototype")} type="button">
  Stitch reference
</button>
```

- [ ] **步骤 11：验证**

运行：`npm run build`

预期：所有 route page import 均可编译。

---

## 任务 5：i18n 和样式收口

**文件：**
- 修改：`src/i18n/types.ts`
- 修改：`src/i18n/zh-CN.ts`
- 修改：`src/i18n/en-US.ts`
- 修改：`src/styles.css`

**接口：**
- 产出：新路由使用的所有 key
- 产出：响应式产品 shell 样式

- [ ] **步骤 1：增加 i18n keys**

添加页面 key：

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

添加 save、confirm、dismiss、defer、generate、accept、future capability 和 mock saved notice 所需的 action/status key。

- [ ] **步骤 2：补中文词典**

中文作为 MVP 主文案。示例：

```ts
"page.body.title": "身体数据",
"page.body.description": "查看体重、BMI 和近期趋势，理解它们和当前目标的关系。",
"page.advice.title": "建议",
"page.advice.description": "集中查看 Agent 今日建议、周总结和计划调整原因。",
"status.futureCapability": "后续能力",
```

- [ ] **步骤 3：补英文词典**

英文保持结构完整：

```ts
"page.body.title": "Body Data",
"page.body.description": "Review weight, BMI, and recent trends in the context of the current goal.",
"page.advice.title": "Advice",
"page.advice.description": "Review Agent daily advice, weekly summaries, and plan adjustment reasons.",
"status.futureCapability": "Future capability",
```

- [ ] **步骤 4：样式补齐**

添加 CSS classes：

```css
.business-page {}
.page-header {}
.page-grid {}
.business-panel {}
.business-panel.compact {}
.prototype-reference-link {}
.prototype-reference-badge {}
```

桌面客户端规则：

- 保留左侧导航和顶部导航。
- 主内容区使用桌面客户端宽度设计，导航只保留桌面客户端形态。

- [ ] **步骤 5：验证**

运行：`npm run build`

在浏览器自动化中打开桌面客户端宽度进行检查。

---

## 任务 6：验收 QA 和文档

**文件：**
- 创建：`docs/PRD_FRONTEND_FOUNDATION_QA.md`
- 仅在需要澄清 Stitch-specific QA 属于历史记录时修改 `design-qa.md`

**接口：**
- 产出：build、routes、interactions 和 prototype access 的 QA 证据

- [ ] **步骤 1：构建验证**

运行：

```powershell
npm run build
```

预期：退出码为 0。

- [ ] **步骤 2：启动本地服务**

运行：

```powershell
npm run dev -- --port 5173 --strictPort
```

如果 5173 端口已在监听，复用它。

- [ ] **步骤 3：浏览器路由 smoke**

使用 Chrome/Playwright 验证：

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

预期：0 个控制台错误。

- [ ] **步骤 4：交互 smoke**

至少验证：

```text
Today: save check-in
Workout: save workout log
Diet: confirm planned meal and save manual meal
Body: save weight metric
Advice: accept/dismiss/defer advice
Agent: send message and confirm draft
Settings: switch language
```

预期：每一项都有可见 notice 或状态变化。

- [ ] **步骤 5：写 QA 文档**

创建 `docs/PRD_FRONTEND_FOUNDATION_QA.md`：

```md
# PRD 前端基础层 QA

最终结果：通过

## 范围

本 QA 验证第一版 PRD 驱动的功能基础层。它不是完整 Stitch 像素级还原验证。

## 证据

- `npm run build` 通过。
- 主产品路由渲染时没有控制台错误。
- `/prototype/*` 路由仍可作为 Stitch reference 访问。
- 主导航不再暴露容易误导的 Schedule 顶层路由。
- 已检查 Today、Workout、Diet、Body、Advice、Agent 和 Settings 的核心 mock 交互。

## 剩余工作

- 使用 Stitch reference 将每个页面从信息架构骨架转换为高保真 React 组件。
- 后端/API 准备好后，用真实集成替换内存 mock API。
- 测试框架加入后扩展自动化测试。
```

- [ ] **步骤 6：最终状态检查**

运行：

```powershell
git status --short
```

报告变更文件和验证证据。

---

## 自检

### 规格覆盖

- App Shell and PRD primary routes: Task 1
- Prototype route namespace: Task 2
- Typed demo data and mock API boundaries: Task 3
- All primary page skeletons: Task 4
- i18n and responsive shell styling: Task 5
- Build/browser/interaction QA: Task 6

### 已知非目标

- This plan does not complete full Stitch pixel migration.
- This plan does not add backend persistence.
- This plan does not add a routing library; routing remains lightweight and pathname-based.

### 空缺项扫描

实施步骤不应包含未定项或待补项。空状态 UI 是明确产品行为，不是缺失实现。
