# 单设备 Refresh Token 会话 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 945 的长期 localStorage Bearer token 升级为短期 access token、HttpOnly refresh Cookie 和可单独撤销的设备会话。

**Architecture:** Mongo `auth_device_sessions` 保存每台设备的 refresh token HMAC 摘要与撤销状态。access token 含 `sid`，每次受保护请求同时验证用户的 session version 和设备会话。前端只在内存保留 access token，启动和单次 401 时通过 refresh Cookie 恢复或轮换。

**Tech Stack:** FastAPI、Pydantic、MongoDB、Python 标准库 HMAC、React 19、TypeScript、Playwright、Pytest。

**Spec:** `docs/superpowers/specs/2026-08-29-auth-device-sessions-design.md`

## Global Constraints

- 不改变颜色、字体、图标、导航外观、玻璃效果、组件视觉样式或整体设计语言。
- 不做邮箱验证、密码重置、Redis、第三方登录或 Agent 功能。
- refresh token、密码、Authorization header 不写入日志、错误响应、测试快照或前端状态。
- mock 模式不调用 refresh endpoint，保持当前 demo 行为。
- 每个任务先写失败测试，再实现最小代码、运行定向测试并提交。

---

## 文件结构

- `backend/app/models/domain.py`：设备会话、摘要和 auth response 模型。
- `backend/app/core/config.py`：15 分钟 access、30 天 refresh 配置。
- `backend/app/services/repository_store.py`：Mongo 会话读写与原子轮换。
- `backend/app/services/auth_service.py`：token 签发、刷新、撤销和验证。
- `backend/app/api/routes_auth.py`、`backend/app/api/auth.py`：Cookie 和 HTTP 鉴权。
- `src/services/authSession.ts`、`src/services/httpApi.ts`、`src/App.tsx`：内存会话、恢复和单次重试。
- `src/pages/SettingsPage.tsx`：已登录设备内容。
- `backend/tests/test_auth_service.py`、`backend/tests/test_auth_api.py`、`tests/auth-session.spec.ts`：后端与浏览器验收。

## Task 1: 设备会话数据模型和 Mongo 操作

**Files:**
- Modify: `backend/app/models/domain.py`
- Modify: `backend/app/core/config.py`
- Modify: `backend/app/services/repository_store.py`
- Test: `backend/tests/test_auth_service.py`
- Test: `backend/tests/test_mongo_repository.py`

**Interfaces:**
- Produces `AuthDeviceSession` and `AuthDeviceSessionSummary`.
- Produces `create_auth_device_session(session)`, `get_auth_device_session_by_hash(hash)`, `list_auth_device_sessions(user_id)`, `rotate_auth_device_session(session_id, old_hash, new_hash)`, `revoke_auth_device_session(user_id, session_id)` and `revoke_all_auth_device_sessions(user_id)`.

- [ ] **Step 1: Write failing tests**

```python
def test_session_summary_never_exposes_refresh_hash():
    session = make_device_session(refresh_token_hash="secret-hash")
    result = AuthDeviceSessionSummary.from_session(session, current_session_id=session.session_id)
    assert "refresh_token_hash" not in result.model_dump()
    assert result.current is True

def test_mongo_rotation_rejects_the_old_refresh_hash(mongo_store):
    created = mongo_store.create_auth_device_session(make_device_session(refresh_token_hash="old"))
    assert mongo_store.rotate_auth_device_session(created.session_id, "old", "new") is not None
    assert mongo_store.get_auth_device_session_by_hash("old") is None
    assert mongo_store.get_auth_device_session_by_hash("new").session_id == created.session_id
```

- [ ] **Step 2: Verify RED**

Run: `python -m pytest backend/tests/test_auth_service.py backend/tests/test_mongo_repository.py -q`

Expected: FAIL because the device-session model and store operations do not exist.

- [ ] **Step 3: Implement minimal models and persistence**

```python
class AuthDeviceSession(ApiModel):
    session_id: str
    user_id: str
    refresh_token_hash: str
    device_name: str
    created_at: str
    last_used_at: str
    expires_at: str
    revoked_at: str | None = None
```

Add `945_AUTH_ACCESS_TOKEN_TTL_SECONDS=900` and `945_AUTH_REFRESH_TOKEN_TTL_SECONDS=2592000` settings. Add the `auth_device_sessions` collection and indexes for `session_id`, `refresh_token_hash`, and `user_id`. Rotation must compare the old hash and replace it atomically; revoked sessions must not rotate.

