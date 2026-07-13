# 945 Stitch 原型交接说明

版本：v0.1  
日期：2026-07-11  
状态：原型到工程交接说明  

## 1. 当前状态

当前项目已经包含 Stitch 参考导出和一个 Vite React 包装层。

现有实现特点：

- `src/App.tsx` 动态加载 `public/stitch-reference/*/screen.html`。
- `src/screens.ts` 定义 11 个 Stitch screen 和路由。
- 现有页面主要是 Stitch HTML 的展示和轻量交互模拟。
- `design-qa.md` 记录了现有视觉 QA 结果。

这说明当前前端更接近“可浏览原型”，不是最终业务化 React 实现。

## 2. 已有 Stitch 页面

当前 `src/screens.ts` 中包含：

- `/` - 今日 Dashboard
- `/workout` - 训练详情 v3
- `/settings` - 设置与偏好 v2
- `/weekly-summary` - 周总结 v2
- `/agent-v3` - Agent Chat v3
- `/diet` - 饮食追踪 v2
- `/workout-alt` - 训练详情备选版
- `/agent` - Agent Chat 最终校准版
- `/onboarding` - 引导流程
- `/ai-adjustment` - AI 调整分析
- `/diet-alt` - 饮食追踪备选版

## 3. 工程化目标

下一阶段不是继续堆 Stitch HTML，而是逐步把原型转成业务组件：

1. 建立 TypeScript 数据类型。
2. 建立 mock API。
3. 建立 i18n 文案结构。
4. 建立真实 React 页面骨架。
5. 按页面逐个替换 Stitch HTML。
6. 保留 Stitch screenshot 作为视觉参考。

## 4. 保留内容

建议保留：

- `stitch-reference/`
- `public/stitch-reference/`
- `qa-shots/`
- `design-qa.md`
- `docs/superpowers/plans/2026-07-11-stitch-ui-prototype-implementation.md`

这些内容作为视觉和原型参考。

## 5. 不建议长期保留为产品实现的内容

不建议把以下方式作为最终产品架构：

- 用 `dangerouslySetInnerHTML` 长期渲染 Stitch HTML。
- 依赖 Stitch screen 内联样式作为业务 UI 系统。
- 在 `App.tsx` 中集中处理所有页面交互。
- 通过按钮文字和 icon 字符串判断业务行为。

这些方式适合原型，不适合长期维护。

## 6. 推荐迁移顺序

### 阶段 1：基础层

- 创建 `src/types/domain.ts`
- 创建 `src/data/demoData.ts`
- 创建 `src/services/mockApi.ts`
- 创建 `src/i18n/zh-CN.ts`
- 创建 `src/i18n/en-US.ts`

### 阶段 2：应用外壳

- 创建真实 `AppShell`
- 创建导航
- 创建路由状态
- 接入语言切换

### 阶段 3：今日页面

- 用真实 React 组件实现今日 Dashboard。
- 使用 mock API 的 `/today` 数据形状。
- 保留 Stitch today screenshot 作为视觉参考。

### 阶段 4：记录流程

- 训练记录
- 计划餐确认
- 手动饮食记录
- 每日打卡
- 身体数据记录

### 阶段 5：Agent 流程

- Agent Chat
- record draft
- confirmation modal
- advice card
- weekly adjustment confirmation

## 7. 验收要求

每迁移一个页面，必须确认：

- 页面使用业务数据，而不是硬编码 Stitch HTML。
- 页面文案走 i18n。
- 页面支持 mock API 状态变化。
- 页面移动端可用。
- 页面与对应 Stitch reference 在信息层级上保持一致。
