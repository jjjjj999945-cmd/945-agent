# Stitch UI 原型实现计划

> **给 agentic worker：** 必须使用子技能：推荐 `superpowers:subagent-driven-development`，或使用 `superpowers:executing-plans`，按任务逐步执行本计划。步骤使用 checkbox（`- [ ]`）语法跟踪。

**目标：** 在 `D:\Codex\945` 中构建 React 前端，尽量还原提供的 Stitch 页面，用于 945 健身与饮食 Agent 工作台。

**架构：** 使用自包含 Vite React app。将每个 Stitch screen 转为有路由支撑的 React 页面，使用共享 token 还原 Refined Glacier Light 视觉系统，复用 shell/navigation，并在布局不同的位置保留页面专属模块。

**技术栈：** Vite、React、TypeScript、CSS modules/global CSS、静态 mock 数据、来自 Stitch 导出的本地图片/HTML 参考。

## 全局约束

- Stitch 截图和 `screen.html` 文件是视觉事实来源。
- PRD 是产品和交互事实来源。
- 不要把 Stitch HTML 作为 iframe app 实现。
- 保留页面专属模块差异，不强行套用一个通用模板。
- 提供 `zh-CN` 和 `en-US` i18n 结构；中文可以作为主语言。
- 只实现真实感本地 demo 交互；不实现后端、登录、支付、医疗声明、图片识别、穿戴设备或社区功能。
- 使用运行中的开发服务器和浏览器截图进行验证。

---

### 任务 1：搭建 App 和参考资产

**文件：**
- 创建：`package.json`、`index.html`、`src/`、`public/stitch-reference/`
- 修改：无

**交付物：** Vite React app 可以构建，并能本地访问 Stitch 参考截图。

### 任务 2：共享视觉系统

**文件：**
- 创建：`src/styles.css`、`src/data/i18n.ts`、`src/data/mockData.ts`、`src/components/AppShell.tsx`、`src/components/ui.tsx`

**交付物：** Glacier light tokens、导航、按钮、卡片、进度条、图表基础元素和表单控件匹配 Stitch 比例和色板。

### 任务 3：页面路由

**文件：**
- 创建：`src/pages/*.tsx`、`src/App.tsx`、`src/main.tsx`

**交付物：** 11 个 Stitch screen 都有对应路由和可见的页面专属模块结构。

### 任务 4：交互

**文件：**
- 修改：`src/pages/*.tsx`、`src/App.tsx`

**交付物：** 导航、tab、toggle、checkbox、饮食/训练确认、引导字段、语言切换和 chat 输入都能基于 demo 状态给出可见反馈。

### 任务 5：验证与视觉 QA

**文件：**
- 创建：`design-qa.md`

**交付物：** 开发服务器可运行，app 可构建，截图已与 Stitch 参考对比，并修复 QA 中发现的 P0/P1/P2 视觉或运行时问题。
