# 945 是怎么一步步搭建起来的

版本：v0.1  
日期：2026-07-15  
状态：项目学习与搭建说明

## 1. 先理解一句话

945 的搭建顺序不是“先写 Agent 聊天框”，而是：

```text
产品闭环 -> 数据模型 -> API 契约 -> 前端 mock -> 真实页面 -> QA -> 后端 -> Agent -> RAG
```

原因很简单：健身 Agent 不只是聊天。它必须知道用户目标、计划、训练记录、饮食记录、身体数据和建议状态。没有这些结构化数据，Agent 就只能泛泛聊天，不能形成长期闭环。

## 2. 第一步：定义产品边界

先写 `PRD.md`。

这里确定了 945 的产品边界：

- 产品名叫 945。
- 第一版使用本地 demo 用户。
- 当前只做桌面客户端。
- 第一版支持训练计划、饮食计划、数据记录和建议闭环。
- Agent 不能静默保存关键数据。
- Agent Chat 不替代结构化页面。
- 第一版不做医疗诊断、穿戴设备、食物图片识别、完整账号体系。

这一步的作用是避免项目变成“什么都想做”的 AI 聊天工具。

## 3. 第二步：定义数据模型

然后写 `docs/DATA_MODEL.md`。

核心集合是：

```text
users
user_profiles
plans
daily_checkins
body_metrics
workout_logs
meal_logs
agent_advice
agent_messages
```

这些数据模型回答的是：

- 用户是谁。
- 用户目标是什么。
- 当前计划是什么。
- 今天练了什么。
- 今天吃了什么。
- 身体数据怎么变化。
- Agent 基于什么给建议。

这一步决定了后面页面、API、Agent 工具都围绕同一套事实工作。

## 4. 第三步：定义 API 契约

接着写 `docs/API_CONTRACT.md`。

API 契约把未来后端接口先定出来，例如：

- `GET /api/today`
- `POST /api/workout-logs`
- `POST /api/meal-logs/confirm-planned-meal`
- `POST /api/body-metrics`
- `POST /api/daily-checkins`
- `POST /api/agent/chat`

这一步的作用是：即使后端还没写，前端也知道未来应该怎么拿数据、怎么写数据。

## 5. 第四步：创建前端项目基础

当前项目是 React + Vite + TypeScript。

核心结构：

```text
src/
  App.tsx
  components/business/
  pages/
  types/
  data/
  services/
  i18n/
```

各目录职责：

| 目录 | 职责 |
| --- | --- |
| `types/` | 定义 User、Plan、WorkoutLog、MealLog、AgentAdvice 等类型 |
| `data/` | 放本地 demo 数据 |
| `services/` | 放 mock API 和未来真实 API adapter |
| `pages/` | 放今日、训练、饮食、身体数据、建议、Agent、设置页面 |
| `components/business/` | 放业务组件和应用外壳 |
| `i18n/` | 放中文和英文文案 |

## 6. 第五步：用 mockApi 模拟真实后端

当前前端不是直接读取 `demoData`，而是通过 `mockApi`。

例如：

```text
TodayPage -> api.confirmPlannedMeal -> mockApi -> 更新内存状态
```

这样做是为了让前端先像真实产品一样运行：

- 确认计划餐后，热量和蛋白质进度会变化。
- 保存身体数据后，页面有反馈。
- Agent 输入训练记录后，会生成记录草稿。
- 用户确认草稿后，才显示保存反馈。

以后真实后端接入时，目标是把：

```text
mockApi
```

替换为：

```text
httpApi
```

页面本身尽量不用大改。

## 7. 第六步：搭桌面客户端页面

当前已经有这些业务页面：

```text
/            今日
/plan        计划
/workout     训练
/diet        饮食
/body        身体数据
/advice      建议
/agent       Agent
/settings    设置
/prototype   Stitch 参考页
```

最近的桌面端 P0 主要补了三件事：

1. `/agent` 增加明确页面标题 `945 智能教练`。
2. `/workout` 从单次训练执行页扩展成“训练计划中心”。
3. `/settings` 把可用控件和后续能力边界说清楚，并补点击反馈。

这一步的目标是让桌面客户端像一个真实产品，而不是只像一组静态原型图。