- [ ] **Step 4: Verify GREEN**

Run: `python -m pytest backend/tests/test_auth_service.py backend/tests/test_mongo_repository.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/models/domain.py backend/app/core/config.py backend/app/services/repository_store.py backend/tests/test_auth_service.py backend/tests/test_mongo_repository.py
git commit -m "feat: add device session storage"
```

## Task 2: Access token、refresh token 与立即撤销

**Files:**
- Modify: `backend/app/services/auth_service.py`
- Modify: `backend/app/services/demo_store.py`
- Test: `backend/tests/test_auth_service.py`

**Interfaces:**
- Consumes Task 1 store operations.
- Produces `create_authenticated_session()`, `refresh_authenticated_session(raw_token)`, `get_authenticated_session(access_token)`, `revoke_current_device_session()` and `revoke_all_device_sessions()`.

- [ ] **Step 1: Write failing lifecycle tests**

```python
def test_refresh_rotates_and_old_refresh_token_cannot_be_reused():
    _, first_refresh = register_with_refresh(make_register_input())
    _, second_refresh = refresh_authenticated_session(first_refresh)
    assert first_refresh != second_refresh
    assert refresh_authenticated_session(first_refresh) is None

def test_revoked_device_access_token_is_immediately_invalid():
    session, _ = register_with_refresh(make_register_input())
    assert get_authenticated_session(session.access_token) is not None
    revoke_current_device_session(session.user.user_id, session.session_id)
    assert get_authenticated_session(session.access_token) is None
```

- [ ] **Step 2: Verify RED**

Run: `python -m pytest backend/tests/test_auth_service.py -q`

Expected: FAIL because existing HMAC payload has no `sid` and no refresh lifecycle.

- [ ] **Step 3: Implement token lifecycle**

```python
def _refresh_token_hash(raw_token: str) -> str:
    secret = get_settings().auth_secret.get_secret_value().encode()
    return hmac.new(secret, raw_token.encode(), hashlib.sha256).hexdigest()

def _access_token(user_id: str, session_version: int, session_id: str) -> str:
    return _sign_payload({"sub": user_id, "ver": session_version, "sid": session_id,
        "exp": int((datetime.now(UTC) + timedelta(seconds=get_settings().auth_access_token_ttl_seconds)).timestamp())})
```

Generate refresh values with `secrets.token_urlsafe(48)`. Every access validation must load the `sid` session and reject it when missing, revoked or expired. Refresh rotates the stored hash before issuing a new access token. Keep matching in-memory session behavior for demo tests.

- [ ] **Step 4: Verify GREEN**

Run: `python -m pytest backend/tests/test_auth_service.py backend/tests/test_auth_api.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/services/auth_service.py backend/app/services/demo_store.py backend/tests/test_auth_service.py backend/tests/test_auth_api.py
git commit -m "feat: rotate refresh tokens per device"
```

## Task 3: Cookie 和设备会话 HTTP 合约

**Files:**
- Modify: `backend/app/api/routes_auth.py`
- Modify: `backend/app/api/auth.py`
- Modify: `backend/app/models/domain.py`
- Test: `backend/tests/test_auth_api.py`

**Interfaces:**
- Consumes Task 2 lifecycle helpers.
- Produces `POST /api/auth/refresh`, `GET /api/auth/sessions`, `DELETE /api/auth/sessions/{session_id}`, `POST /api/auth/logout-all` and current-device `POST /api/auth/logout`.

- [ ] **Step 1: Write failing endpoint tests**

```python
def test_login_sets_http_only_cookie_and_refresh_rotates_cookie():
    login = client.post("/api/auth/login", json=valid_login())
    assert "httponly" in login.headers["set-cookie"].lower()
    old_cookie = login.cookies.get("945_refresh_token")
    refreshed = client.post("/api/auth/refresh")
    assert refreshed.status_code == 200
    assert refreshed.cookies.get("945_refresh_token") != old_cookie

def test_foreign_device_revoke_returns_404(authenticated_client):
    foreign_session_id = create_session_for_other_user().session_id
    assert authenticated_client.delete(f"/api/auth/sessions/{foreign_session_id}").status_code == 404
```

- [ ] **Step 2: Verify RED**

Run: `python -m pytest backend/tests/test_auth_api.py -q`

Expected: FAIL because no refresh Cookie or device endpoints exist.

