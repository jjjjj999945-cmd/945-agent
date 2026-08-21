# Agent Run Mongo Lease Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 使用 Mongo 原子租约替代 Agent run 的进程内所有权判断，使多个后端 Worker 共享 Mongo 时同一任务只有一个有效执行者，并保持用户手动恢复。

**Architecture:** `AgentRun` 保存租约 owner、单调递增版本、Mongo 服务端到期时间和恢复 checkpoint。Demo store 与 `RepositoryBackedStore` 暴露同一组原子租约操作；`AgentLeaseSession` 负责当前执行的心跳和取消；LangGraph checkpoint 带租约版本并在写入前校验；Agent service 只有在带租约的终态 CAS 成功后才发布消息。

**Tech Stack:** Python 3.11、FastAPI、Pydantic、PyMongo、MongoDB、LangGraph 0.6.11、MongoDBSaver、Pytest、React 19、TypeScript、Vite、Playwright。

**Spec:** `docs/superpowers/specs/2026-08-21-agent-run-mongo-lease-design.md`

## Global Constraints

- 任务过期后只转为 `interrupted`；必须由用户点击“继续任务”，禁止后台自动接管。
- Mongo 中的 `AgentRun` 是运行所有权和终态的唯一权威。
- 所有运行期写入必须校验 `user_id + agent_run_id + lease_owner + lease_version`。
- 新 run 的 `lease_version = 1`；每次成功恢复原子加一，版本不回退、不复用。
- 默认 `945_AGENT_LEASE_TTL_SECONDS=60`、`945_AGENT_LEASE_HEARTBEAT_SECONDS=15`，且 heartbeat 不得超过 TTL 的三分之一。
- Mongo 租约到期和续租时间使用服务端 `$$NOW`；Demo 使用可替换 UTC clock。
- 恢复前后 `agent_run_id` 和 LangGraph `thread_id` 保持不变。
- 旧 Worker 失去租约后不能发布用户可见消息、终态或被新执行采用的 checkpoint。
- 模型只生成草稿；训练、饮食和计划写入仍必须经过用户确认和结构化 API。
- 不引入 Redis、Celery、消息队列、自动恢复扫描器或第三方依赖。
- 不修改颜色、字体、图标、导航、玻璃效果、组件视觉样式或整体设计语言。
- 默认不修改前端生产组件；只在公开 HTTP 契约无法兼容时做最小功能适配。
- 所有测试使用 deterministic/fake Provider；不运行 DeepSeek 或其他付费模型。
- `.venv/` 和 `output/` 不暂存、不提交。

## File Structure

- Create `backend/app/services/agent_run_lease.py`：租约 token、owner 生成、配置转换、租约丢失异常和异步心跳会话。
- Modify `backend/app/core/config.py`：TTL 与 heartbeat 配置和交叉校验。
- Modify `backend/app/models/domain.py`：AgentRun 内部租约、固定 checkpoint 和消息收口字段。
- Modify `backend/app/services/demo_store.py`：Demo 原子租约状态机及 Mongo store 委托入口。
- Modify `backend/app/repositories/mongo.py`：原子插入、`find_one_and_update` 和条件更新基础能力。
- Modify `backend/app/services/repository_store.py`：使用 Mongo 服务端时间实现 AgentRun 租约操作。
- Modify `backend/app/agents/checkpoint.py`：租约校验的 checkpointer wrapper。
- Modify `backend/app/agents/graph.py`：Graph 租约配置、节点边界校验、固定 checkpoint 恢复与结果读取。
- Modify `backend/app/services/agent_service.py`：创建、心跳、收口、过期识别、恢复竞争和消息修复。
- Modify `backend/app/api/routes_agent.py`：内部字段过滤、租约错误映射和消息修复入口。
- Create `backend/tests/test_agent_run_lease_store.py`：Demo store 租约契约测试。
- Create `backend/tests/test_agent_run_lease_mongo.py`：真实 Mongo 双 owner 原子竞争测试。
- Modify `backend/tests/test_agent_graph.py`、`backend/tests/test_agent_service.py`、`backend/tests/test_agent_api.py`、`backend/tests/test_auth_api.py`、`backend/tests/conftest.py`：分层回归测试。
- Modify `tests/http-integration.spec.ts`：公开 HTTP 状态和字段回归。
- Modify `backend/README.md`：运行配置、手动恢复和离线验收说明。

---

### Task 1: 租约模型、配置与 token

**Files:**
- Create: `backend/app/services/agent_run_lease.py`
- Modify: `backend/app/core/config.py:10-38`
- Modify: `backend/app/models/domain.py:399-422`
- Create: `backend/tests/test_agent_run_lease_store.py`
- Modify: `backend/tests/test_llm_config.py`

**Interfaces:**
- Produces: `AgentLeaseToken(user_id, agent_run_id, owner, version, expires_at)`。
- Produces: `AgentLeaseLostError`、`new_lease_owner()`、`lease_token_from_run(run)`。
- Produces: `Settings.agent_lease_ttl_seconds`、`Settings.agent_lease_heartbeat_seconds`。
- Produces: `AgentRun.lease_owner`、`lease_version`、`lease_expires_at`、`last_heartbeat_at`、`resume_checkpoint_id`、`messages_persisted`。

- [ ] **Step 1: 写模型和配置失败测试**

在 `backend/tests/test_agent_run_lease_store.py` 创建：

```python
from datetime import UTC, datetime

from backend.app.models.domain import AgentRun
from backend.app.services.agent_run_lease import lease_token_from_run


def test_agent_run_builds_an_internal_lease_token():
    expires_at = datetime(2026, 8, 21, 12, 1, tzinfo=UTC)
    run = AgentRun(
        agent_run_id="run-lease-1",
        user_id="demo-user-945",
        status="running",
        started_at="2026-08-21T12:00:00Z",
        lease_owner="worker-a:attempt-1",
        lease_version=1,
        lease_expires_at=expires_at,
    )

    token = lease_token_from_run(run)

    assert token.agent_run_id == run.agent_run_id
    assert token.owner == "worker-a:attempt-1"
    assert token.version == 1
    assert token.expires_at == expires_at
```

在 `backend/tests/test_llm_config.py` 增加：

```python
import pytest
from pydantic import ValidationError

from backend.app.core.config import Settings


def test_agent_lease_settings_require_heartbeat_at_most_one_third_of_ttl():
    with pytest.raises(ValidationError):
        Settings(
            agent_lease_ttl_seconds=30,
            agent_lease_heartbeat_seconds=11,
        )


def test_agent_lease_settings_accept_the_default_ratio():
    settings = Settings()

    assert settings.agent_lease_ttl_seconds == 60
    assert settings.agent_lease_heartbeat_seconds == 15
```

