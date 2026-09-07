# 945 Backend

这是 945 的真实后端入口。当前阶段已完成本地 demo 用户下的 MVP 后端闭环：资料、设置、计划读取、今日聚合、训练记录、饮食记录、身体数据、每日打卡、建议状态和最小 Agent 草稿对话。

当前后端默认仍然运行本地 demo store 和 deterministic LLM Provider，但已经具备 MongoDB repository 边界、Agent 白名单工具层、本地 RAG 检索、Provider Router、OpenAI Responses Provider 和每周长期记忆摘要。生产鉴权、云部署和向量数据库仍不在当前 MVP 范围内。

## 当前包含

```text
backend/
  app/
    main.py
    api/
      routes_advice.py
      routes_agent.py
      routes_body_metrics.py
      routes_daily_checkins.py
      routes_demo.py
      routes_meal_logs.py
      routes_plans.py
      routes_profile.py
      routes_settings.py
      routes_workout_logs.py
      responses.py
    data/
      demo_data.py
    models/
      domain.py
    agents/
      graph.py
      nodes.py
      prompts.py
      tool_registry.py
      tools.py
    llm/
      deterministic.py
      factory.py
      models.py
      openai_provider.py
    rag/
      retriever.py
    repositories/
      mongo.py
    services/
      demo_store.py
      memory_service.py
      plan_service.py
      repository_store.py
      today_service.py
  tests/
```

## 运行后端

在项目根目录执行：

```powershell
python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

健康检查：

```text
http://127.0.0.1:8000/health
```

## 已实现接口

```text
GET /health
GET /api/demo-user
GET /api/today?user_id=demo-user-945&date=2026-07-11
GET /api/plans/current?user_id=demo-user-945

GET /api/profile/{user_id}
POST /api/profile
PATCH /api/profile/{user_id}

GET /api/settings?user_id=demo-user-945
PATCH /api/settings

GET /api/workout-logs?user_id=demo-user-945
POST /api/workout-logs

GET /api/meal-logs?user_id=demo-user-945
POST /api/meal-logs
POST /api/meal-logs/confirm-planned-meal

GET /api/body-metrics?user_id=demo-user-945
POST /api/body-metrics
POST /api/daily-checkins

GET /api/advice?user_id=demo-user-945
PATCH /api/advice/{advice_id}/status

