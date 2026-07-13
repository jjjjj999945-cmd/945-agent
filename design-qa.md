# 设计 QA

最终结果：通过

## 范围

将 React 实现与本地 `stitch-reference/` 中的 Stitch 导出进行对比。

已实现路由：

- `/` - 今日 Dashboard
- `/workout` - 训练详情 v3
- `/settings` - 设置与偏好 v2
- `/weekly-summary` - 周总结 v2
- `/agent-v3` - Agent Chat v3
- `/diet` - 饮食追踪 v2
- `/workout-alt` - 训练详情
- `/agent` - Agent Chat 最终校准
- `/onboarding` - 引导流程
- `/ai-adjustment` - AI 调整分析
- `/diet-alt` - 饮食追踪

## 证据

- `npm run build` 通过。
- Vite 开发服务器运行在 `http://localhost:5173/`。
- 浏览器 QA 在 `1280x720` 视口检查了全部 11 条路由。
- Chrome 交互 QA 检查了 11 条路由中的代表性控件：36 项检查，0 个失败，0 个控制台错误。
- 所有已检查路由都能渲染主要页面内容。
- 所有已检查路由的 `brokenImages` 均为 `0`。
- 所有已检查路由的 `remoteImages` 均为 `0`；Stitch 托管图片已从本地 `public/stitch-reference` 提供。
- 浏览器控制台没有错误日志。
- 原型操作现在会为主 CTA、图标按钮、日期控件、设置输入框、Agent chat 发送、路由导航、训练/饮食确认、批准、导出、关闭和引导初始化提供可见反馈。
- 实现期间使用的可见路由切换器已隐藏，不会改变 Stitch 视觉表面。
- 每个 screen 都注入了 Stitch body class 和内联样式块，保留页面级布局、背景、glass card 和模块差异。
- 额外本地 CSS 覆盖了 Stitch 的任意 Tailwind class，例如 `border-l-[3px]`、固定宽高、精确阴影和精确颜色工具类。

## 视觉对比

代表性视口截图已保存到 `qa-shots/`：

- `today-app.png` vs `today-ref.png`
- `workout-app.png` vs `workout-ref.png`
- `agent-app.png` vs `agent-ref.png`

React app 使用相同的 Stitch screen HTML body、本地资产、页面 body class 和内联样式块。剩余像素级差异主要来自浏览器/字体渲染和 CDN Tailwind 运行时行为；已检查视图中没有发现 P0/P1/P2 布局问题、资产缺失或运行时问题。

## 后续说明

- 若生产构建不能依赖 Tailwind CDN，需要把 Stitch Tailwind 配置迁移到本地 Tailwind/PostCSS 设置。
- 若本轮视觉实现需要中文本地化，应通过规划中的 i18n 层翻译可见文案，同时保持相同布局尺寸。

## MVP 基础层验证 - 2026-07-11

结果：通过

已检查：

- MVP 基础层变更后，`npm run build` 通过。
- Vite 开发服务器可通过 `http://localhost:5173/` 访问。
- `http://localhost:5173/` 返回 HTTP 200。
- `http://localhost:5173/app` 返回 HTTP 200。
- `/app` 已接入业务数据驱动的今日页面入口。
- 现有 Stitch 原型路由仍可通过原型路由器访问。
- 新增 `npm run qa:app` Playwright smoke test，使用本机 Chrome 检查 `/app`。
- 计划餐确认已验证：点击确认后出现保存反馈，连续确认后营养进度从 `1480 / 2300` 变为 `1548 / 2300`。
- 每日打卡已验证：填写体重和睡眠后点击保存，页面出现已保存状态。
- Agent 草稿确认已验证：发送包含深蹲记录的消息后弹出 draft 确认框，确认后弹窗关闭。
- 语言切换已验证：切换到 `en-US` 后，导航和保存按钮文案变为英文。

历史问题：

- 应用内浏览器自动化无法连接，因为 Browser 插件在写入本地运行时资产时失败，错误为 `系统找不到指定的路径。 (os error 3)`。
- 该问题已通过项目本地 Playwright + Chrome smoke test 绕过，不再阻塞 MVP 基础层 QA。
