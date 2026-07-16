# 945 Backend

这是 945 的真实后端入口。当前阶段已完成本地 demo 用户下的 MVP 后端闭环：资料、设置、计划读取、今日聚合、训练记录、饮食记录、身体数据、每日打卡、建议状态和最小 Agent 草稿对话。

当前后端默认仍然运行本地 demo store，但已经具备 MongoDB repository 边界、Agent 白名单工具层、本地 RAG 检索、确定性 Agent graph 和每周长期记忆摘要。真实大模型、生产鉴权和云部署仍不在当前 MVP 范围内。

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
      tools.py
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
- `backend/app/agents/tools.py` 提供 Agent 白名单工具；关键写入仍只生成草稿。
- `backend/app/rag/retriever.py` 提供本地关键词 RAG 检索，不保存主业务事实。
- `backend/app/agents/graph.py` 提供确定性 Agent graph，用于安全检查、意图路由、上下文构建、RAG 检索、工具草稿和回复生成。
- `backend/app/services/memory_service.py` 可以从结构化记录生成每周长期记忆摘要。
- `/api/agent/chat` 当前只做规则版草稿生成和高风险词安全提醒。
- Agent 不会自动保存训练或饮食记录；保存仍必须调用对应结构化写入接口。
- 高风险输入会返回安全提醒，不继续输出高强度训练建议。

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

## 运行测试

```powershell
python -m pytest backend/tests -q
```

前端兼容验证：

```powershell
npm run build
npm run qa:app
```

## 下一步

下一步建议进入真实模型和生产化准备，但不要破坏当前可测试闭环：

1. 接入真实 LLM provider，但保留 deterministic/mock provider 用于测试。
2. 将本地关键词 RAG 替换或增强为 embedding/vector store。
3. 增加真实 MongoDB 集成环境和启动脚本。
4. 增加用户鉴权、数据隔离和生产配置。
5. 扩展计划生成、计划调整和确认工作流。
