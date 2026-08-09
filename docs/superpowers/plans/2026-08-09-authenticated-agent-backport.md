# 认证用户与 Agent 后端定向回迁 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** 在不改动前端的前提下，让 Mongo 注册用户通过 Bearer 会话安全使用 945 的全部业务 API 和 Agent。

**Architecture:** 从当前 master 的后端结构定向补齐认证域模型、Mongo 凭据存储、会话服务和统一路由授权函数。所有业务路由复用 authorize_user 边界；Agent 通过仓储用户存在性校验接纳 Mongo 注册用户，并且仍只返回确认草稿。

**Tech Stack:** FastAPI、Pydantic、MongoRepository、pytest、LangGraph MemorySaver（仅测试替身）。

## Global Constraints

- 只修改 backend/、docs/ 和后端测试；禁止修改 src/、样式、图标或前端交互。
- 不修改 DeepSeek、Prompt、RAG、Agent 工具定义或模型调用策略。
- demo 模式仅保留 demo-user-945；注册必须返回 503 STORAGE_CONFIG_ERROR。
- Agent 结构化记录请求只返回 RecordDraft，不得自动写入训练、饮食或计划数据。
- 在隔离分支 codex/auth-user-scope-backport 实施；不得操作主工作区未提交改动。

---

### Task 1: Mongo 用户凭据与测试夹具

**Files:**
- Modify: backend/app/models/domain.py
- Modify: backend/app/services/repository_store.py
- Modify: backend/tests/conftest.py
- Modify: backend/tests/test_mongo_repository.py
- Create: backend/tests/test_auth_api.py

**Interfaces:**
- Produces: AuthCredential、RegisterInput、LoginInput、PasswordChangeInput 和 AuthSession。
- Produces: RepositoryBackedStore.get_user(user_id)、save_registered_user(user, credential)、get_credential(email) 和 save_credential(credential)。
- Produces: mongo_store fixture，向 demo_store 注入 FakeDatabase 支持的 repository-backed store。

- [ ] **Step 1: 写入 Mongo 注册持久化的失败测试**

~~~python
def test_mongo_store_persists_registered_user_and_credential(mongo_store):
    user = User(user_id="user-test", display_name="Test", locale="zh-CN", unit_system="metric", created_at="2026-08-09T00:00:00Z", updated_at="2026-08-09T00:00:00Z")
    credential = AuthCredential(email="test@example.com", user_id=user.user_id, password_hash="hash", password_salt="salt", created_at=user.created_at)
    mongo_store.save_registered_user(user, credential)

    assert mongo_store.get_user(user.user_id) == user
    assert mongo_store.get_credential("test@example.com") == credential
~~~

- [ ] **Step 2: 运行测试确认失败**

Run: python -m pytest backend/tests/test_mongo_repository.py::test_mongo_store_persists_registered_user_and_credential -q

Expected: FAIL，缺少认证域模型或 repository-backed 存储方法。

- [ ] **Step 3: 实现最小的认证域模型和 Mongo 存储方法**

~~~python
class AuthCredential(ApiModel):
    email: str
    user_id: str
    password_hash: str
    password_salt: str
    created_at: str
    session_version: int = 1

def save_registered_user(self, user: User, credential: AuthCredential) -> None:
    self.repository.upsert_model("users", user, id_field="user_id")
    self.repository.upsert_model("auth_credentials", credential, id_field="email")
~~~

mongo_store fixture 必须设置 945_STORAGE_BACKEND=mongo、清理 settings cache，并在结束时移除 repository override。

- [ ] **Step 4: 运行认证存储与既有 Mongo 测试**

Run: python -m pytest backend/tests/test_mongo_repository.py backend/tests/test_repository_backed_store.py -q

Expected: PASS。

- [ ] **Step 5: 提交任务**

~~~powershell
git add backend/app/models/domain.py backend/app/services/repository_store.py backend/tests/conftest.py backend/tests/test_mongo_repository.py backend/tests/test_auth_api.py
git commit -m "feat: add mongo auth storage"
~~~

