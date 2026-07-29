# 945 Agent-First 最小闭环 Implementation Plan

> **For agentic workers:** Execute inline in this session with focused tests. Do not use subagents for this plan.

**Goal:** 将 945 首页改为 Agent 工作区，将现有 Dashboard 迁为 `/today`，使有计划、过期计划和无计划用户均从 Agent 开始。

**Architecture:** 复用既有 `AgentPage`、`PlanContext`、计划草稿和确认 API。首页只改变路由和内容职责，不改变视觉 token、导航外观或组件样式；资料收集卡先以入口/状态卡完成，不在本批重做完整六步表单。

**Tech Stack:** React、TypeScript、Vite、现有 FastAPI HTTP/mock adapter、Playwright。

## Global Constraints

- 保留现有颜色、字体、图标、导航外观、玻璃质感和组件视觉样式。
- `/` 永远显示 Agent；`/agent` 兼容重定向到 `/`；Dashboard 使用 `/today`。
- `PlanContext` 是 Profile、当前 active plan、覆盖状态和运行日期的唯一来源。
- 不接真实模型；不新增 RAG、LangGraph、LangSmith、Eval、Checkpoint 或移动端工作。
- 计划和记录仍须用户确认后写入。

### Task 1: 路由与导航职责迁移

**Files:**
- Modify: `src/routes.ts`
- Modify: `src/App.tsx`
- Modify: `src/components/business/AppShell.tsx`
- Test: `tests/agent-first-flow.spec.ts`

- [ ] 写失败测试：访问 `/` 显示 `945 智能教练`；访问 `/agent` 最终 URL 为 `/`；访问 `/today` 显示原 Dashboard 标识。
- [ ] 运行：`npx playwright test tests/agent-first-flow.spec.ts --project=http`，确认当前失败。
- [ ] 将 `today` 路由改为 `/today`，将 `agent` 路由改为 `/`；在 `getRouteByPath()` 中把 `/agent` 规范化为 `/`；删除 `App.tsx` 中针对首页渲染计划续建空态的 Dashboard 逻辑。
- [ ] 保持 AppShell 的 CSS class 和视觉样式不变；仅更新顶部“今日”按钮跳转 `/today`，同步教练按钮跳转 `/`。
- [ ] 运行相同测试和 `npm run build`，确认通过。

### Task 2: 首页 Agent 状态与资料入口

**Files:**
- Modify: `src/pages/AgentPage.tsx`
- Modify: `src/i18n/zh-CN.ts`
- Modify: `src/i18n/en-US.ts`
- Test: `tests/agent-first-flow.spec.ts`

- [ ] 写失败测试：`expired`/`none` 状态下首页显示“开始创建计划”并导航 `/onboarding`；`active_today` 状态下首页显示当前训练或“今天没有训练安排”。
- [ ] 运行：`npx playwright test tests/agent-first-flow.spec.ts --project=http -g "Agent"`，确认当前失败。
- [ ] 从 `PlanContext` 读取 `coverageStatus` 和 `profile`，在现有 Agent 页面顶部插入状态说明和一个结构化资料入口按钮；保留聊天区、右侧状态面板和草稿确认弹窗的现有样式。
- [ ] `expired`/`none`/`incomplete` 时入口跳转 `/onboarding`，并将 Agent 欢迎文本改为解释“完成资料后我会生成训练与饮食计划草稿”；`active_today` 时保留当前计划/今日记录上下文。
- [ ] 运行针对性测试并确认用户点击入口后可到达 `/onboarding`。

### Task 3: Dashboard 执行页与回归

**Files:**
- Modify: `src/pages/TodayPage.tsx`
- Modify: `tests/http-integration.spec.ts`
- Modify: `tests/app-smoke.spec.ts`
- Test: `tests/agent-first-flow.spec.ts`

- [ ] 写失败测试：激活计划后 `/today` 仍展示 Dashboard；首页不会出现 Dashboard 的今日 hero 标题。
- [ ] 移除 TodayPage 中重复 Agent 输入、回复和草稿确认区域，仅保留执行、计划餐确认、每日打卡、建议摘要与跳转 Agent 的入口；不修改现有 CSS 视觉样式。
- [ ] 更新旧测试的首页 URL 为 `/today`，并新增一次 HTTP 路径：`/` Agent -> `/onboarding` -> 生成/启用计划 -> `/today` Dashboard。
- [ ] 运行：`npm run build`、`npx playwright test tests/agent-first-flow.spec.ts --project=http`、`npm run qa:http`。
- [ ] 仅提交本批路由、Agent、Today 与测试文件：`git commit -m "feat: make agent the 945 home experience"`。

## Self-Review

- 覆盖：首页 Agent、旧 Agent 链接兼容、Dashboard 路由、过期/无计划入口、active 计划状态、视觉冻结和 HTTP 回归均有任务。
- 范围：本批不实现 Agent 内完整资料卡或真实模型，仅复用已有 `/onboarding` 作为结构化资料页。
- 验收：没有计划时用户从 `/` 能抵达资料入口；有计划时用户从 `/` 直接和 945 对话；执行内容只在 `/today` 展示。
