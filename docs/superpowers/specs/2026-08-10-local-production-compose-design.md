# 本机 Docker Compose 稳定运行设计

## 目标

在不改变前端 UI、视觉、路由或 Agent 产品能力的前提下，让 945 可以在 Windows 本机以接近生产的方式稳定运行。使用者通过一个地址访问页面；重启整套容器后，账号、业务记录、Agent 运行记录和 LangGraph checkpoint 仍然保留。

## 范围

- 复用现有 `docker-compose.yml`、`Dockerfile.backend`、`Dockerfile.frontend` 与 `deploy/nginx.conf`。
- 补齐本机启动说明、生产配置校验和必要的 Compose 健康检查。
- 使用 Git 忽略的 `.env.production` 保存本机密钥。
- 验证注册、登录、DeepSeek 对话、草稿确认、Mongo 持久化和健康检查。

不在本阶段修改前端 UI、样式、页面排版、Prompt、RAG 或 Agent 工具定义；不部署公网。

## 运行拓扑

```text
Browser (127.0.0.1:8080)
  -> Nginx frontend
       -> /api/* and /health -> FastAPI backend
            -> MongoDB named volume: mongo_data
            -> DeepSeek API
            -> LangSmith (optional tracing)
```

Compose 服务为 `mongo`、`backend` 和 `frontend`。Mongo 仅在 Compose 内网暴露；浏览器只访问 `frontend` 的 `127.0.0.1:8080`。

## 配置与安全边界

`.env.production` 由用户在本机创建且不提交，至少包含：

- `945_AUTH_SECRET`：随机高强度会话签名密钥。
- `DEEPSEEK_API_KEY`：真实模型调用密钥。
- `LANGSMITH_API_KEY`：仅在启用追踪时设置。
- `945_LANGSMITH_TRACING=true`：仅在启用追踪时设置。

Compose 始终以 `945_APP_ENV=production`、`945_STORAGE_BACKEND=mongo` 运行，因此业务 API 默认要求 Bearer token。Docker 命名卷 `mongo_data` 是唯一持久化边界；`docker compose down -v` 会删除数据，普通 `docker compose down` 不会。

## 启动与恢复

1. 启动 Docker Desktop，并确认 Docker daemon 可用。
2. 根据 `.env.production.example` 创建本机 `.env.production`，填入密钥。
3. 运行 `docker compose up --build -d`。
4. 访问 `http://127.0.0.1:8080`；使用注册页面创建账号并登录。
5. 需要停止时运行 `docker compose down`；恢复时再次运行 `docker compose up -d`。

若后端健康检查失败，优先读取 `docker compose logs backend`；若前端无法访问，读取 `docker compose logs frontend`；不得通过删除 `mongo_data` 作为常规故障修复。

## 验收

1. `docker compose up --build -d` 后，`http://127.0.0.1:8080/health` 返回成功。
2. 注册、登录和带 Bearer token 的业务访问成功；跨用户读取返回 `403`。
3. DeepSeek Agent 对话生成建议或草稿，草稿未确认前不写入结构化记录。
4. 确认草稿后写入训练、饮食或计划记录。
5. `docker compose down` 后再 `docker compose up -d`，同一账号仍可登录，已确认记录和 Agent runs 仍存在。
6. 启用 LangSmith 时，至少产生一条可查看的运行轨迹。

## 实施边界

实施按最小变更进行：先审计现有 Compose 配置，再仅修复阻止上述验收的配置或启动问题。所有涉及 Mongo 写入、认证和草稿确认的修改需要完整后端测试、前端构建及至少一条对应端到端用例。
