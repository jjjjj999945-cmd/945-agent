# 945 Backend

这是 945 的真实后端入口。当前阶段只完成 FastAPI 空壳和健康检查，还没有接入 MongoDB、LangGraph、RAG 或真实 Agent 工具层。

## 当前包含

```text
backend/
  app/
    main.py
    api/
      responses.py
  tests/
    test_health.py
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

## 运行测试

```powershell
python -m pytest backend/tests -q
```

## 下一步

下一步应继续实现结构化 API，而不是直接接 RAG：

1. `GET /api/demo-user`
2. `GET /api/today`
3. `GET /api/plans/current`
4. 训练、饮食、身体数据和每日打卡写入接口
5. 前端 `httpApi` adapter
6. MongoDB repository
7. Agent 工具层
8. RAG 检索层