### Task 2: 会话服务与认证路由

**Files:**
- Modify: backend/app/core/config.py
- Modify: backend/app/main.py
- Create: backend/app/services/auth_service.py
- Create: backend/app/api/routes_auth.py
- Modify: backend/tests/test_auth_api.py

**Interfaces:**
- Consumes: Task 1 的 AuthCredential 与 repository-backed 存储方法。
- Produces: register(input_data)、login(input_data)、get_session(token)、change_password(user_id, input_data) 和 revoke_sessions(user_id)。
- Produces: /api/auth/register、/login、/me、/change-password、/logout。

- [ ] **Step 1: 写入注册模式限制和会话生命周期的失败测试**

~~~python
def test_registration_requires_mongo_storage():
    response = client.post("/api/auth/register", json={"display_name": "User", "email": "user@example.com", "password": "secure-pass-945"})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "STORAGE_CONFIG_ERROR"

def test_mongo_registration_login_and_logout(mongo_store):
    session = client.post("/api/auth/register", json={"display_name": "User", "email": "user@example.com", "password": "secure-pass-945"}).json()["data"]
    headers = {"Authorization": f"Bearer {session['access_token']}"}
    assert client.get("/api/auth/me", headers=headers).status_code == 200
    assert client.post("/api/auth/logout", headers=headers).status_code == 200
    assert client.get("/api/auth/me", headers=headers).status_code == 401

def register_session(email: str) -> dict:
    response = client.post("/api/auth/register", json={"display_name": email.split("@")[0], "email": email, "password": "secure-pass-945"})
    assert response.status_code == 200
    return response.json()["data"]
~~~

- [ ] **Step 2: 运行认证测试确认失败**

Run: python -m pytest backend/tests/test_auth_api.py -q

Expected: FAIL，认证路由尚未注册。

- [ ] **Step 3: 实现最小会话服务与路由**

~~~python
@router.post("/register")
def register_user(input_data: RegisterInput) -> object:
    if get_settings().storage_backend != "mongo":
        return JSONResponse(status_code=503, content=error("STORAGE_CONFIG_ERROR", "User registration requires MongoDB storage."))
    session = register(input_data)
    if session is None:
        return JSONResponse(status_code=409, content=error("REGISTRATION_FAILED", "Email already exists or password is too short."))
    return ok(session.model_dump())
~~~

会话 token 使用 HMAC 签名，payload 包含用户 ID、会话版本与过期时间；密码只以 PBKDF2-HMAC-SHA256 加盐哈希保存。main.py 必须注册 auth router。

- [ ] **Step 4: 运行认证回归**

Run: python -m pytest backend/tests/test_auth_api.py -q

Expected: PASS，覆盖注册、登录、会话读取、改密、退出和无效凭据。

- [ ] **Step 5: 提交任务**

~~~powershell
git add backend/app/core/config.py backend/app/main.py backend/app/services/auth_service.py backend/app/api/routes_auth.py backend/tests/test_auth_api.py
git commit -m "feat: add mongo-backed auth sessions"
~~~

### Task 3: 全业务 API 的用户授权边界

**Files:**
- Create: backend/app/api/auth.py
- Modify: backend/app/api/routes_advice.py
- Modify: backend/app/api/routes_agent.py
- Modify: backend/app/api/routes_body_metrics.py
- Modify: backend/app/api/routes_daily_checkins.py
- Modify: backend/app/api/routes_meal_logs.py
- Modify: backend/app/api/routes_plans.py
- Modify: backend/app/api/routes_profile.py
- Modify: backend/app/api/routes_settings.py
- Modify: backend/app/api/routes_workout_logs.py
- Modify: backend/app/services/repository_store.py
- Modify: backend/tests/test_auth_api.py