- [ ] **Step 2: 运行测试并确认 RED**

```powershell
python -m pytest backend/tests/test_agent_run_lease_store.py::test_agent_run_builds_an_internal_lease_token backend/tests/test_llm_config.py::test_agent_lease_settings_require_heartbeat_at_most_one_third_of_ttl backend/tests/test_llm_config.py::test_agent_lease_settings_accept_the_default_ratio -q
```

Expected: FAIL，因为租约模块、字段和配置尚不存在。

- [ ] **Step 3: 实现配置和 AgentRun 字段**

在 `Settings` 中增加整数配置，并使用 Pydantic `model_validator` 校验：

```python
from pydantic import BaseModel, ConfigDict, SecretStr, model_validator


class Settings(BaseModel):
    agent_lease_ttl_seconds: int = 60
    agent_lease_heartbeat_seconds: int = 15

    @model_validator(mode="after")
    def validate_agent_lease_intervals(self):
        if self.agent_lease_ttl_seconds <= 0:
            raise ValueError("Agent lease TTL must be positive.")
        if self.agent_lease_heartbeat_seconds <= 0:
            raise ValueError("Agent lease heartbeat must be positive.")
        if self.agent_lease_heartbeat_seconds * 3 > self.agent_lease_ttl_seconds:
            raise ValueError("Agent lease heartbeat must not exceed one third of TTL.")
        return self
```

`get_settings()` 必须读取：

```python
agent_lease_ttl_seconds=int(os.getenv("945_AGENT_LEASE_TTL_SECONDS", "60")),
agent_lease_heartbeat_seconds=int(
    os.getenv("945_AGENT_LEASE_HEARTBEAT_SECONDS", "15")
),
```

`AgentRun` 增加：

```python
lease_owner: str | None = None
lease_version: int = 0
lease_expires_at: datetime | None = None
last_heartbeat_at: datetime | None = None
resume_checkpoint_id: str | None = None
messages_persisted: bool = True
```

- [ ] **Step 4: 实现不可变 token 和转换函数**

`backend/app/services/agent_run_lease.py` 初始内容：

```python
from dataclasses import dataclass
from datetime import datetime
from os import getpid
from uuid import uuid4

from backend.app.models.domain import AgentRun


class AgentLeaseLostError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class AgentLeaseToken:
    user_id: str
    agent_run_id: str
    owner: str
    version: int
    expires_at: datetime


def new_lease_owner() -> str:
    return f"{getpid()}:{uuid4().hex}"


def lease_token_from_run(run: AgentRun) -> AgentLeaseToken:
    if run.lease_owner is None or run.lease_expires_at is None:
        raise ValueError("Agent run does not hold a lease.")
    return AgentLeaseToken(
        user_id=run.user_id,
        agent_run_id=run.agent_run_id,
        owner=run.lease_owner,
        version=run.lease_version,
        expires_at=run.lease_expires_at,
    )
```

- [ ] **Step 5: 验证 GREEN**

```powershell
python -m pytest backend/tests/test_agent_run_lease_store.py backend/tests/test_llm_config.py -q
```

Expected: PASS。

- [ ] **Step 6: 提交 Task 1**

```powershell
git add backend/app/core/config.py backend/app/models/domain.py backend/app/services/agent_run_lease.py backend/tests/test_agent_run_lease_store.py backend/tests/test_llm_config.py
git commit -m "feat: add agent run lease model"
```

---

### Task 2: Demo store 原子租约契约

**Files:**
- Modify: `backend/app/services/demo_store.py:20-55,254-301`
- Modify: `backend/tests/test_agent_run_lease_store.py`

**Interfaces:**
- Consumes: `AgentLeaseToken`、`lease_token_from_run()`、TTL 配置。
- Produces: `create_agent_run_with_lease(run, owner) -> AgentRun | None`。
- Produces: `acquire_agent_run_lease(user_id, run_id, owner) -> AgentRun | None`。
- Produces: `renew_agent_run_lease(token) -> AgentRun | None`。
- Produces: `agent_run_lease_is_valid(token) -> bool`。
- Produces: `interrupt_expired_agent_runs(user_id) -> int`。
- Produces: `set_agent_run_resume_checkpoint(token, checkpoint_id) -> AgentRun | None`。
- Produces: `transition_agent_run_with_lease(token, updated_run) -> AgentRun | None`。
- Produces: `mark_agent_run_messages_persisted(user_id, run_id, lease_version) -> bool`。

- [ ] **Step 1: 写 Demo 状态机失败测试**

在同一测试文件增加可替换时钟和完整竞争用例：

```python
from datetime import UTC, datetime, timedelta

from backend.app.models.domain import AgentRetryInput, AgentRun
from backend.app.services import demo_store
from backend.app.services.agent_run_lease import lease_token_from_run


def test_demo_lease_expires_then_only_one_new_owner_can_resume(monkeypatch):
    now = datetime(2026, 8, 21, 12, 0, tzinfo=UTC)
    monkeypatch.setattr(demo_store, "_agent_lease_now", lambda: now)
    run = AgentRun(
        agent_run_id="run-race",
        user_id="demo-user-945",
        status="running",
        started_at="2026-08-21T12:00:00Z",
        request_input=AgentRetryInput(message="继续任务", locale="zh-CN"),
    )

    first = demo_store.create_agent_run_with_lease(run, "worker-a")
    first_token = lease_token_from_run(first)
    assert demo_store.acquire_agent_run_lease(run.user_id, run.agent_run_id, "worker-b") is None

    now += timedelta(seconds=61)
    assert demo_store.interrupt_expired_agent_runs(run.user_id) == 1

    second = demo_store.acquire_agent_run_lease(run.user_id, run.agent_run_id, "worker-b")
    assert second is not None
    assert second.lease_version == 2
    assert demo_store.acquire_agent_run_lease(run.user_id, run.agent_run_id, "worker-c") is None

    stale_completion = first.model_copy(update={"status": "completed"})
    assert demo_store.transition_agent_run_with_lease(first_token, stale_completion) is None
```

再增加续租、终态保护和 checkpoint CAS：

```python
def test_demo_lease_renewal_and_checkpoint_require_the_current_token(monkeypatch):
    now = datetime(2026, 8, 21, 12, 0, tzinfo=UTC)
    monkeypatch.setattr(demo_store, "_agent_lease_now", lambda: now)
    created = demo_store.create_agent_run_with_lease(
        AgentRun(
            agent_run_id="run-renew",
            user_id="demo-user-945",
            status="running",
            started_at="2026-08-21T12:00:00Z",
        ),
        "worker-a",
    )
    token = lease_token_from_run(created)

    renewed = demo_store.renew_agent_run_lease(token)
    pinned = demo_store.set_agent_run_resume_checkpoint(
        lease_token_from_run(renewed),
        "checkpoint-1",
    )

    assert pinned.resume_checkpoint_id == "checkpoint-1"
    assert demo_store.agent_run_lease_is_valid(lease_token_from_run(pinned))
```

