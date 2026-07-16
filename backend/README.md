# 945 Backend

这是 945 的真实后端入口。当前阶段已完成 FastAPI 空壳、健康检查、demo 用户接口、今日聚合接口和当前计划接口，还没有接入 MongoDB、LangGraph、RAG 或真实 Agent 工具层。

## 当前包含

```text
backend/
  app/
    main.py
    api/
      routes_demo.py
      routes_plans.py
      responses.py
    data/
      demo_data.py
    models/
      domain.py
    services/
      plan_service.py
      today_service.py
  tests/
    test_demo_api.py
    test_health.py
    test_plans_api.py
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

预期响应：

```json
{
  "data": {
    "status": "ok",
    "service": "945-backend"
  },
  "error": null
}
```

demo 用户：

```text
http://127.0.0.1:8000/api/demo-user
```

今日聚合：

```text
http://127.0.0.1:8000/api/today?user_id=demo-user-945&date=2026-07-11
```

当前计划：

```text
http://127.0.0.1:8000/api/plans/current?user_id=demo-user-945
```

这些接口当前使用 `backend/app/data/demo_data.py` 中的本地 demo 数据，字段形状对齐前端 `src/data/demoData.ts` 和 `docs/API_CONTRACT.md`。

## 运行测试

```powershell
python -m pytest backend/tests -q
```

## 下一步

下一步应继续实现结构化写入 API，而不是直接接 RAG：

1. `POST /api/workout-logs`
2. `POST /api/meal-logs/confirm-planned-meal`
3. `POST /api/body-metrics`
4. `POST /api/daily-checkins`
5. 前端 `httpApi` adapter
6. MongoDB repository
7. Agent 工具层
8. RAG 检索层
