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
```

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
- `backend/app/repositories/mongo.py` 已提供 MongoDB repository 边界，用于后续把 demo store 的读写迁移到 MongoDB。
- `backend/app/services/repository_store.py` 已把结构化集合映射到 repository-backed store。
- `backend/app/agents/tool_registry.py` 提供 Agent 白名单工具注册、严格参数校验和显式分派；关键写入仍只生成草稿。
- `backend/app/rag/retriever.py` 提供本地关键词 RAG 检索，不保存主业务事实。
- `backend/app/agents/graph.py` 提供异步 Agent graph，用于安全检查、上下文构建、RAG 检索、Provider 调用、单轮工具执行和草稿校验。
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
```

开发环境启用真实 OpenAI：

```powershell
$env:945_APP_ENV="development"
$env:945_LLM_PROVIDER="openai"
$env:OPENAI_API_KEY="你的服务端 API Key"
$env:945_OPENAI_MODEL="你的 OpenAI 模型 ID"
$env:945_LLM_TIMEOUT_SECONDS="20"
```

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

## MongoDB repository 配置

当前默认仍使用本地 demo store：

```powershell
$env:945_STORAGE_BACKEND="demo"
```

后续切换 MongoDB repository 时使用这些环境变量：

```powershell
$env:945_STORAGE_BACKEND="mongo"
$env:945_MONGODB_URI="mongodb://127.0.0.1:27017"
$env:945_MONGODB_DATABASE="945"
```

当前已完成 MongoDB 文档转换、按集合 upsert、按条件查询、Pydantic model 还原、demo seed 和 repository-backed store 委托测试。默认 demo 模式仍不需要 MongoDB 进程。

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

## 运行测试

```powershell
python -m pytest backend/tests -q
```

真实 OpenAI 冒烟测试默认跳过，避免误触发费用。只有明确配置后才运行：

```powershell
$env:945_RUN_OPENAI_SMOKE_TESTS="1"
python -m pytest backend/tests/test_openai_smoke.py -q
```

前端兼容验证：

```powershell
npm run build
npm run qa:app
```

## 下一步

下一步建议进入真实模型联调和生产化准备，但不要破坏当前可测试闭环：

1. 用明确配置的服务端 API Key 做一次 OpenAI 冒烟验证。
2. 将本地关键词 RAG 替换或增强为 embedding/vector store。
3. 增加真实 MongoDB 集成环境和启动脚本。
4. 增加用户鉴权、数据隔离和生产配置。
5. 扩展计划生成、计划调整和确认工作流。