增加历史文档兼容测试：

```python
def test_legacy_runs_without_lease_fields_keep_terminal_states_and_interrupt_running():
    for status in ("completed", "failed"):
        demo_store.save_agent_run(
            AgentRun(
                agent_run_id=f"legacy-{status}",
                user_id="demo-user-945",
                status=status,
                started_at="2026-08-21T12:00:00Z",
            )
        )
    demo_store.save_agent_run(
        AgentRun(
            agent_run_id="legacy-running",
            user_id="demo-user-945",
            status="running",
            started_at="2026-08-21T12:00:00Z",
        )
    )

    assert demo_store.interrupt_expired_agent_runs("demo-user-945") == 1
    states = {run.agent_run_id: run.status for run in demo_store.list_agent_runs("demo-user-945")}
    assert states == {
        "legacy-completed": "completed",
        "legacy-failed": "failed",
        "legacy-running": "interrupted",
    }

    legacy_interrupted = AgentRun(
        agent_run_id="legacy-interrupted",
        user_id="demo-user-945",
        status="interrupted",
        started_at="2026-08-21T12:00:00Z",
    )
    demo_store.save_agent_run(legacy_interrupted)
    resumed = demo_store.acquire_agent_run_lease(
        legacy_interrupted.user_id,
        legacy_interrupted.agent_run_id,
        "worker-a",
    )
    assert resumed.lease_version == 1
```

- [ ] **Step 2: 运行测试并确认 RED**

```powershell
python -m pytest backend/tests/test_agent_run_lease_store.py -q
```

Expected: FAIL，因为 Demo store 仍只有普通 upsert。

- [ ] **Step 3: 实现锁、时钟和匹配函数**

在 `demo_store.py` 增加：

```python
from datetime import UTC, datetime, timedelta
from threading import RLock

from backend.app.services.agent_run_lease import AgentLeaseToken


_agent_run_lock = RLock()


def _agent_lease_now() -> datetime:
    return datetime.now(UTC)


def _demo_run_for_token(token: AgentLeaseToken) -> AgentRun | None:
    return next(
        (
            run
            for run in agent_runs
            if run.user_id == token.user_id
            and run.agent_run_id == token.agent_run_id
            and run.status == "running"
            and run.lease_owner == token.owner
            and run.lease_version == token.version
            and run.lease_expires_at is not None
            and run.lease_expires_at > _agent_lease_now()
        ),
        None,
    )
```

`reset_demo_store()` 在同一 `_agent_run_lock` 内清理 run 和消息，避免并发测试残留。

- [ ] **Step 4: 实现 Demo 原子操作**

每个函数先检查 `_active_repository_store()` 并委托同名方法；Demo 分支在
`_agent_run_lock` 内完成读写。创建和恢复的核心更新固定为：

```python
expires_at = _agent_lease_now() + timedelta(
    seconds=get_app_settings().agent_lease_ttl_seconds
)
leased = run.model_copy(
    update={
        "status": "running",
        "lease_owner": owner,
        "lease_version": 1,
        "last_heartbeat_at": _agent_lease_now(),
        "lease_expires_at": expires_at,
    }
)
```

恢复必须仅匹配 `interrupted`，并执行：

```python
leased = existing.model_copy(
    update={
        "status": "running",
        "lease_owner": owner,
        "lease_version": existing.lease_version + 1,
        "last_heartbeat_at": now,
        "lease_expires_at": now + timedelta(seconds=settings.agent_lease_ttl_seconds),
        "resume_count": existing.resume_count + 1,
        "completed_at": None,
        "error_code": None,
    }
)
```

`transition_agent_run_with_lease()` 只接受目标状态
`completed | failed | interrupted`，匹配成功后清除 owner/expiry，保留 version。
`mark_agent_run_messages_persisted()` 只匹配
`completed + user_id + run_id + lease_version`。

- [ ] **Step 5: 验证 GREEN**

```powershell
python -m pytest backend/tests/test_agent_run_lease_store.py backend/tests/test_agent_service.py::test_demo_store_upserts_agent_runs_and_messages_by_id -q
```

Expected: PASS。Task 5 改造 service 以前保留 `_active_agent_run_ids` 和对应 fixture
清理，保证本任务提交自身是绿色的。

- [ ] **Step 6: 提交 Task 2**

```powershell
git add backend/app/services/demo_store.py backend/tests/test_agent_run_lease_store.py
git commit -m "feat: add in-memory agent run leases"
```

---

### Task 3: Mongo 原子租约实现

**Files:**
- Modify: `backend/app/repositories/mongo.py:1-57`
- Modify: `backend/app/services/repository_store.py:334-352`
- Modify: `backend/tests/test_mongo_repository.py`
- Create: `backend/tests/test_agent_run_lease_mongo.py`

**Interfaces:**
- Consumes: Task 2 的八个 store 操作和 `AgentLeaseToken`。
- Produces: Mongo 模式下同名、同返回类型的原子实现。
- Produces: `MongoRepository.insert_model()`、`find_one_and_update_model()`、`update_one()`。

- [ ] **Step 1: 扩展 FakeCollection 并写 Mongo helper 失败测试**

`backend/tests/test_mongo_repository.py` 的 fake 记录调用参数，并增加：

```python
def test_repository_find_one_and_update_returns_the_updated_model():
    database = FakeDatabase()
    repository = MongoRepository(database)
    run = AgentRun(
        agent_run_id="run-atomic",
        user_id="demo-user-945",
        status="interrupted",
        started_at="2026-08-21T12:00:00Z",
    )
    repository.upsert_model("agent_runs", run, id_field="agent_run_id")

    updated = repository.find_one_and_update_model(
        "agent_runs",
        AgentRun,
        {"_id": "run-atomic", "status": "interrupted"},
        {"$set": {"status": "running", "lease_version": 1}},
    )

    assert updated.status == "running"
    assert updated.lease_version == 1
```

- [ ] **Step 2: 写真实 Mongo 双 owner 失败测试**

`backend/tests/test_agent_run_lease_mongo.py` 使用专用数据库：

