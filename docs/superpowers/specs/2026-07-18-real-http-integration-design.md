# 945 真实前后端联调设计

日期：2026-07-18  
状态：待用户审核

## 1. 目标

把 945 桌面客户端从“页面默认调用 `mockApi`”推进到“可以通过独立 HTTP 模式调用真实 FastAPI”，并用自动化测试证明主要产品流程能够跨越浏览器、HTTP adapter、FastAPI、业务 service 和本地 demo store 完成闭环。

本阶段不以生产部署为目标。联调环境固定使用：

- `945_STORAGE_BACKEND=demo`
- `945_LLM_PROVIDER=deterministic`
- demo 用户 `demo-user-945`
- 桌面 Chrome 视口

## 2. 方案选择

### 方案 A：双服务真实端到端联调（采用）

Playwright 启动 FastAPI 和 HTTP 模式 Vite，浏览器通过 `httpApi` 请求真实后端。测试从页面操作开始，并观察页面反馈和后端聚合结果。

优点：能够发现 CORS、端口、序列化、接口字段、状态刷新和页面交互之间的真实问题。缺点：测试时间比纯单元测试稍长，需要管理两个本地服务。

### 方案 B：只做 HTTP adapter 契约测试

在前端测试中模拟 `fetch`，检查 URL、请求体和响应转换。

优点：快且容易定位 adapter 问题。缺点：无法证明 FastAPI 实际响应与前端契约一致，也无法覆盖浏览器和 CORS。

### 方案 C：直接接 MongoDB 和真实 OpenAI

在联调时同时启用 MongoDB、OpenAI Provider 和真实前端。

优点：更接近生产环境。缺点：数据库、网络、API Key、费用、模型不确定性会干扰基础契约验证，不适合作为第一层联调。

本阶段采用方案 A；必要的 adapter 级断言可以作为方案 A 的补充，但不替代真实链路。

## 3. 运行架构

```text
Playwright Desktop Chrome
  -> Vite :5177 --mode http
  -> httpApi
  -> FastAPI :8000
  -> service / Agent graph
  -> demo store + deterministic Provider
```

新增 HTTP 专用运行入口，不改变普通开发和现有 mock QA：

```text
npm run dev          -> 5173，默认 mock
npm run qa:app       -> 现有 mock 页面测试
npm run dev:http     -> 5177，使用 httpApi
npm run qa:http      -> 自动启动 FastAPI + HTTP Vite 并执行真实联调测试
```

HTTP 模式配置由 `.env.http` 提供：

```text
VITE_945_API_MODE=http
VITE_945_API_BASE_URL=http://127.0.0.1:8000
```

普通开发仍默认使用 `mockApi`。只有显式选择 HTTP 模式时才请求 FastAPI，避免后端未启动时破坏当前可演示客户端。

## 4. 组件边界

### 4.1 `apiClient`

只负责根据 Vite mode 选择 `mockApi` 或 `httpApi`。页面不得直接读取环境变量，也不得直接调用 `fetch`。

### 4.2 `httpApi`

负责：

- 组装路径、查询参数和 JSON 请求体。
- 解析统一响应 `{ data, error }`。
- 将网络错误转换为稳定的 `NETWORK_ERROR`。
- 聚合训练、饮食和身体页面需要的多个后端请求。

它不保存业务状态，也不在前端伪造写入成功。

### 4.3 FastAPI

继续负责请求校验、统一错误响应、业务服务调用和 demo store 写入。CORS 允许 HTTP 联调端口 `5177`。

### 4.4 页面

页面继续只依赖统一的 `api` 接口。操作成功后必须刷新或局部更新真实数据；操作失败时必须展示可见反馈，不能把失败当成功处理。

## 5. 数据流

### 5.1 计划餐确认

```text
Diet/Today 页面点击确认
  -> httpApi.confirmPlannedMeal
  -> POST /api/meal-logs/confirm-planned-meal
  -> FastAPI 写入 meal_logs
  -> 页面重新读取 today/diet 数据
  -> 已摄入热量和蛋白质发生变化
```

### 5.2 每日打卡和身体数据

```text
页面提交表单
  -> POST /api/daily-checkins 或 POST /api/body-metrics
  -> demo store 保存
  -> 再次读取页面数据时返回新记录
```

### 5.3 Agent 记录草稿确认

```text
用户消息
  -> POST /api/agent/chat
  -> deterministic Provider + Agent tools
  -> 返回 RecordDraft，不写结构化记录
  -> 用户点击确认
  -> workout draft 调用 POST /api/workout-logs
     或 meal draft 调用 POST /api/meal-logs
  -> 页面显示保存结果
```

计划调整草稿仍不得直接修改计划；在专用计划调整确认接口完成前，只展示草稿和边界提示。

## 6. 错误处理

- 后端未启动或网络失败：返回 `NETWORK_ERROR`，页面显示失败反馈。
- FastAPI 返回 `{ data: null, error }`：页面展示后端错误，不更新成功状态。
- 请求体不合法：保留 HTTP `422` 状态；adapter 将 FastAPI 的 `detail` 响应归一化为 `VALIDATION_ERROR`。
- 非 `2xx` 且响应已经符合 `{ data, error }` 时保留后端错误；其他非 JSON 或协议不兼容响应归一化为 `HTTP_ERROR`，避免页面因 JSON 解析异常崩溃。
- Agent Provider 失败：开发环境遵循现有 deterministic 降级策略；不得保存半条消息或自动写入记录。
- 测试数据隔离：HTTP QA 每次启动新的 FastAPI 进程，并使用单 worker 顺序执行，避免 demo store 在并行测试间互相污染。

## 7. 自动化测试

新增独立 Playwright HTTP 配置，包含两个 `webServer`：

1. FastAPI `127.0.0.1:8000`
2. Vite HTTP 模式 `127.0.0.1:5177`

真实联调至少覆盖：

- `/health` 和业务页面初始加载。
- 今日页读取真实 `/api/today`。
- 计划餐确认后真实营养汇总变化。
- 每日打卡提交成功且重新读取可见。
- 身体数据保存后列表或最新指标更新。
- Agent 训练草稿在确认前不产生训练记录，确认后才产生记录。
- Agent 饮食草稿在确认前不产生饮食记录，确认后才产生记录。
- 高风险 Agent 输入返回安全提醒且不产生草稿。
- Playwright 通过拦截并中止 `/api/*` 请求模拟后端不可用，页面必须显示可见错误反馈。

现有验证继续保留：

```powershell
python -m pytest backend/tests -q
npm run build
npm run qa:app
```

新增验证：

```powershell
npm run qa:http
```

## 8. 验收标准

- 不修改页面对 `api` 的统一依赖方式。
- 普通 `npm run dev` 和 `npm run qa:app` 继续使用 mock 并通过。
- `npm run qa:http` 在没有 MongoDB、OpenAI API Key 的机器上可重复通过。
- HTTP QA 的关键写入由 FastAPI 完成，而不是浏览器内存模拟。
- Agent 草稿确认边界得到端到端证明：确认前无结构化写入，确认后调用对应结构化 API。
- 所有用户可见失败都有明确反馈。
- 文档说明如何分别运行 mock 模式、HTTP 模式和真实 OpenAI 可选模式。

## 9. 不在本阶段范围

- 把 HTTP 模式改成所有开发场景的默认值。
- 启用真实 OpenAI 冒烟测试。
- 启动或部署真实 MongoDB。
- embedding/vector store 升级。
- 生产鉴权、用户隔离、云部署。
- 移动端适配或测试。
