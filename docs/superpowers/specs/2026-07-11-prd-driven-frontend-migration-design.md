# 945 PRD 驱动前端迁移设计

## 背景

当前前端是一个 Vite + React 包装层，用来加载 Stitch 导出的 HTML。它很好地保留了高保真视觉原型，但不适合作为长期产品实现，因为导航和交互行为依赖静态 HTML、按钮文字和 Material icon 名称来推断。

`PRD.md` 和 `docs/FRONTEND_REQUIREMENTS.md` 定义的产品范围，比当前 11 个 Stitch 导出页面更完整。下一步迁移需要保留 Stitch 作为视觉参考，同时把主应用迁移到由 PRD 定义的路由、状态、数据和组件体系上。

## 目标

为 945 建立第一版真实前端基础，同时保留 Stitch 的视觉方向。

本阶段不追求一次性实现 PRD 中所有业务流程。它的目标是先建立正确的应用外壳、路由表、数据契约、mock 数据和页面骨架，让后续可以逐页把 Stitch HTML 替换为真实业务组件。

## 范围

### 本阶段包含

- 将主产品入口替换为真实 React App Shell。
- 定义 PRD 主导的一级路由：
  - `/`：今日
  - `/onboarding`：首次引导
  - `/plan`：计划生成
  - `/workout`：训练
  - `/diet`：饮食
  - `/body`：身体数据
  - `/advice`：建议
  - `/agent`：Agent
  - `/settings`：设置
- 将 Stitch 包装层移动到原型/参考路由命名空间：
  - `/prototype`
  - `/prototype/workout`
  - `/prototype/settings`
  - `/prototype/weekly-summary`
  - `/prototype/agent-v3`
  - `/prototype/diet`
  - `/prototype/workout-alt`
  - `/prototype/agent`
  - `/prototype/onboarding`
  - `/prototype/ai-adjustment`
  - `/prototype/diet-alt`
- 为 PRD 的核心领域创建类型化 demo 数据：
  - demo 用户
  - 今日状态
  - 训练计划和训练记录草稿
  - 饮食计划和饮食记录草稿
  - 身体数据
  - 每日打卡
  - 建议和周总结
  - Agent 消息
- 创建简单 mock API service，使用异步函数和浏览器会话内的内存状态变化。
- 创建 `zh-CN` 和 `en-US` i18n 字典，默认界面语言为中文。
- 为所有主路由增加真实页面骨架，每个页面在信息架构层面展示 PRD 要求的核心模块。
- 保留现有 Stitch 导出、资源和 QA 截图，作为视觉参考。

### 本阶段不包含

- 后端接入。
- 登录、账号系统或云端持久化。
- 完整图表库接入。
- 食物图片识别、条形码扫描、外卖平台接入或自动识别餐盘。
- 将每个 Stitch 页面完整像素级转成 React 组件。
- 完整 Agent 智能能力；Agent 回复仍使用确定性的 mock 行为。

## 架构

### App Shell

`src/App.tsx` 从 Stitch renderer 改为路由外壳。它根据 `window.location.pathname` 判断当前路由，渲染 `AppShell`，并选择对应页面组件。

Shell 负责：

- 桌面端左侧导航
- 顶部页面标题区
- 语言切换
- 原型参考入口
- 当前路由 active 状态

导航由类型化 route config 定义，不再从静态 HTML 推断。

### 原型参考

现有 Stitch renderer 拆到更聚焦的文件中：

- `src/prototype/StitchPrototype.tsx`
- `src/prototype/screens.ts`
- `src/prototype/stitchDom.ts`

它继续通过 `/prototype/*` 提供视觉对照和 QA 参考，但不再控制主产品路由。

### 领域数据

领域模型放在 `src/types/domain.ts`。Demo 数据放在 `src/data/demoData.ts`。Mock API 放在 `src/services/mockApi.ts`，暴露接近未来后端边界的异步函数：

- `getToday()`
- `getWorkout()`
- `saveWorkoutLog(input)`
- `getDiet()`
- `confirmMeal(mealId)`
- `saveManualMeal(input)`
- `getBodyMetrics()`
- `saveDailyCheckIn(input)`
- `getAdvice()`
- `sendAgentMessage(message)`
- `getSettings()`
- `saveSettings(input)`

Mock mutation 在当前浏览器会话中更新内存状态。刷新页面后恢复到默认 demo seed。

### 页面

每个主页面都是 `src/pages/` 下的真实 React 组件：