```python
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest
from pymongo import MongoClient

from backend.app.models.domain import AgentRun
from backend.app.repositories.mongo import MongoRepository
from backend.app.services.agent_run_lease import lease_token_from_run
from backend.app.services.repository_store import RepositoryBackedStore


pytestmark = pytest.mark.skipif(
    os.getenv("945_RUN_MONGO_INTEGRATION_TESTS") != "1",
    reason="Set 945_RUN_MONGO_INTEGRATION_TESTS=1 to run Mongo lease tests.",
)


def test_two_mongo_stores_allow_only_one_resume_owner():
    client = MongoClient("mongodb://127.0.0.1:27017")
    database_name = "945_agent_lease_test"
    client.drop_database(database_name)
    first = RepositoryBackedStore(MongoRepository(client[database_name]))
    second = RepositoryBackedStore(MongoRepository(client[database_name]))
    first.seed_demo_data()
    try:
        created = first.create_agent_run_with_lease(
            AgentRun(
                agent_run_id="run-mongo-race",
                user_id="demo-user-945",
                status="running",
                started_at="2026-08-21T12:00:00Z",
            ),
            "worker-a",
        )
        client[database_name]["agent_runs"].update_one(
            {"_id": created.agent_run_id},
            {"$set": {"lease_expires_at": datetime.now(UTC) - timedelta(seconds=1)}},
        )
        assert first.interrupt_expired_agent_runs(created.user_id) == 1

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(
                executor.map(
                    lambda owner: second.acquire_agent_run_lease(
                        created.user_id,
                        created.agent_run_id,
                        owner,
                    ),
                    ["worker-b", "worker-c"],
                )
            )

        winners = [run for run in results if run is not None]
        assert len(winners) == 1
        assert winners[0].lease_version == 2
        assert first.transition_agent_run_with_lease(
            lease_token_from_run(created),
            created.model_copy(update={"status": "completed"}),
        ) is None
    finally:
        client.drop_database(database_name)
```

- [ ] **Step 3: 运行测试并确认 RED**

```powershell
python -m pytest backend/tests/test_mongo_repository.py::test_repository_find_one_and_update_returns_the_updated_model -q
$env:945_RUN_MONGO_INTEGRATION_TESTS="1"
python -m pytest backend/tests/test_agent_run_lease_mongo.py -q
Remove-Item Env:945_RUN_MONGO_INTEGRATION_TESTS
```

Expected: FAIL，因为 MongoRepository 和 RepositoryBackedStore 尚无租约方法。

- [ ] **Step 4: 实现 MongoRepository 原子基础方法**

`mongo.py` 使用 `ReturnDocument.AFTER`：

```python
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError


def find_one_and_update_model(
    self,
    collection_name: str,
    model_type: type[ModelT],
    filter_doc: dict[str, Any],
    update_doc: dict[str, Any] | list[dict[str, Any]],
    *,
    upsert: bool = False,
) -> ModelT | None:
    try:
        document = self.database[collection_name].find_one_and_update(
            filter_doc,
            update_doc,
            upsert=upsert,
            return_document=ReturnDocument.AFTER,
        )
    except DuplicateKeyError:
        return None
    return None if document is None else mongo_document_to_model(document, model_type)
```

`insert_model()` 返回 `False` 而不是覆盖重复 `_id`；
`update_one()` 返回 `matched_count == 1`。

- [ ] **Step 5: 实现 RepositoryBackedStore 租约查询和服务端时间更新**

所有有效租约查询复用同一私有 filter：

```python
def _lease_filter(token: AgentLeaseToken) -> dict[str, Any]:
    return {
        "_id": token.agent_run_id,
        "user_id": token.user_id,
        "status": "running",
        "lease_owner": token.owner,
        "lease_version": token.version,
        "$expr": {"$gt": ["$lease_expires_at", "$$NOW"]},
    }
```

续租使用 update pipeline：

```python
[
    {
        "$set": {
            "last_heartbeat_at": "$$NOW",
            "lease_expires_at": {
                "$dateAdd": {
                    "startDate": "$$NOW",
                    "unit": "second",
                    "amount": get_settings().agent_lease_ttl_seconds,
                }
            },
        }
    }
]
```

创建使用带 `_id` 唯一约束的 upsert pipeline；现有 ID 导致 duplicate key 时返回
`None`。恢复只匹配 `interrupted` 并在 pipeline 中
`lease_version = $add(ifNull(version, 0), 1)`、`resume_count + 1`。
过期收口只匹配 `running` 且 expiry 缺失、为空或 `<= $$NOW`。

- [ ] **Step 6: 验证 GREEN**

```powershell
python -m pytest backend/tests/test_mongo_repository.py -q
$env:945_RUN_MONGO_INTEGRATION_TESTS="1"
python -m pytest backend/tests/test_agent_run_lease_mongo.py -q
Remove-Item Env:945_RUN_MONGO_INTEGRATION_TESTS
```

Expected: PASS；真实 Mongo 竞争 winner 数固定为 1。

- [ ] **Step 7: 提交 Task 3**

```powershell
git add backend/app/repositories/mongo.py backend/app/services/repository_store.py backend/tests/test_mongo_repository.py backend/tests/test_agent_run_lease_mongo.py
git commit -m "feat: coordinate agent runs with Mongo leases"
```

---

### Task 4: 租约保护的 LangGraph checkpoint

**Files:**
- Modify: `backend/app/agents/checkpoint.py:1-31`
- Modify: `backend/app/agents/graph.py:100-326`
- Modify: `backend/app/services/agent_run_lease.py`
- Modify: `backend/tests/test_agent_graph.py`

**Interfaces:**
- Consumes: `AgentLeaseToken`、`agent_run_lease_is_valid()`。
- Produces: `LeaseFencedCheckpointer`，读操作委托，写操作校验租约并写 metadata。
- Produces: `get_safe_resume_checkpoint_id(run_id, before_version) -> str | None`。
- Produces: `load_completed_agent_graph_result(run_id, lease_version) -> AgentGraphResult | None`。
- Changes: `run_agent_graph(user_id, locale, message, context=None, *, conversation=None, provider_router=None, request_id=None, lease_token=None)`。
- Changes: `resume_agent_graph(request_id, *, checkpoint_id, lease_token, provider_router=None)`。

- [ ] **Step 1: 写 checkpoint fencing 失败测试**

使用 `MemorySaver` 作为 delegate：