**Interfaces:**
- Consumes: Task 2 的 get_session(token)。
- Produces: authorize_user(user_id, authorization) -> JSONResponse | None。
- Produces: 每个带 user_id 的业务路由在读写前调用授权函数。

- [ ] **Step 1: 写入跨用户业务访问的失败测试**

~~~python
def test_authenticated_user_cannot_read_or_write_another_users_data(mongo_store):
    alice = register_session("alice@example.com")
    bob = register_session("bob@example.com")
    alice_headers = {"Authorization": f"Bearer {alice['access_token']}"}
    bob_headers = {"Authorization": f"Bearer {bob['access_token']}"}

    assert client.get(f"/api/workout-logs?user_id={alice['user']['user_id']}", headers=bob_headers).status_code == 403
    profile = {"user_id": alice["user"]["user_id"], "display_name": "Alice", "age": 30, "height_cm": 176, "weight_kg": 74.8, "goal": "maintenance", "experience_level": "intermediate", "training_days_per_week": 3, "training_duration_minutes": 45, "equipment": ["gym"], "dietary_preferences": ["high_protein"], "allergies": [], "constraints": [], "locale": "zh-CN", "unit_system": "metric"}
    assert client.post("/api/profile", headers=bob_headers, json=profile).status_code == 403
~~~

- [ ] **Step 2: 运行跨用户测试确认失败**

Run: python -m pytest backend/tests/test_auth_api.py::test_authenticated_user_cannot_read_or_write_another_users_data -q

Expected: FAIL，当前业务路由未校验 token 所属用户。

- [ ] **Step 3: 实现统一授权函数并接入所有业务路由**

~~~python
def authorize_user(user_id: str, authorization: str | None = Header(default=None)) -> JSONResponse | None:
    if authorization is None:
        return JSONResponse(status_code=401, content=error("UNAUTHORIZED", "A valid session is required.")) if get_settings().auth_required else None
    if not authorization.startswith("Bearer "):
        return JSONResponse(status_code=401, content=error("UNAUTHORIZED", "Bearer token is required."))
    user = get_session(authorization.removeprefix("Bearer "))
    if user is None:
        return JSONResponse(status_code=401, content=error("UNAUTHORIZED", "A valid session is required."))
    if user.user_id != user_id:
        return JSONResponse(status_code=403, content=error("FORBIDDEN", "The session cannot access another user's data."))
    return None
~~~

每个路由只加入 Header(default=None) 和 authorize_user 调用；不得同时调整业务响应、字段或前端契约。RepositoryBackedStore 的 demo-only 判断改为 Mongo 中用户是否存在，使已授权的注册用户能访问自己的资料、日志、计划、建议、打卡和 Agent 数据。

- [ ] **Step 4: 运行所有业务 API 回归**

Run: python -m pytest backend/tests/test_auth_api.py backend/tests/test_demo_api.py backend/tests/test_plans_api.py backend/tests/test_profile_settings_advice_api.py backend/tests/test_body_checkins_api.py backend/tests/test_meal_logs_api.py backend/tests/test_workout_logs_api.py -q

Expected: PASS。

- [ ] **Step 5: 提交任务**

~~~powershell
git add backend/app/api/auth.py backend/app/api/routes_advice.py backend/app/api/routes_agent.py backend/app/api/routes_body_metrics.py backend/app/api/routes_daily_checkins.py backend/app/api/routes_meal_logs.py backend/app/api/routes_plans.py backend/app/api/routes_profile.py backend/app/api/routes_settings.py backend/app/api/routes_workout_logs.py backend/app/services/repository_store.py backend/tests/test_auth_api.py
git commit -m "feat: isolate business APIs by session user"
~~~

### Task 4: Mongo 注册用户的 Agent 使用与草稿边界

**Files:**
- Modify: backend/app/services/demo_store.py
- Modify: backend/app/services/agent_service.py
- Modify: backend/tests/conftest.py
- Modify: backend/tests/test_agent_api.py
- Modify: backend/tests/test_mongo_storage_mode.py