- `TodayPage.tsx`
- `OnboardingPage.tsx`
- `PlanPage.tsx`
- `WorkoutPage.tsx`
- `DietPage.tsx`
- `BodyPage.tsx`
- `AdvicePage.tsx`
- `AgentPage.tsx`
- `SettingsPage.tsx`

页面使用 `src/components/` 下的轻量共享组件：

- `AppShell.tsx`
- `MetricCard.tsx`
- `ProgressBar.tsx`
- `SectionPanel.tsx`
- `StatusPill.tsx`
- `ActionButton.tsx`
- `EmptyState.tsx`
- `ConfirmModal.tsx`

组件保持简单、局部和可读。本阶段不新增 UI 组件库。

## 产品行为

### 今日

今日页展示：

- 状态摘要
- 今日训练卡片
- 今日饮食卡片
- 身体数据快捷录入
- 每日打卡
- Agent 今日建议
- 本周进度

核心操作通过 mock API 更新状态，并给出明确反馈：

- 保存每日打卡
- 标记训练完成
- 确认计划餐
- 创建手动饮食记录草稿
- 打开建议页

### 训练

训练页展示：

- 本周训练计划
- 选中日期的训练内容
- 动作列表
- 组级完成控制
- 训练历史摘要
- 完成率和训练量摘要

### 饮食

饮食页展示：

- 今日饮食计划
- 营养进度
- 餐次列表
- 计划餐确认
- 手动饮食录入
- 饮食历史摘要

### 身体数据

身体数据页展示：

- 当前体重
- BMI
- 最近 7 天、30 天、90 天趋势摘要
- 当 demo 数据缺失时，将体脂率和腰围显示为明确空状态
- 与当前目标相关的解释

### 建议

建议页解决当前 `Analytics/Schedule` 混用造成的歧义。它展示：

- 今日建议
- 周总结
- 计划调整建议
- 建议来源说明
- 采纳、忽略、稍后处理反馈动作

### Agent

Agent 仍然是确定性的 mock chat，但必须遵守 PRD 约束：

- 可以解释计划
- 可以准备记录草稿
- 不会静默保存关键数据
- 保存草稿必须经过用户明确确认

### 设置

设置页展示：

- demo 用户资料
- 目标和偏好摘要
- 单位设置
- 语言设置
- 安全声明
- 数据导出入口，并标记为未来能力

## 导航规则

- `Schedule` 不是 PRD 信息架构中的一级路由，不应该跳转到 Weekly Summary。
- 本阶段 Weekly Summary 归入 Advice 页面。
- `Body data` 拥有独立 `/body` 路由。
- 新 App Shell 不使用 `Analytics` 作为一级导航名称。趋势和总结内容分别归入 Body 和 Advice。
- 原型参考路由需要明确标记为 reference，避免用户误以为它们是正式产品页面。

## 样式策略

新产品 shell 使用 `src/styles.css` 中的本地 CSS。视觉方向借鉴 Stitch 的 “Refined Glacier Light”：

- 浅蓝白背景
- 克制的玻璃质感面板
- 紧凑的 dashboard 卡片
- 主色使用蓝色
- 成功状态使用绿色
- 清晰边框和轻量阴影

不要把 Stitch HTML 整段复制进业务组件。Stitch 截图和本地导出只作为视觉参考。

## 测试与验收

本阶段满足以下条件即可验收：

- `npm run build` 通过。
- 所有主路由无控制台错误。
- 主导航路由正确：
  - 今日 -> `/`
  - 训练 -> `/workout`
  - 饮食 -> `/diet`
  - 身体数据 -> `/body`
  - 建议 -> `/advice`
  - Agent -> `/agent`
  - 设置 -> `/settings`
- 原型参考路由仍可通过 `/prototype` 访问。
- 今日、训练、饮食、建议、Agent、设置至少各有一个可见 mock 交互。
- `Schedule` 不再作为误导性的主产品一级路由出现。
- `design-qa.md` 或新的 QA 记录明确说明：这是功能基础迁移，不是完整 Stitch 像素级迁移。

## 风险

- 第一版真实组件在逐页视觉迁移完成前，可能没有 Stitch HTML 那么像素级精确。
- 原型路由和产品路由并存时，如果标识不清，用户可能混淆。
- 内存 mock API 适合演示，但不能被误认为持久化数据。

## 决策

- 使用渐进迁移，而不是一次性重写全部页面。
- 保留现有 Stitch 实现，并移动到 `/prototype`。
- 产品导航以 PRD 路由结构为事实来源。
- 本阶段不新增 routing、状态管理、UI 组件或图表依赖。