```python
def test_fenced_checkpointer_rejects_a_stale_lease(monkeypatch):
    from langgraph.checkpoint.memory import MemorySaver
    from backend.app.agents.checkpoint import LeaseFencedCheckpointer
    from backend.app.services.agent_run_lease import AgentLeaseLostError

    monkeypatch.setattr(
        "backend.app.agents.checkpoint.agent_run_lease_is_valid",
        lambda token: False,
    )
    saver = LeaseFencedCheckpointer(MemorySaver())
    config = {
        "configurable": {
            "thread_id": "run-stale",
            "checkpoint_ns": "",
            "agent_user_id": "demo-user-945",
            "agent_run_id": "run-stale",
            "agent_lease_owner": "worker-a",
            "agent_lease_version": 1,
            "agent_lease_expires_at": "2026-08-21T12:01:00+00:00",
        }
    }
    checkpoint = {
        "v": 1,
        "id": "checkpoint-stale-1",
        "ts": "2026-08-21T12:00:00+00:00",
        "channel_values": {},
        "channel_versions": {},
        "versions_seen": {},
        "pending_sends": [],
    }

    with pytest.raises(AgentLeaseLostError):
        saver.put(config, checkpoint, {}, {})
```

增加恢复固定 checkpoint 用例：

```python
def test_resume_agent_graph_reads_the_pinned_checkpoint(monkeypatch):
    captured = {}
    result = AgentGraphResult(
        intent="ask_question",
        reply="固定检查点结果",
        record_draft=None,
        today_context=None,
        rag_chunks=[],
        provider="stub",
    )

    class StubGraph:
        def get_state(self, config):
            captured.update(config)
            return SimpleNamespace(values={"result": result}, next=())

    monkeypatch.setattr(agent_graph_module, "get_agent_graph", lambda: StubGraph())
    token = AgentLeaseToken(
        user_id="demo-user-945",
        agent_run_id="run-pinned",
        owner="worker-b",
        version=2,
        expires_at=datetime(2026, 8, 21, 12, 1, tzinfo=UTC),
    )

    restored = asyncio.run(
        agent_graph_module.resume_agent_graph(
            "run-pinned",
            checkpoint_id="checkpoint-v1-safe",
            lease_token=token,
        )
    )

    assert restored.reply == "固定检查点结果"
    assert captured["configurable"]["checkpoint_id"] == "checkpoint-v1-safe"
```

测试文件同时导入 `SimpleNamespace`、`UTC`、`datetime`、`AgentLeaseToken` 和
`AgentGraphResult`；不使用未定义的测试 helper。

- [ ] **Step 2: 运行测试并确认 RED**

```powershell
python -m pytest backend/tests/test_agent_graph.py -q
```

Expected: FAIL，因为 checkpointer wrapper 和租约 metadata 尚不存在。

- [ ] **Step 3: 实现 config 与 token 转换**

`agent_run_lease.py` 增加：

```python
def lease_config(token: AgentLeaseToken) -> dict[str, object]:
    return {
        "agent_user_id": token.user_id,
        "agent_run_id": token.agent_run_id,
        "agent_lease_owner": token.owner,
        "agent_lease_version": token.version,
        "agent_lease_expires_at": token.expires_at.isoformat(),
    }


def lease_token_from_config(config: dict) -> AgentLeaseToken | None:
    values = config.get("configurable", {})
    if "agent_lease_version" not in values:
        return None
    return AgentLeaseToken(
        user_id=str(values["agent_user_id"]),
        agent_run_id=str(values["agent_run_id"]),
        owner=str(values["agent_lease_owner"]),
        version=int(values["agent_lease_version"]),
        expires_at=datetime.fromisoformat(str(values["agent_lease_expires_at"])),
    )
```

- [ ] **Step 4: 实现 LeaseFencedCheckpointer**

Wrapper 覆盖并委托 `get_tuple/list/aget_tuple/alist`；`put/put_writes/aput/aput_writes`
先调用：

```python
def _assert_write_lease(self, config: RunnableConfig) -> AgentLeaseToken | None:
    token = lease_token_from_config(config)
    if token is not None and not agent_run_lease_is_valid(token):
        raise AgentLeaseLostError(token.agent_run_id)
    return token
```

`put()` 将安全 metadata 合并后再委托：

```python
token = self._assert_write_lease(config)
safe_metadata = dict(metadata)
if token is not None:
    safe_metadata.update(
        {"agent_run_id": token.agent_run_id, "lease_version": token.version}
    )
return self.delegate.put(config, checkpoint, safe_metadata, new_versions)
```

`create_agent_checkpointer()` 对 MemorySaver 和 MongoDBSaver 都返回 wrapper，保证
Demo 与 Mongo 走同一 Graph 行为。

- [ ] **Step 5: 实现 Graph 节点边界和固定 checkpoint**

Graph runtime config 的 `configurable` 合并 `lease_config(token)`；公开
LangSmith metadata 仍只使用现有匿名字段，不加入 owner。

每个节点在入口和出口调用：

```python
def _assert_graph_lease(config: RunnableConfig) -> None:
    token = lease_token_from_config(config)
    if token is not None and not agent_run_lease_is_valid(token):
        raise AgentLeaseLostError(token.agent_run_id)
```

`resume_agent_graph()` 明确传入固定 ID：

```python
configurable = {
    "thread_id": request_id,
    "checkpoint_id": checkpoint_id,
    "provider_router": provider_router,
    **lease_config(lease_token),
}
```

`get_safe_resume_checkpoint_id()` 按 checkpoint 新到旧遍历，接受 metadata
`lease_version <= before_version`；无版本的历史 checkpoint 按 `0`。
`load_completed_agent_graph_result()` 只接受 metadata version 等于终态 run version
且 state 中存在 `result` 的 checkpoint。

- [ ] **Step 6: 验证 GREEN**

```powershell
python -m pytest backend/tests/test_agent_graph.py -q
```

Expected: PASS，原有同 thread 恢复测试继续通过。

- [ ] **Step 7: 提交 Task 4**

```powershell
git add backend/app/agents/checkpoint.py backend/app/agents/graph.py backend/app/services/agent_run_lease.py backend/tests/test_agent_graph.py
git commit -m "feat: fence agent checkpoints by lease"
```

---

### Task 5: Agent service 心跳、收口与手动恢复

**Files:**
- Modify: `backend/app/services/agent_run_lease.py`
- Modify: `backend/app/services/agent_service.py:1-369`
- Modify: `backend/tests/test_agent_service.py`
- Modify: `backend/tests/conftest.py`

**Interfaces:**
- Consumes: Tasks 2-4 的 store 与 Graph 接口。
- Produces: `AgentLeaseSession.run(awaitable) -> T`。
- Produces: `list_user_agent_messages(user_id) -> list[AgentMessage] | None`。
- Produces: `AgentRunExecutionError(code, message, status_code)`。
- Removes: `_active_agent_run_ids` 作为状态依据。

- [ ] **Step 1: 重写孤儿判断和竞争恢复失败测试**

先在 `backend/tests/test_agent_service.py` 增加本任务使用的完整构造函数：

