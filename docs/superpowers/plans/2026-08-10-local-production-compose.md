# 本机 Docker Compose 稳定运行 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 945 在 Windows 本机通过 Docker Compose 以生产配置稳定运行，且重启后 Mongo 数据保留。

**Architecture:** 复用现有 `mongo`、`backend` 和 `frontend` Compose 服务及 Nginx 反向代理。仅补齐生产环境模板、运行文档和静态回归测试；随后通过真实 Docker 容器验证注册登录、Agent 草稿确认、健康检查与 Mongo 命名卷持久化。

**Tech Stack:** Docker Compose、MongoDB 8、FastAPI、Nginx、React/Vite、pytest、Playwright。

## Global Constraints

- 不修改前端 UI、视觉、样式、页面排版、路由、Prompt、RAG 或 Agent 工具定义。
- `.env.production` 只能由用户本机创建，必须保持 Git 忽略，绝不写入真实 Key。
- 生产运行固定 `945_STORAGE_BACKEND=mongo`、`945_APP_ENV=production` 与 `945_AUTH_REQUIRED=true`。
- 所有 Mongo、认证、Agent 草稿确认相关变更完成时运行完整后端测试、前端构建和一条真实 Compose 端到端验收。

---

### Task 1: 锁定生产环境模板契约

**Files:**
- Create: `backend/tests/test_deployment_config.py`
- Modify: `.env.production.example`

**Interfaces:**
- Consumes: 根目录 `.env.production.example` 的 `KEY=value` 环境变量文本。
- Produces: 可重复执行的 pytest 约束，确保生产模板声明模型、认证与可选追踪配置。

- [ ] **Step 1: 写入失败测试**

```python
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def read_env_template() -> dict[str, str]:
    return {
        key: value
        for line in (ROOT / ".env.production.example").read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#")
        for key, value in [line.split("=", 1)]
    }


def test_production_template_declares_real_agent_runtime_configuration():
    env = read_env_template()

    assert env["945_LLM_PROVIDER"] == "deepseek"
    assert env["DEEPSEEK_API_KEY"] == "replace-with-your-deepseek-key"
    assert env["945_LANGSMITH_TRACING"] == "false"
    assert env["LANGSMITH_API_KEY"] == ""
    assert env["945_AUTH_SECRET"] == "replace-with-a-long-random-secret"


def test_compose_keeps_the_local_production_service_contract():
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert "mongo_data:/data/db" in compose
    assert "945_STORAGE_BACKEND: mongo" in compose
    assert "945_APP_ENV: production" in compose
    assert '945_AUTH_REQUIRED: "true"' in compose
    assert '"8080:80"' in compose
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest backend/tests/test_deployment_config.py -q`

Expected: FAIL，缺少 `945_LLM_PROVIDER`、`DEEPSEEK_API_KEY`、`945_LANGSMITH_TRACING` 或 `LANGSMITH_API_KEY`。

- [ ] **Step 3: 补齐最小环境模板**

将 `.env.production.example` 更新为：

```dotenv
# Copy to .env.production. Never commit the copied file or real keys.
945_AUTH_SECRET=replace-with-a-long-random-secret
945_AUTH_TOKEN_TTL_SECONDS=604800
945_AUTH_LOGIN_MAX_ATTEMPTS=5
945_AUTH_LOGIN_WINDOW_SECONDS=900
945_MONGODB_DATABASE=945
945_LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=replace-with-your-deepseek-key
945_LANGSMITH_TRACING=false
LANGSMITH_API_KEY=
LANGSMITH_PROJECT=945
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python -m pytest backend/tests/test_deployment_config.py -q`

Expected: PASS。

- [ ] **Step 5: 提交模板契约**

```powershell
git add .env.production.example backend/tests/test_deployment_config.py
git commit -m "feat: define local production runtime config"
```

### Task 2: 明确本机 Compose 操作手册

**Files:**
- Modify: `README.md`
- Modify: `backend/README.md`

**Interfaces:**
- Consumes: `.env.production.example` 和现有 `docker-compose.yml` 的服务名、端口、健康检查与命名卷。
- Produces: 统一的 Windows 本机启动、停止、日志、重启与数据保留说明。

- [ ] **Step 1: 记录当前文档中的运行限制**

Run: `rg -n "Docker|docker compose|mongo_data|Docker CLI" README.md backend/README.md`

Expected: 两份文档均说明 `http://127.0.0.1:8080`、`mongo_data` 或 Docker Compose；`backend/README.md` 含有过时的“未执行真实容器启动验证”说明。