- [ ] **Step 3: Implement routes**

```python
def _set_refresh_cookie(response: JSONResponse, raw_token: str) -> None:
    response.set_cookie("945_refresh_token", raw_token, httponly=True, samesite="lax",
        path="/api/auth", secure=get_settings().app_env == "production",
        max_age=get_settings().auth_refresh_token_ttl_seconds)
```

Read Cookie only in `/refresh`. Clear it with the same path for invalid refresh, logout, logout-all and password change. `/logout` revokes the current `sid`; `/logout-all` increments `session_version` and revokes every device session. Preserve `/me` response shape.

- [ ] **Step 4: Verify GREEN**

Run: `python -m pytest backend/tests/test_auth_api.py -q`

Expected: PASS for cookie flags, rotation, per-device revoke, cross-user isolation, logout-all and password-change invalidation.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/api/routes_auth.py backend/app/api/auth.py backend/app/models/domain.py backend/tests/test_auth_api.py
git commit -m "feat: expose device session auth APIs"
```

## Task 4: 前端内存会话和页面刷新恢复

**Files:**
- Modify: `src/services/authSession.ts`
- Modify: `src/App.tsx`
- Test: `tests/auth-session.spec.ts`

**Interfaces:**
- Consumes `POST /api/auth/refresh`.
- Produces in-memory `getAccessToken()`, `saveSession()`, `clearSession()` and `authApi.refresh()`.

- [ ] **Step 1: Write failing browser test**

```typescript
test("restores a signed-in HTTP session after page reload", async ({ page }) => {
  await registerThroughAuthPage(page);
  await page.reload();
  await expect(page.getByRole("heading", { name: "早上好，Alex。" })).toBeVisible();
  expect(await page.evaluate(() => localStorage.getItem("945.auth.token"))).toBeNull();
});
```

- [ ] **Step 2: Verify RED**

Run: `npx playwright test --config=playwright.http.config.ts tests/auth-session.spec.ts`

Expected: FAIL because the current client restores a long-lived localStorage token and never calls refresh.

- [ ] **Step 3: Implement memory-only session state**

```typescript
let accessToken: string | null = null;
let currentUserId: string | null = null;

export function saveSession(session: AuthSession) {
  accessToken = session.access_token;
  currentUserId = session.user.user_id;
}
```

Use `credentials: "include"` for auth requests. During HTTP-mode startup, `App` waits for `authApi.refresh()`; success saves the access token, failure shows the existing login page. Do not alter mock-mode startup.

- [ ] **Step 4: Verify GREEN**

Run: `npx playwright test --config=playwright.http.config.ts tests/auth-session.spec.ts; npm run build`

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add src/services/authSession.ts src/App.tsx tests/auth-session.spec.ts
git commit -m "feat: restore sessions from refresh cookies"
```

## Task 5: 单次 401 refresh 和原请求重试

**Files:**
- Modify: `src/services/httpApi.ts`
- Modify: `src/services/authSession.ts`
- Test: `tests/auth-session.spec.ts`

**Interfaces:**
- Consumes `authApi.refresh()` from Task 4.
- Produces protected-request retry behavior with exactly one refresh attempt.

- [ ] **Step 1: Write failing browser tests**

```typescript
test("refreshes once then retries one protected request", async ({ page }) => {
  await registerThroughAuthPage(page);
  await expireNextTodayRequest(page);
  await page.goto("/today");
  await expect(page.getByRole("heading", { name: "早上好，Alex。" })).toBeVisible();
});

test("returns to login after a second unauthorized response", async ({ page }) => {
  await registerThroughAuthPage(page);
  await makeRefreshAndRetryReturnUnauthorized(page);
  await page.goto("/today");
  await expect(page.getByRole("heading", { name: "登录 945" })).toBeVisible();
});
```

- [ ] **Step 2: Verify RED**

Run: `npx playwright test --config=playwright.http.config.ts tests/auth-session.spec.ts -g "refreshes once|second unauthorized"`

Expected: FAIL because `httpApi.request()` returns the first 401 unchanged.

- [ ] **Step 3: Implement one retry**

```typescript
if (AUTH_ENABLED && response.status === 401 && !refreshed && await refreshSession()) {
  return request<T>(path, init, true);
}
if (AUTH_ENABLED && response.status === 401) clearSession();
```

Only protected HTTP-mode requests use this behavior. Never refresh auth endpoints, network errors, invalid JSON responses or mock requests.