```python
from datetime import UTC, datetime
from time import perf_counter

from backend.app.agents.graph import AgentGraphResult
from backend.app.models.domain import AgentChatInput, AgentRetryInput, AgentRun
from backend.app.services.agent_run_lease import AgentLeaseToken


def _lease_test_run(run_id: str) -> AgentRun:
    return AgentRun(
        agent_run_id=run_id,
        user_id="demo-user-945",
        status="running",
        started_at="2026-08-21T12:00:00Z",
        request_input=AgentRetryInput(message="继续任务", locale="zh-CN"),
    )


def _lease_test_input() -> AgentChatInput:
    return AgentChatInput(
        user_id="demo-user-945",
        locale="zh-CN",
        message="继续任务",
    )


def _lease_test_result(reply: str) -> AgentGraphResult:
    return AgentGraphResult(
        intent="ask_question",
        reply=reply,
        record_draft=None,
        today_context=None,
        rag_chunks=[],
        provider="stub",
    )


def _lease_test_token() -> AgentLeaseToken:
    return AgentLeaseToken(
        user_id="demo-user-945",
        agent_run_id="run-heartbeat",
        owner="worker-a",
        version=1,
        expires_at=datetime(2026, 8, 21, 12, 1, tzinfo=UTC),
    )
```

用租约替代活动集合：

```python
def test_agent_service_keeps_a_foreign_live_lease_running(monkeypatch):
    now = datetime(2026, 8, 21, 12, 0, tzinfo=UTC)
    monkeypatch.setattr(demo_store, "_agent_lease_now", lambda: now)
    run = demo_store.create_agent_run_with_lease(
        AgentRun(
            agent_run_id="foreign-live-run",
            user_id="demo-user-945",
            status="running",
            started_at="2026-08-21T12:00:00Z",
        ),
        "other-worker",
    )

    listed = agent_service.list_user_agent_runs(run.user_id)

    assert listed[0].status == "running"
```

```python
def test_stale_worker_cannot_publish_messages_after_a_new_lease(monkeypatch):
    now = datetime(2026, 8, 21, 12, 0, tzinfo=UTC)
    monkeypatch.setattr(demo_store, "_agent_lease_now", lambda: now)
    first = demo_store.create_agent_run_with_lease(_lease_test_run("stale-run"), "worker-a")
    first_token = lease_token_from_run(first)
    now += timedelta(seconds=61)
    demo_store.interrupt_expired_agent_runs(first.user_id)
    second = demo_store.acquire_agent_run_lease(first.user_id, first.agent_run_id, "worker-b")

    result = agent_service._complete_agent_run(
        first,
        first_token,
        _lease_test_input(),
        _lease_test_result("旧结果"),
        perf_counter(),
    )

    assert result is None
    assert demo_store.list_agent_messages(first.user_id) == []
    assert second.lease_version == 2
```

增加事件控制的双 resume 测试，避免依赖线程调度速度：

```python
def test_agent_service_allows_only_one_concurrent_resume(monkeypatch):
    interrupted = _lease_test_run("concurrent-resume").model_copy(
        update={"status": "interrupted"}
    )
    demo_store.save_agent_run(interrupted)
    started = asyncio.Event()
    release = asyncio.Event()
    calls = 0

    monkeypatch.setattr(
        agent_service,
        "get_safe_resume_checkpoint_id",
        lambda run_id, before_version: "checkpoint-safe",
    )

    async def slow_resume(*args, **kwargs):
        nonlocal calls
        calls += 1
        started.set()
        await release.wait()
        return _lease_test_result("恢复完成")

    monkeypatch.setattr(agent_service, "resume_agent_graph", slow_resume)

    async def scenario():
        first = asyncio.create_task(
            agent_service.resume_agent_run(interrupted.user_id, interrupted.agent_run_id)
        )
        await started.wait()
        with pytest.raises(agent_service.AgentRunResumeError) as captured:
            await agent_service.resume_agent_run(interrupted.user_id, interrupted.agent_run_id)
        assert captured.value.code == "AGENT_RUN_ACTIVE"
        release.set()
        await first

    asyncio.run(scenario())

    saved = demo_store.list_agent_runs(interrupted.user_id)[0]
    assert calls == 1
    assert saved.resume_count == 1
    assert saved.status == "completed"
```

- [ ] **Step 2: 写心跳丢失和消息修复失败测试**

```python
def test_lease_session_cancels_work_when_renewal_loses_ownership(monkeypatch):
    token = _lease_test_token()
    monkeypatch.setattr(agent_run_lease, "renew_agent_run_lease", lambda _: None)

    async def never_finishes():
        await asyncio.Event().wait()

    with pytest.raises(AgentLeaseLostError):
        asyncio.run(
            AgentLeaseSession(token, heartbeat_seconds=0).run(never_finishes())
        )
```

消息修复测试不允许重新执行 Graph：

```python
def test_message_repair_reads_the_final_checkpoint_without_running_the_graph(monkeypatch):
    run = _lease_test_run("repair-messages").model_copy(
        update={
            "status": "completed",
            "lease_version": 1,
            "messages_persisted": False,
            "completed_at": "2026-08-21T12:01:00Z",
        }
    )
    demo_store.save_agent_run(run)
    monkeypatch.setattr(
        agent_service,
        "load_completed_agent_graph_result",
        lambda run_id, lease_version: _lease_test_result("检查点回复"),
    )

    async def forbidden_graph_call(*args, **kwargs):
        raise AssertionError("message repair must not execute the graph")

    monkeypatch.setattr(agent_service, "run_agent_graph", forbidden_graph_call)
    monkeypatch.setattr(agent_service, "resume_agent_graph", forbidden_graph_call)

    messages = agent_service.list_user_agent_messages(run.user_id)

    assert [message.message_id for message in messages] == [
        f"msg-user-{run.agent_run_id}",
        f"msg-agent-{run.agent_run_id}",
    ]
    repaired = demo_store.list_agent_runs(run.user_id)[0]
    assert repaired.messages_persisted is True
```

- [ ] **Step 3: 运行测试并确认 RED**

```powershell
python -m pytest backend/tests/test_agent_service.py -q
```

Expected: FAIL，因为 service 仍依赖活动集合且先写消息后写终态。

- [ ] **Step 4: 实现 AgentLeaseSession**

在同一模块定义 HTTP 可映射的执行错误：

```python
class AgentRunExecutionError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 409) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
```

`AgentLeaseSession.run()` 同时维护 Graph task 和心跳：

```python
async def run(self, awaitable):
    work = asyncio.create_task(awaitable)
    heartbeat = asyncio.create_task(self._heartbeat(work))
    try:
        return await work
    except asyncio.CancelledError as exc:
        if self.lease_lost:
            raise AgentLeaseLostError(self.token.agent_run_id) from exc
        raise
    finally:
        heartbeat.cancel()
        with suppress(asyncio.CancelledError):
            await heartbeat
```