## 8. 第七步：保留 Stitch 原型作为参考

Stitch 导出的页面没有直接替代业务页面，而是放在 `/prototype/*`。

原因：

- Stitch 原型适合看视觉和布局。
- 真实产品需要数据、状态、API、i18n 和测试。
- 原型不应该控制主产品路由。

所以当前策略是：

```text
主产品页面：React + mockApi + domain types
视觉参考：/prototype/*
```

## 9. 第八步：加自动化 QA

当前使用 Playwright 做桌面客户端 QA。

主要验证：

- 主路由能打开。
- Stitch 参考页仍可访问。
- 计划餐确认能反馈。
- 手动餐食能保存。
- 身体数据能保存。
- Agent 草稿确认能跑通。
- 设置语言切换能跑通。
- Agent / Workout / Settings 的桌面语义完整。

常用命令：

```powershell
npm run build
npm run qa:app
```

构建负责确认 TypeScript 和 Vite 没问题。  
QA 负责确认关键用户流程没有被改坏。

## 10. 第九步：为什么现在还没直接搭 RAG

RAG 要搭，但不应该比结构化数据更早成为核心。

如果过早搭 RAG，会出现几个问题：

- 用户训练记录可能无法精确统计。
- 饮食热量和蛋白质难以可靠计算。
- 计划调整无法做版本控制。
- Agent 很难知道哪些数据是事实，哪些只是聊天上下文。

所以正确顺序是：

```text
结构化数据和 API 先稳定
  -> Agent 工具层读取这些数据
    -> RAG 补充动作、饮食和产品规则知识
```

## 11. 第十步：下一阶段怎么搭后端

下一阶段建议按这个顺序：

### 10.1 创建 backend 目录

先建：

```text
backend/
  app/
    main.py
```

只做：

- FastAPI 应用入口。
- `/health`。
- 统一响应格式。

### 10.2 实现不依赖 Agent 的 API

先做结构化接口：

- 今日聚合。
- 当前计划。
- 训练记录。
- 饮食记录。
- 身体数据。
- 每日打卡。
- 设置。

这一步完成后，即使没有大模型，945 也已经是一个真实数据工作台。

### 10.3 接 MongoDB

把 demo 数据从内存迁到数据库。

重点是：

- 重启后数据不丢。
- 每个集合字段和 `DATA_MODEL.md` 对齐。
- 今日页能从多个集合聚合出状态摘要。

### 10.4 前端接真实 API

新增：

```text
src/services/httpApi.ts
src/services/apiClient.ts
```

目标：

- mock 模式还能跑。
- 真实后端模式也能跑。
- 页面不关心底层数据来自哪里。

### 10.5 搭 Agent 工具层

先做工具，不急着做复杂聊天：

- 读取今日上下文。
- 读取当前计划。
- 生成训练记录草稿。
- 生成饮食记录草稿。
- 生成计划调整草稿。

### 10.6 再接 RAG

第一批 RAG 知识库只放：

- 动作知识。
- 饮食知识。
- 945 产品规则。
- 安全边界。

不要把每条训练记录和饮食记录直接当作主知识库。长期记录要先进数据库，再定期生成摘要进入 RAG。

## 12. 你现在应该怎么读这个项目

推荐阅读顺序：

1. `PRD.md`
2. `README.md`
3. `docs/DATA_MODEL.md`
4. `docs/API_CONTRACT.md`
5. `docs/AGENT_BACKEND_RAG_ARCHITECTURE.md`
6. `src/types/domain.ts`
7. `src/data/demoData.ts`
8. `src/services/mockApi.ts`
9. `src/pages/TodayPage.tsx`
10. `src/pages/WorkoutPage.tsx`
11. `tests/prd-foundation.spec.ts`

按这个顺序读，你会先理解产品，再理解数据，再理解页面，最后理解测试。

## 13. 当前项目状态

当前阶段可以理解为：

```text
桌面客户端 demo 已成型
  -> mock API 已能模拟关键写入
  -> Playwright 已覆盖核心流程
  -> 后端和 Agent/RAG 还没正式实现
```

下一步真正写代码时，应该从 `backend/` 的 FastAPI 空壳开始，而不是直接写 RAG。