- [ ] **Step 2: 更新根 README 的本机运行段落**

将“本地生产化容器运行”段落写为以下步骤：

```text
1. 启动 Docker Desktop。
2. 复制 .env.production.example 为 .env.production，并替换 945_AUTH_SECRET 和 DEEPSEEK_API_KEY；仅在需要追踪时填写 LANGSMITH_API_KEY 并设 945_LANGSMITH_TRACING=true。
3. 执行 docker compose up --build -d。
4. 访问 http://127.0.0.1:8080；停止使用 docker compose down，数据保留在 mongo_data。
```

明确 `docker compose down -v` 会删除本机 Mongo 数据，普通 `docker compose down` 不会。

- [ ] **Step 3: 更新后端 README 的 Docker 段落**

删除“当前机器没有安装 Docker CLI，尚未执行真实容器启动验证”的静态结论，替换为操作与排障命令：

```powershell
docker compose ps
docker compose logs backend
docker compose logs frontend
docker compose down
```

说明 `/health` 通过 Nginx 暴露在 `http://127.0.0.1:8080/health`，且生产模式必须经登录取得 Bearer token。

- [ ] **Step 4: 验证文档与模板一致**

Run: `python -m pytest backend/tests/test_deployment_config.py -q`

Expected: PASS，文档中的变量名与模板一致，不出现真实 Key。

- [ ] **Step 5: 提交运行文档**

```powershell
git add README.md backend/README.md
git commit -m "docs: explain local production compose workflow"
```

### Task 3: 验证真实容器启动与持久化

**Files:**
- Create locally only: `.env.production`（Git 忽略，不暂存）
- No repository file changes required.

**Interfaces:**
- Consumes: Docker Desktop daemon、`.env.production`、`docker-compose.yml`。
- Produces: 运行中的本机服务、Mongo 命名卷与可复查的手工验收结果。

- [ ] **Step 1: 创建本机环境文件**

Run: `Copy-Item .env.production.example .env.production`

然后仅在 `.env.production` 填入：随机 `945_AUTH_SECRET`、真实 `DEEPSEEK_API_KEY`；如需追踪，填入 `LANGSMITH_API_KEY` 并将 `945_LANGSMITH_TRACING=true`。不得将该文件加入 Git。

- [ ] **Step 2: 验证 Compose 服务声明**

Run: `docker compose config --services`

Expected: 成功输出 `mongo`、`backend`、`frontend` 三个服务。生产环境变量与端口映射由 Task 1 的静态 pytest 验证；不要运行或粘贴会展开真实 Key 的 `docker compose config` 完整输出。

- [ ] **Step 3: 启动容器并检查健康状态**

Run: `docker compose up --build -d; docker compose ps; Invoke-WebRequest http://127.0.0.1:8080/health -UseBasicParsing`

Expected: 三个服务为 running 或 healthy；`/health` 返回 HTTP 200。

- [ ] **Step 4: 完成真实业务验收**

在 `http://127.0.0.1:8080` 注册两个账号。使用第一个账号完成一次 DeepSeek Agent 对话并确认一个草稿；使用第二个账号访问第一个账号的数据。

Expected: 第一个账号在确认前没有新增结构化记录，确认后出现记录与 Agent run；第二个账号请求返回 `403` 或页面拒绝访问。

- [ ] **Step 5: 验证重启持久化**

Run: `docker compose down; docker compose up -d; docker compose ps`

Expected: 不使用 `-v`；服务恢复 healthy。重新登录第一个账号后，已确认记录和 Agent run 仍存在。

- [ ] **Step 6: 运行完整回归并提交任何必要的配置修复**

Run: `python -m pytest backend/tests -q; npm run build; git diff --check`

Expected: 后端测试、构建和 Git 检查均通过。若 Task 3 仅产生本机 `.env.production` 与 Docker 数据，不创建 Git 提交；若发现并修复 Compose 配置问题，单独暂存相关配置文件并以 `fix: harden local compose runtime` 提交。

## Plan Self-Review

- Spec coverage: Task 1 覆盖生产配置与密钥边界；Task 2 覆盖操作与故障恢复说明；Task 3 覆盖启动、认证、Agent 草稿、持久化与 LangSmith 可选轨迹。
- Scope: 不含公网部署、前端视觉调整、Agent 功能扩展或 Docker 以外的服务编排。
- Ambiguity: 真实 Key 只在用户本机 `.env.production` 中填写；验收不要求将 Key 或运行产物提交。