`_heartbeat()` 每次调用 `renew_agent_run_lease(self.token)` 并用返回 run 更新 token：

```python
async def _heartbeat(self, work: asyncio.Task) -> None:
    while not work.done():
        await asyncio.sleep(self.heartbeat_seconds)
        try:
            renewed = renew_agent_run_lease(self.token)
        except Exception:
            if datetime.now(UTC) < self.token.expires_at:
                continue
            renewed = None
        if renewed is None:
            self.lease_lost = True
            work.cancel()
            return
        self.token = lease_token_from_run(renewed)
```

Mongo 查询是否有效仍由 store 完成，不能只比较本机 expires_at。本机时间只用于
判断数据库异常还能否在已知到期时间前重试。

- [ ] **Step 5: 改造创建与恢复流程**

`create_agent_reply()`：

```python
leased_run = create_agent_run_with_lease(run, new_lease_owner())
if leased_run is None:
    raise AgentRunExecutionError("AGENT_RUN_CONFLICT", "Agent run already exists.")
token = lease_token_from_run(leased_run)
session = AgentLeaseSession(token)
graph_result = await session.run(
    run_agent_graph(
        user_id=input_data.user_id,
        locale=input_data.locale,
        message=input_data.message,
        context=input_data.context,
        conversation=existing[-10:],
        provider_router=provider_router,
        request_id=request_id,
        lease_token=token,
    )
)
token = session.token
```

`resume_agent_run()`：

1. 先 `interrupt_expired_agent_runs(user_id)`。
2. 仅通过 `acquire_agent_run_lease()` 抢占 `interrupted`。
3. 竞争失败后重新读取；`running` 映射 `AGENT_RUN_ACTIVE`，终态映射
   `AGENT_RUN_NOT_RESUMABLE`。
4. 使用 `get_safe_resume_checkpoint_id(run_id, leased.lease_version - 1)`。
5. 使用当前 token 写入 `resume_checkpoint_id`。
6. 在 `AgentLeaseSession` 中调用固定 checkpoint 的 `resume_agent_graph()`。

删除 `_active_agent_run_ids` 的所有 add/discard/contains 操作。
同时从 `backend/tests/conftest.py` 删除两处
`agent_service._active_agent_run_ids.clear()`；其余 fixture 清理保持不变。

- [ ] **Step 6: 改造终态和消息顺序**

`_complete_agent_run()` 先构造 completed run，并执行：

```python
completed = transition_agent_run_with_lease(
    token,
    run.model_copy(
        update={
            "status": "completed",
            "completed_at": completed_at,
            "updated_at": completed_at,
            "messages_persisted": False,
            **result_fields,
        }
    ),
)
if completed is None:
    return None
save_agent_message(user_message)
save_agent_message(agent_message)
mark_agent_run_messages_persisted(
    completed.user_id,
    completed.agent_run_id,
    completed.lease_version,
)
return agent_message
```

`_fail_agent_run()`、`_interrupt_agent_run()` 和 checkpoint missing 都改用
`transition_agent_run_with_lease()`。CAS 失败统一转成 `AgentLeaseLostError`，
不能再次普通 upsert。

- [ ] **Step 7: 实现过期列表和消息幂等修复**

`list_user_agent_runs()` 固定为：

```python
def list_user_agent_runs(user_id: str) -> list[AgentRun] | None:
    interrupt_expired_agent_runs(user_id)
    return list_agent_runs(user_id)
```

`list_user_agent_messages()` 对 completed 且
`messages_persisted == false` 的 run 调用
`load_completed_agent_graph_result(run_id, run.lease_version)`；只有读到最终结果才
使用 `request_input` 和确定性 ID 补齐消息并标记 true。不得调用
`run_agent_graph`、`resume_agent_graph` 或 Provider。

- [ ] **Step 8: 验证 GREEN**

```powershell
python -m pytest backend/tests/test_agent_service.py backend/tests/test_agent_graph.py -q
```

Expected: PASS；结构化 workout/meal 写入断言仍为零。

- [ ] **Step 9: 提交 Task 5**

```powershell
git add backend/app/services/agent_run_lease.py backend/app/services/agent_service.py backend/tests/test_agent_service.py backend/tests/conftest.py
git commit -m "feat: run agents under renewable leases"
```

---

### Task 6: HTTP 契约、双实例验收与运行文档

**Files:**
- Modify: `backend/app/api/routes_agent.py:1-170`
- Modify: `backend/tests/test_agent_api.py:299-434`
- Modify: `backend/tests/test_auth_api.py:90-122`
- Modify: `backend/tests/test_agent_run_lease_mongo.py`
- Modify: `tests/http-integration.spec.ts`
- Modify: `backend/README.md`

**Interfaces:**
- Consumes: `list_user_agent_messages()`、`AgentRunExecutionError` 和完整租约状态机。
- Preserves: 现有四个公开 run 状态及 chat/resume/retry 路径。
- Hides: 所有 `lease_*`、`resume_checkpoint_id`、`messages_persisted` 字段。

- [ ] **Step 1: 写公开字段和错误映射失败测试**

`test_get_agent_runs_exposes_safe_observability_fields_only` 增加内部字段断言：

```python
internal_fields = {
    "lease_owner",
    "lease_version",
    "lease_expires_at",
    "last_heartbeat_at",
    "resume_checkpoint_id",
    "messages_persisted",
}
assert internal_fields.isdisjoint(runs[0])
```

增加有效外部租约 API 用例：

```python
def test_run_api_keeps_a_foreign_live_lease_running(monkeypatch):
    now = datetime(2026, 8, 21, 12, 0, tzinfo=UTC)
    monkeypatch.setattr(demo_store, "_agent_lease_now", lambda: now)
    demo_store.create_agent_run_with_lease(
        AgentRun(
            agent_run_id="api-live-run",
            user_id="demo-user-945",
            status="running",
            started_at="2026-08-21T12:00:00Z",
        ),
        "other-worker",
    )

    response = client.get("/api/agent/runs", params={"user_id": "demo-user-945"})

    assert response.status_code == 200
    assert response.json()["data"][0]["status"] == "running"
```

测试文件导入 `UTC` 和 `datetime`。再增加双 resume 请求：