**Interfaces:**
- Produces: user_exists(user_id) -> bool，demo 模式只承认 demo-user-945，Mongo 模式通过 repository 查找用户。
- Produces: 已注册用户的 Agent 消息和运行记录按用户持久化并由 Task 3 的路由授权保护。

- [ ] **Step 1: 写入注册用户 Agent 隔离与无自动写入的失败测试**

~~~python
def test_registered_agent_users_are_isolated_and_drafts_do_not_write(mongo_store):
    alice = register_session("alice-agent@example.com")
    bob = register_session("bob-agent@example.com")
    alice_headers = {"Authorization": f"Bearer {alice['access_token']}"}
    bob_headers = {"Authorization": f"Bearer {bob['access_token']}"}

    response = client.post("/api/agent/chat", headers=alice_headers, json={"user_id": alice["user"]["user_id"], "locale": "zh-CN", "message": "今天深蹲做了4组，每组8次，80kg，帮我记录"})
    assert response.status_code == 200
    assert response.json()["data"]["record_draft"]["requires_confirmation"] is True
    assert client.get(f"/api/agent/messages?user_id={alice['user']['user_id']}", headers=bob_headers).status_code == 403
    assert client.get(f"/api/workout-logs?user_id={alice['user']['user_id']}", headers=alice_headers).json()["data"] == []
~~~

- [ ] **Step 2: 运行 Agent 隔离测试确认失败**

Run: python -m pytest backend/tests/test_agent_api.py::test_registered_agent_users_are_isolated_and_drafts_do_not_write -q

Expected: FAIL，注册用户被当作未知 Agent 用户或测试尝试连接真实 Mongo checkpoint。

- [ ] **Step 3: 实现用户存在性校验和测试内存 checkpoint**

~~~python
def user_exists(user_id: str) -> bool:
    store = _active_repository_store()
    return store.get_user(user_id) is not None if store else user_id == DEMO_USER_ID
~~~

create_agent_reply() 用 user_exists() 取代 demo-only 校验。mongo_store fixture 在测试中清除 get_agent_graph 缓存，并将 graph module 的 get_agent_checkpointer 替换为 MemorySaver()；不得修改生产 checkpoint.py。

- [ ] **Step 4: 运行 Agent 与 Mongo 回归**

Run: python -m pytest backend/tests/test_agent_api.py backend/tests/test_agent_service.py backend/tests/test_mongo_storage_mode.py -q

Expected: PASS，且没有真实 Mongo 连接尝试。

- [ ] **Step 5: 提交任务**

~~~powershell
git add backend/app/services/demo_store.py backend/app/services/agent_service.py backend/tests/conftest.py backend/tests/test_agent_api.py backend/tests/test_mongo_storage_mode.py
git commit -m "feat: support registered mongo users in agent"
~~~

### Task 5: 文档与严格验收

**Files:**
- Modify: backend/README.md

**Interfaces:**
- Documents: Mongo 注册、环境变量、demo 限制、认证隔离和 Agent 草稿确认边界。

- [ ] **Step 1: 补充后端运行说明**

写入以下 Mongo 启动配置：

~~~powershell
$env:945_STORAGE_BACKEND="mongo"
$env:945_MONGODB_URI="mongodb://127.0.0.1:27017"
$env:945_MONGODB_DATABASE="945"
python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
~~~

明确 demo-user-945 是 demo 模式唯一用户，demo 注册返回 503 STORAGE_CONFIG_ERROR，Agent 不会自动写入结构化记录。

- [ ] **Step 2: 运行严格验证**

Run: python -m pytest backend/tests -q

Expected: PASS。

Run: npm run build

Expected: PASS。

Run: git diff --check

Expected: 无输出且退出码为 0。

- [ ] **Step 3: 提交任务**

~~~powershell
git add backend/README.md
git commit -m "docs: explain mongo-backed agent users"
~~~