POST /api/agent/chat
GET /api/agent/messages?user_id=demo-user-945
GET /api/agent/runs?user_id=demo-user-945
GET /api/agent/runs/{agent_run_id}/trace?user_id=demo-user-945
GET /api/agent/metrics?user_id=demo-user-945
POST /api/agent/runs/{agent_run_id}/retry
```

## Agent 失败重试

每次 Agent 调用都会记录运行元数据，包括运行 ID、状态、耗时、Provider、模型、意图、草稿类型和错误码，不保存模型推理内容。

`GET /api/agent/runs?user_id=...` 只返回可观察性字段，不返回失败运行中的重试输入。

`GET /api/agent/runs/{agent_run_id}/trace?user_id=...` 返回该次运行的安全流程事件，例如安全检查、上下文读取、知识检索、模型生成、工具执行与草稿校验。事件只包含节点状态、错误码和数量类元数据，不包含用户输入、模型推理过程或思维链。

`GET /api/agent/metrics?user_id=...` 返回成功率、平均耗时、累计 token、生成次数、HTTP 尝试次数和按错误码聚合的失败次数，可用于真实模型接入后的质量与成本观察。

当一次 Agent 调用因 Provider 错误失败时，客户端可以显式调用 `POST /api/agent/runs/{agent_run_id}/retry`，请求体为 `{ "user_id": "..." }`。服务只会重新执行该失败请求，并创建一条新的运行记录；不会自动确认草稿，也不会写入训练、饮食或计划数据。

所有接口都使用统一响应格式：

```json
{
  "data": {},
  "error": null
}
```

错误响应示例：

```json
{
  "data": null,
  "error": {
    "code": "NOT_FOUND",
    "message": "Demo user not found.",
    "details": {
      "user_id": "missing-user"
    }
  }
}
```

字段形状对齐 `src/types/domain.ts` 和 `docs/API_CONTRACT.md`。

## 当前数据边界

- demo 用户固定为 `demo-user-945`。
- 结构化事实保存在 `backend/app/services/demo_store.py` 的进程内 store 中。
- 服务重启后，训练记录、饮食记录、身体数据、打卡、设置修改和 Agent 消息会重置。
- `backend/app/repositories/mongo.py` 提供 MongoDB repository 边界；设置 `945_STORAGE_BACKEND=mongo` 后，业务数据和 Agent run 会持久化到 MongoDB。
- `backend/app/services/repository_store.py` 已把结构化集合映射到 repository-backed store。
- `backend/app/agents/tool_registry.py` 提供 Agent 白名单工具注册、严格参数校验和显式分派；关键写入仍只生成草稿。
- `backend/app/rag/retriever.py` 提供本地关键词 RAG 检索，不保存主业务事实。
- `backend/app/agents/graph.py` 使用 LangGraph `StateGraph` 编排安全检查、上下文构建、RAG 检索、Provider 调用、单轮工具执行和草稿校验；demo 模式使用 `MemorySaver`，Mongo 模式使用 `MongoDBSaver`。
- 两种 checkpointer 都经过 Agent run 租约校验。Mongo 模式支持跨 Worker 的持久化 checkpoint 和用户手动恢复；旧租约不能写入新执行采用的 checkpoint。
- `backend/app/llm/factory.py` 提供 Provider Router：开发环境 OpenAI 失败会降级到 deterministic，生产环境会返回稳定错误。
- `backend/app/llm/openai_provider.py` 已接入 OpenAI Responses API，显式 `store=False`、`parallel_tool_calls=False`，并关闭 SDK 内部重试。
- `backend/app/services/memory_service.py` 可以从结构化记录生成每周长期记忆摘要。
- `/api/agent/chat` 默认使用 deterministic Provider；配置 OpenAI 后可以走真实模型，但模型只能提出白名单工具调用。
- Agent 不会自动保存训练或饮食记录；保存仍必须调用对应结构化写入接口。
- 高风险输入会返回安全提醒，不继续输出高强度训练建议。

## LLM Provider 配置

默认本地模式不需要 API Key：

```powershell
$env:945_APP_ENV="development"
$env:945_LLM_PROVIDER="deterministic"
$env:945_AGENT_MAX_RUNS_PER_HOUR="30"
$env:945_AGENT_MAX_TOKENS_PER_DAY="200000"
$env:945_AGENT_MAX_LOGICAL_GENERATIONS_PER_DAY="100"
```

`945_AGENT_MAX_RUNS_PER_HOUR` 是每个用户的进程内每小时 Agent 调用上限；设为 `0` 可关闭。超过上限时接口返回 `429 AGENT_USAGE_LIMIT`，不会调用 Provider 或写入业务记录。

`945_AGENT_MAX_TOKENS_PER_DAY` 是每个用户按 UTC 自然日累计的输入与输出 token 上限；设为 `0` 可关闭。达到上限时接口同样返回 `429 AGENT_USAGE_LIMIT`，并在调用 Provider 前拦截请求。

`945_AGENT_MAX_LOGICAL_GENERATIONS_PER_DAY` 是每个用户按 UTC 自然日累计的逻辑生成次数上限；设为 `0` 可关闭。它独立于 token 统计，可防止低 token 请求高频消耗 Provider 调用配额。

开发环境启用真实 OpenAI：

```powershell
$env:945_APP_ENV="development"
$env:945_LLM_PROVIDER="openai"
$env:OPENAI_API_KEY="你的服务端 API Key"
$env:945_OPENAI_MODEL="你的 OpenAI 模型 ID"
$env:945_LLM_TIMEOUT_SECONDS="20"
```

启用 DeepSeek（默认使用 `deepseek-v4-flash`，关闭 thinking mode，并限制每次最多输出 600 tokens）：

```powershell
$env:945_APP_ENV="production"
$env:945_LLM_PROVIDER="deepseek"
$env:DEEPSEEK_API_KEY="你的 DeepSeek API Key"
$env:945_DEEPSEEK_MODEL="deepseek-v4-flash"
$env:945_DEEPSEEK_MAX_TOKENS="600"
$env:945_LLM_TIMEOUT_SECONDS="20"
```

首次仅做一条低成本真实调用验证：

```powershell
$env:945_RUN_DEEPSEEK_SMOKE_TESTS="1"
python -m pytest backend/tests/test_deepseek_smoke.py -q
```

该测试只发送一个训练知识问题，不携带工具定义，不会生成草稿或写入训练、饮食、计划数据。不要将 `DEEPSEEK_API_KEY` 写入仓库、`.env.http`、测试快照或前端 `VITE_*` 变量。

生产环境启用 OpenAI 时必须配置 `OPENAI_API_KEY` 和 `945_OPENAI_MODEL`。缺少配置或 Provider 调用失败时，生产环境不会自动降级保存消息，而是返回稳定错误响应。

稳定错误码：

```text
LLM_CONFIG_ERROR
LLM_TIMEOUT
LLM_RATE_LIMITED
LLM_PROVIDER_ERROR
LLM_OUTPUT_INVALID
```

开发环境自动降级只体现在后端运行元数据中，对前端成功响应形状保持兼容。无论 deterministic 还是 OpenAI，模型都不能直接写入训练、饮食或计划数据；记录类操作只返回 `RecordDraft`，用户确认后再调用结构化 API。

## LangSmith 可观测性

945 已保留可选的 LangSmith 追踪接入，用于查看 Agent 图节点耗时、Provider 调用与失败链路。默认关闭；没有 LangSmith Key 不影响本地 demo、MongoDB 或 deterministic Provider。

启用时在启动后端的终端设置：

```powershell
$env:945_LANGSMITH_TRACING="true"
$env:LANGSMITH_API_KEY="你的 LangSmith API Key"
$env:LANGSMITH_PROJECT="945"
```

服务端会强制设置 `LANGSMITH_HIDE_INPUTS=true` 和 `LANGSMITH_HIDE_OUTPUTS=true`。发送到追踪系统的运行 metadata 仅包含匿名用户哈希、`request_id`、语言和 Provider；不会发送用户聊天正文、训练/饮食数据、profile、RAG 原文或模型推理过程。未设置 Key 时追踪保持关闭。

## MongoDB repository 配置

当前默认仍使用本地 demo store：

```powershell
$env:945_STORAGE_BACKEND="demo"
```

切换到 MongoDB repository 模式时使用这些环境变量：

```powershell
$env:945_STORAGE_BACKEND="mongo"
$env:945_MONGODB_URI="mongodb://127.0.0.1:27017"
$env:945_MONGODB_DATABASE="945"
$env:945_AGENT_LEASE_TTL_SECONDS="60"
$env:945_AGENT_LEASE_HEARTBEAT_SECONDS="15"
```

`945_AGENT_LEASE_TTL_SECONDS` 必须为正数；heartbeat 必须为正数且不能超过 TTL 的三分之一。Mongo 使用数据库服务端时间判断到期和续租，避免多个后端 Worker 的本机时钟差异。默认 demo 模式仍不需要 MongoDB 进程，但使用相同的租约状态机。

本机便携版已部署在 `D:\MongoDB`。启动命令：

```powershell
& "D:\MongoDB\server\mongodb-win32-x86_64-windows-8.3.4\bin\mongod.exe" --dbpath D:\MongoDB\data --bind_ip 127.0.0.1 --port 27017 --logpath D:\MongoDB\log\mongod.log
```

## LangGraph checkpoint 持久化

默认 demo 模式继续使用进程内 `MemorySaver`，适合本地演示，不会跨后端重启保留 Agent 图状态。

当设置 `945_STORAGE_BACKEND=mongo` 后，Agent 图会切换到 MongoDB checkpointer，并使用当前 `945_MONGODB_DATABASE` 中的两个专用集合：

```text
agent_checkpoints
agent_checkpoint_writes
```

这两个集合保存 LangGraph 的节点状态和中间写入，用于服务重启后的运行状态读取、排障与手动恢复；不会保存模型推理过程或对用户展示的思维链。训练、饮食和计划变更仍然只能通过用户确认后的结构化 API 写入。

`/api/agent/chat` 每次请求会生成新的 Agent run 和同名 `thread_id`。执行租约过期时，读取 run 或用户请求恢复只会先把任务标记为 `interrupted`，不会自动调用模型；用户显式调用 `POST /api/agent/runs/{agent_run_id}/resume` 后，服务才会竞争新租约，并从同一 `agent_run_id/thread_id` 的固定安全 checkpoint 恢复。只有当前租约能续租、更新 checkpoint、写终态和发布消息。

本机验证 Mongo checkpoint：

```powershell
$env:945_RUN_MONGO_INTEGRATION_TESTS="1"
python -m pytest backend/tests/test_agent_graph.py -q
```

## 运行测试

```powershell
python -m pytest backend/tests -q
```

## Agent 评测基线

```powershell
python -m backend.evals.run_agent_eval
```

该命令固定运行训练记录、饮食记录、计划调整、知识问答和高风险输入场景，输出每条场景的意图与草稿类型以及总通过率。它使用 deterministic Provider，只生成或校验 `RecordDraft`，不调用训练、饮食或计划的结构化写入接口，也不会消耗真实模型额度。

### Agent Eval 质量门

默认评测固定使用 deterministic Provider，适合本地和 CI，零模型费用：

```powershell
python -m backend.evals.run_agent_eval --json-output output/agent-eval.json
```

CI 只运行上面的确定性命令，绝不会自动运行 DeepSeek。报告会记录通过率、token、耗时和 HTTP 尝试次数；它不估算人民币或美元成本。

DeepSeek 小样本评测必须由开发者在本地显式执行，会产生 Provider 费用：

```powershell
$env:DEEPSEEK_API_KEY="your-deepseek-api-key"
python -m backend.evals.run_agent_eval --provider deepseek --json-output output/deepseek-eval.json
```

两种评测都只验证 Agent 输出和确认边界，不会直接写入训练、饮食或计划等结构化记录。

评测可输出机器可读 JSON 报告，适合作为本地或 CI 质量门：

```powershell
python -m backend.evals.run_agent_eval --json-output output/agent-eval.json
```

项目根目录也提供 `npm run qa:agent` 快捷命令。`.github/workflows/agent-eval.yml` 会在推送到 `master` 或创建 Pull Request 时运行后端测试和该评测，并上传 JSON 报告。评测失败、意图/草稿类型回归，或任一场景发生结构化写入时都会返回非零退出码。

真实 OpenAI 冒烟测试默认跳过，避免误触发费用。只有明确配置后才运行：

```powershell
$env:945_RUN_OPENAI_SMOKE_TESTS="1"
python -m pytest backend/tests/test_openai_smoke.py -q
```

也可使用 `npm run qa:openai`。它只执行两条最小请求：一个中文训练知识问题和一个训练记录草稿请求；不会自动写入训练、饮食或计划数据。

运行前需设置：

```powershell
$env:945_APP_ENV="development"
$env:945_LLM_PROVIDER="openai"
$env:OPENAI_API_KEY="你的服务端 API Key"
$env:945_OPENAI_MODEL="你的模型 ID"
$env:945_RUN_OPENAI_SMOKE_TESTS="1"
npm run qa:openai
```

不要把 API Key 写入仓库、`.env.http`、测试快照或前端 `VITE_*` 变量。未设置 `945_RUN_OPENAI_SMOKE_TESTS=1` 时，测试会跳过，不产生模型调用。

前端兼容验证：

```powershell
npm run build
npm run qa:app
```

真实 HTTP 联调：

```powershell
npm run qa:http
```

`qa:http` 会启动 FastAPI 和 HTTP 模式 Vite，并显式固定 `945_STORAGE_BACKEND=demo`、`945_LLM_PROVIDER=deterministic`、`945_APP_ENV=development`。因此不需要 MongoDB 或 API Key，且不会调用真实 OpenAI。

Mongo 持久化 HTTP QA：

```powershell
npm run qa:mongo
```

该命令仅清空专用的 `945_mongo_qa` 数据库，随后以 Mongo repository 跑完整 HTTP 用例；不会删除 `945_integration` 或其他数据库。

## 前端确认写入契约

- `/api/agent/chat` 只返回聊天消息、建议和 `RecordDraft`，不会自动保存训练、饮食或计划。
- 用户确认训练草稿后，前端调用 `POST /api/workout-logs`。
- 用户确认饮食草稿后，前端调用 `POST /api/meal-logs`；计划餐确认使用 `POST /api/meal-logs/confirm-planned-meal`。
- 用户确认计划调整草稿后，前端调用 `POST /api/plans/{plan_id}/adjust` 创建新的 active 计划。
- 高风险输入优先返回安全提醒，不生成可确认的记录草稿。

## 下一步

下一步建议进入真实模型联调和生产化准备，但不要破坏当前可测试闭环：

1. 用明确配置的服务端 API Key 做一次 OpenAI 冒烟验证。
2. 将本地关键词 RAG 替换或增强为 embedding/vector store。
3. 增加真实 MongoDB 集成环境和启动脚本。
4. 补齐生产级鉴权、数据隔离审计和部署配置。
5. 扩展计划生成、计划调整和确认工作流。
# 945 后端

945 使用 FastAPI 提供训练计划、饮食记录、身体数据、每日打卡、建议与 Agent 草稿接口。默认以 `demo` 存储模式运行；设置 `945_STORAGE_BACKEND=mongo` 后，业务记录和邮箱密码凭据都会持久化到 MongoDB。

## 启动

```powershell
python -m uvicorn backend.app.main:app --reload
```

Mongo 模式需要先启动 MongoDB：

```powershell
$env:945_STORAGE_BACKEND = "mongo"
$env:945_MONGODB_DATABASE = "945"
python -m uvicorn backend.app.main:app --reload
```

## 认证与多用户边界

- `POST /api/auth/register`：创建邮箱密码账号；密码使用 PBKDF2-HMAC-SHA256 哈希保存，绝不通过 API 返回。
- `POST /api/auth/register`、`POST /api/auth/login`：返回 15 分钟 access token，并通过同源 `HttpOnly` Cookie 写入 30 天 refresh token。
- `POST /api/auth/refresh`：轮换 refresh token 并返回新的 access token；旧 refresh token 不可重放。
- `GET /api/auth/me`、`GET /api/auth/sessions`：读取当前用户与已登录设备摘要；摘要不包含 refresh token 或其摘要。
- `DELETE /api/auth/sessions/{session_id}`、`POST /api/auth/logout`、`POST /api/auth/logout-all`：分别撤销其他设备、当前设备或全部设备；已撤销设备的 access token 会立即失效。
- `POST /api/auth/change-password`：已登录用户校验当前密码后修改密码，并撤销全部设备会话；新密码至少 8 位。
- 已携带 Bearer token 的业务请求只能访问 token 所属的 `user_id`，跨用户请求返回 `403 FORBIDDEN`。
- 生产环境默认强制所有业务接口带 token；开发和 demo 环境可设置 `945_AUTH_REQUIRED=false` 保持兼容。
- 登录失败会按邮箱在单进程内限流，默认 15 分钟内 5 次失败后返回 `429 LOGIN_RATE_LIMITED`。可通过 `945_AUTH_LOGIN_MAX_ATTEMPTS` 和 `945_AUTH_LOGIN_WINDOW_SECONDS` 调整。
- 多用户持久化只在 Mongo 模式可用。demo 模式仍是固定的本地演示用户，进程重启后会恢复初始状态。

access token 使用 HMAC 并包含设备 session ID；每次业务鉴权都会校验用户会话版本与该设备会话。refresh token 仅以 `945_AUTH_SECRET` 派生的 HMAC-SHA256 摘要保存，绝不进入日志、响应或前端状态。上线生产前仍需设置高强度 `945_AUTH_SECRET`，并接入 Redis 限流、邮箱验证和密码重置流程。

可选配置：`945_AUTH_ACCESS_TOKEN_TTL_SECONDS=900`、`945_AUTH_REFRESH_TOKEN_TTL_SECONDS=2592000`。前端仅在内存保存 access token；页面刷新时通过同源 Cookie 调用 `/api/auth/refresh` 恢复会话。

## Docker 部署

1. 启动 Docker Desktop，并将 `.env.production.example` 复制为 `.env.production`。
2. 为 `945_AUTH_SECRET` 设置至少 32 字符的随机值，并填入真实的 `DEEPSEEK_API_KEY`；该文件仅在本机保存，不能提交到 Git。
3. 需要 LangSmith 追踪时，填入 `LANGSMITH_API_KEY` 并将 `945_LANGSMITH_TRACING=true`。
4. 在仓库根目录执行：

```powershell
docker compose up --build -d
```

客户端服务默认在 `http://127.0.0.1:8080`，健康检查为 `http://127.0.0.1:8080/health`。Nginx 会将 `/api/*` 和 `/health` 转发到 FastAPI。生产模式必须先登录取得 Bearer token，MongoDB 使用命名卷 `mongo_data` 持久化数据。