```python
from concurrent.futures import ThreadPoolExecutor


def test_concurrent_resume_requests_execute_the_run_once():
    input_data = AgentChatInput(
        user_id="demo-user-945",
        locale="zh-CN",
        message="如何热身？",
    )
    with pytest.raises(RuntimeError):
        asyncio.run(create_agent_reply(input_data, provider_router=RuntimeCrashRouter()))
    run_id = demo_store.list_agent_runs(input_data.user_id)[0].agent_run_id

    def resume_once():
        return client.post(
            f"/api/agent/runs/{run_id}/resume",
            json={"user_id": input_data.user_id},
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(lambda _: resume_once(), range(2)))

    assert sorted(response.status_code for response in responses) == [200, 409]
    conflict = next(response for response in responses if response.status_code == 409)
    assert conflict.json()["error"]["code"] in {
        "AGENT_RUN_ACTIVE",
        "AGENT_RUN_NOT_RESUMABLE",
    }
    saved_run = demo_store.list_agent_runs(input_data.user_id)[0]
    assert saved_run.resume_count == 1
    assert [message.message_id for message in demo_store.list_agent_messages(input_data.user_id)] == [
        f"msg-user-{run_id}",
        f"msg-agent-{run_id}",
    ]
```

第二个请求允许在第一个请求已快速完成时返回 `AGENT_RUN_NOT_RESUMABLE`；无论
调度顺序如何，成功数、resume_count 和消息数量必须固定。

- [ ] **Step 2: 运行 API 测试并确认 RED**

```powershell
python -m pytest backend/tests/test_agent_api.py backend/tests/test_auth_api.py -q
```

Expected: FAIL，因为路由尚未过滤租约字段或捕获执行租约错误。

- [ ] **Step 3: 修改路由而不改变前端公开类型**

定义固定内部字段集合：

```python
AGENT_RUN_INTERNAL_FIELDS = {
    "request_input",
    "retry_input",
    "trace_steps",
    "lease_owner",
    "lease_version",
    "lease_expires_at",
    "last_heartbeat_at",
    "resume_checkpoint_id",
    "messages_persisted",
}
```

`/runs` 使用 `run.model_dump(exclude=AGENT_RUN_INTERNAL_FIELDS)`。
`/messages` 改为调用 `list_user_agent_messages()`，保证 pending message 可以
幂等修复。`/chat` 和 `/resume` 捕获 `AgentRunExecutionError`，返回异常中
固定的 status、code 和 `agent_run_id`，不泄露 owner/version。

- [ ] **Step 4: 完成真实 Mongo 双实例生命周期测试**

在 Task 3 的测试基础上补齐：

- owner-a 有效时第二个 store 列表仍返回 `running`。
- 没有调用 acquire 时，过期收口后保持 `interrupted`。
- owner-b 取得 version 2 并完成。
- owner-a 的续租、checkpoint CAS、终态 CAS 全部失败。
- 最终 run 为 owner-b 的 `completed`，确定性消息最多各一条。

运行：

```powershell
$env:945_RUN_MONGO_INTEGRATION_TESTS="1"
python -m pytest backend/tests/test_agent_run_lease_mongo.py -q
Remove-Item Env:945_RUN_MONGO_INTEGRATION_TESTS
```

Expected: PASS。

- [ ] **Step 5: 扩充 HTTP 集成回归**

`tests/http-integration.spec.ts` 在 run 响应断言中增加：

```typescript
expect(run.status).toBe("completed");
expect(run).not.toHaveProperty("lease_owner");
expect(run).not.toHaveProperty("lease_version");
expect(run).not.toHaveProperty("lease_expires_at");
expect(run).not.toHaveProperty("resume_checkpoint_id");
expect(run).not.toHaveProperty("messages_persisted");
```

保留现有 `tests/agent-workflow.spec.ts` 的“继续任务只发送一次”测试，不修改
AgentPage 样式或文案。

- [ ] **Step 6: 更新运行文档**

`backend/README.md` 增加以下配置和语义：

```powershell
$env:945_AGENT_LEASE_TTL_SECONDS="60"
$env:945_AGENT_LEASE_HEARTBEAT_SECONDS="15"
```

文档明确：Mongo 多 Worker 共享租约；过期只标记中断；用户点击后才恢复；默认
`npm run qa:lv4` 不调用 DeepSeek。

- [ ] **Step 7: 运行直接相关验证**

```powershell
python -m pytest backend/tests/test_agent_run_lease_store.py backend/tests/test_agent_run_lease_mongo.py backend/tests/test_agent_service.py backend/tests/test_agent_graph.py backend/tests/test_agent_api.py backend/tests/test_auth_api.py -q
npm run build
npx playwright test tests/agent-workflow.spec.ts
```

Expected: PASS。未设置 Mongo integration 环境变量时，真实 Mongo 文件只跳过带
标记用例；Task 6 Step 4 已单独执行真实 Mongo 版本。

- [ ] **Step 8: 运行严格离线验收**

```powershell
python -m pytest backend/tests -q
npm run qa:http
npm run qa:mongo
npm run qa:lv4
```

Expected: 全部 exit code `0`；不运行 `npm run qa:lv4:deepseek`。

- [ ] **Step 9: 检查前端冻结边界和仓库卫生**

```powershell
git diff --name-only 83edfd6..HEAD -- src
git status --short
```

Expected: 第一条无输出；第二条只允许计划内修改，以及未跟踪的 `.venv/`、
`output/`。如果 `src/` 有输出，先确认是否属于公开契约不可兼容的必要适配；
视觉文件和 CSS 不得进入提交。

- [ ] **Step 10: 提交 Task 6**

```powershell
git add backend/app/api/routes_agent.py backend/tests/test_agent_api.py backend/tests/test_auth_api.py backend/tests/test_agent_run_lease_mongo.py tests/http-integration.spec.ts backend/README.md
git commit -m "test: verify distributed agent run recovery"
```

---

## Final Verification Checklist

- [ ] `python -m pytest backend/tests -q` 通过。
- [ ] 真实 Mongo 双 owner 测试证明同一 run 只有一个 version 2 获胜者。
- [ ] `npm run build` 通过。
- [ ] `npm run qa:http` 通过。
- [ ] `npm run qa:mongo` 通过。
- [ ] `npm run qa:lv4` 通过且没有启用 paid smoke。
- [ ] 有效外部租约不会被列表读取改成 `interrupted`。
- [ ] 租约过期不会自动调用模型。
- [ ] 用户手动恢复沿用同一 `agent_run_id/thread_id`。
- [ ] 旧 Worker 无法更新 checkpoint 选择、消息或终态。
- [ ] 重复用户消息和 Agent 消息数均为 `0`。
- [ ] workout、meal、plan 结构化写入数均为 `0`。
- [ ] 公开 run API 不包含任何租约内部字段。
- [ ] `src/` 生产组件和视觉规则没有变更。
- [ ] `.venv/`、`output/` 和密钥没有提交。
