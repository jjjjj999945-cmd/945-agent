# PRD 前端基础层 QA

最终结果：通过

## 范围

本 QA 验证第一版 PRD 驱动的功能基础层。它不是完整 Stitch 像素级还原验证。

## 验证命令

- `npm run build`
- `npm run qa:app`

## 证据

- `npm run build` 通过。
- `npm run qa:app` 通过，4 个 Playwright smoke tests 全部通过。
- 主产品路由可以渲染：
  - `/` -> 今日
  - `/workout` -> 训练
  - `/diet` -> 饮食
  - `/body` -> 身体数据
  - `/advice` -> 建议
  - `/agent` -> Agent
  - `/settings` -> 设置
- `/prototype` 和 `/prototype/diet` 仍可访问 Stitch reference。
- 主导航不暴露 `Schedule` 作为误导性顶层路由。
- 已检查核心 mock 交互：
  - Today：计划餐确认、每日打卡、Agent draft 确认、语言切换。
  - Workout：保存训练记录。
  - Diet：确认计划餐、保存手动餐食。
  - Body：保存体重数据。
  - Advice：采纳、忽略和稍后处理建议。
  - Agent：发送消息并确认 draft。
  - Settings：从设置页切换语言。
- 已检查此前容易无反馈的按钮：
  - Today：训练完成、查看原因、调整今日计划。
  - Plan：生成计划。

## 剩余工作

- 当前页面是信息架构和功能骨架，还不是最终视觉稿还原。
- 后续需要根据 Stitch reference 或新原型，把各页面升级为高保真 React 组件。
- 当前 API 仍为浏览器内存 mock API，后端准备好后需要替换为 FastAPI 集成。
- Agent 行为仍是 deterministic mock，未来需要接入 LangGraph 编排和真实 Agent。