- [ ] **Step 4: Verify GREEN**

Run: `npx playwright test --config=playwright.http.config.ts tests/auth-session.spec.ts`

Expected: PASS; refresh count is one for each original request.

- [ ] **Step 5: Commit**

```powershell
git add src/services/httpApi.ts src/services/authSession.ts tests/auth-session.spec.ts
git commit -m "feat: refresh expired access sessions once"
```

## Task 6: 设置页的设备管理

**Files:**
- Modify: `src/services/authSession.ts`
- Modify: `src/pages/SettingsPage.tsx`
- Modify: `src/App.tsx`
- Test: `tests/auth-session.spec.ts`

**Interfaces:**
- Consumes Task 3 session list, revoke and logout-all endpoints.
- Produces `authApi.sessions()`, `authApi.revokeSession()`, `authApi.logoutAll()` and settings actions.

- [ ] **Step 1: Write failing browser tests**

```typescript
test("lists sessions and revokes an other device", async ({ page }) => {
  await signInWithTwoDeviceSessions(page);
  await page.goto("/settings");
  await expect(page.getByRole("heading", { name: "已登录设备" })).toBeVisible();
  await page.getByRole("button", { name: "退出此设备" }).click();
  await expect(page.getByText("设备已退出")).toBeVisible();
});
```

- [ ] **Step 2: Verify RED**

Run: `npx playwright test --config=playwright.http.config.ts tests/auth-session.spec.ts -g "lists sessions"`

Expected: FAIL because Settings has no device list or individual revoke action.

- [ ] **Step 3: Implement without restyling**

Use existing settings section, `business-panel`, buttons and `ConfirmDialog`. Show device name, last-used time and current marker. Other sessions show `退出此设备`; use a confirmation dialog for `退出所有设备`. Existing app logout becomes current-device logout. Successful password change clears local memory because all sessions were revoked.

- [ ] **Step 4: Verify GREEN**

Run: `npx playwright test --config=playwright.http.config.ts tests/auth-session.spec.ts; npm run build`

Expected: PASS with no color, font, icon, navigation or glass-effect changes.

- [ ] **Step 5: Commit**

```powershell
git add src/services/authSession.ts src/pages/SettingsPage.tsx src/App.tsx tests/auth-session.spec.ts
git commit -m "feat: manage signed-in devices"
```

## Task 7: 文档和严格验收

**Files:**
- Modify: `backend/README.md`
- Modify: `README.md`
- Test: `backend/tests/test_auth_api.py`
- Test: `tests/auth-session.spec.ts`

- [ ] **Step 1: Add any missing global-revocation test**

```python
def test_password_change_invalidates_every_device_session():
    first, second = create_two_device_sessions_for_same_user(client)
    assert change_password(first).status_code == 200
    assert first.get("/api/auth/me").status_code == 401
    assert second.get("/api/auth/me").status_code == 401
```

- [ ] **Step 2: Verify RED or existing coverage**

Run: `python -m pytest backend/tests/test_auth_api.py -q`

Expected: PASS only after global revocation clears all device sessions.

- [ ] **Step 3: Document final configuration**

Document `945_AUTH_ACCESS_TOKEN_TTL_SECONDS=900`, `945_AUTH_REFRESH_TOKEN_TTL_SECONDS=2592000`, the production `945_AUTH_SECRET` requirement, same-origin HttpOnly Cookie behavior and all new session endpoints. Do not write a real key or cookie to docs.

- [ ] **Step 4: Run strict verification**

```powershell
python -m pytest backend/tests -q
npm run build
npm run qa:http
npm run qa:mongo
```

Expected: every command exits `0`; no output artifact includes a refresh token or password.

- [ ] **Step 5: Commit**

```powershell
git add backend/README.md README.md backend/tests/test_auth_api.py tests/auth-session.spec.ts
git commit -m "docs: document device session authentication"
```

## Plan Self-Review

- Spec coverage: Tasks 1-3 cover persisted sessions, token rotation, Cookie contracts and immediate revocation. Tasks 4-6 cover memory-only access state, startup recovery, one-retry behavior and device controls. Task 7 covers password-driven global revocation, documentation and strict verification.
- Scope: no task adds email verification, password reset, Redis, third-party login, Agent behavior or visual-system redesign.
- Type consistency: `session_id`, `refresh_token_hash`, `AuthDeviceSession`, `refreshSession()` and endpoint paths are consistent across tasks.
