# 945 Backend

这是 945 的真实后端入口。当前阶段已完成本地 demo 用户下的 MVP 后端闭环：资料、设置、计划读取、今日聚合、训练记录、饮食记录、身体数据、每日打卡、建议状态和最小 Agent 草稿对话。

当前后端仍然是本地 demo store，不是生产级后端。它还没有接入 MongoDB、LangGraph、RAG 或真实大模型；这些会在结构化 API 稳定后作为下一阶段替换和增强。

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
    services/
      demo_store.py
      plan_service.py
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
- `/api/agent/chat` 当前只做规则版草稿生成和高风险词安全提醒。
- Agent 不会自动保存训练或饮食记录；保存仍必须调用对应结构化写入接口。
- 高风险输入会返回安全提醒，不继续输出高强度训练建议。

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

下一步建议先接前端 HTTP adapter，再做数据库持久化，不要直接把真实 Agent 接进页面：

1. 新增 `src/services/httpApi.ts` 和 `src/services/apiClient.ts`。
2. 让页面能在 mock API 和真实 FastAPI 之间切换。
3. 用 MongoDB repository 替换 `demo_store.py`。
4. 把 Agent 草稿生成改造成工具层。
5. 加 RAG 知识库，只检索动作知识、饮食知识、产品规则和用户长期摘要。
6. 最后接 LangGraph 编排真实 Agent。