查看运行状态、排查日志和停止服务：

```powershell
docker compose ps
docker compose logs backend
docker compose logs frontend
docker compose down
```

普通 `docker compose down` 会保留 `mongo_data` 中的数据；`docker compose down -v` 会删除本机 MongoDB 数据，除非明确要清空数据，否则不要使用。

## 验证

```powershell
python -m pytest backend/tests -q
npm run build
npm run qa:app
```

### Lv4 统一验收

默认完整验收为零模型费用，会串行运行后端测试、50 条确定性 Agent Eval、前端构建、真实 HTTP QA 和 Mongo QA；该命令不会调用 DeepSeek：

```powershell
npm run qa:lv4
```

只有离线检查全部通过后，才可显式运行 5 条真实 DeepSeek 样本：

```powershell
npm run qa:lv4:deepseek
```

真实样本固定覆盖训练草稿、饮食草稿、计划调整草稿、训练知识问答和高风险安全输入。硬门槛为至少 `4/5`、安全用例必须通过、结构化写入必须为 `0`。缺少 `DEEPSEEK_API_KEY` 时会在付费调用前失败；离线检查失败时会直接跳过 DeepSeek。

默认报告：

```text
output/lv4-acceptance.json
output/lv4-acceptance.md
```

付费模式报告：

```text
output/lv4-acceptance-deepseek.json
output/lv4-acceptance-deepseek.md
```

JSON 和中文 Markdown 报告包含完成度矩阵、稳定失败分类、耗时、token、逻辑生成次数和 HTTP 尝试次数，不包含 Key、Authorization、聊天正文、模型完整输出或思维链。DeepSeek 平均单例耗时超过 `10000 ms`、平均单例总 token 超过 `2000`，或 HTTP 尝试次数高于逻辑生成次数时只产生工程提醒，不作为硬阻断；实际金额以 DeepSeek 控制台账单为准。
