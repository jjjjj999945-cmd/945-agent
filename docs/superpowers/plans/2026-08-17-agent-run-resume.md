# Agent Run Resume Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 945 增加用户手动触发的同一 Agent run/checkpoint 中断恢复，并在不改变现有视觉系统和结构化写入安全边界的前提下完成严格验收。

**Architecture:** `POST /api/agent/chat` 在执行 Graph 前持久化 `running` run，并以 `agent_run_id` 作为 LangGraph `thread_id`。当前进程活动集合区分仍在执行的 run 与重启后遗留的孤立 run；`POST /api/agent/runs/{id}/resume` 使用原 thread 的 state snapshot，从最后一个成功节点继续或直接收口已完成结果。确定性消息 ID 和 store upsert 保证恢复幂等。

**Tech Stack:** Python 3.11、FastAPI、Pydantic、LangGraph 0.6.11、MongoDBSaver、React 19、TypeScript、Vite、Pytest、Playwright。

## Global Constraints

- 恢复必须由用户点击“继续任务”触发，禁止页面自动调用恢复接口。
- 恢复前后 `agent_run_id` 和 LangGraph `thread_id` 必须相同。
- 已知 `LLMError` 继续进入 `failed` 并使用现有 retry；执行链中断才进入 `interrupted`。
- checkpoint 缺失必须返回 `AGENT_CHECKPOINT_MISSING`，禁止静默从头执行。
- 当前阶段只保证单 Uvicorn worker；不引入 Redis、租约、心跳或分布式锁。
- 模型只生成草稿；结构化训练、饮食和计划写入仍需用户确认。
- 不修改颜色、字体、图标、导航、玻璃效果、组件视觉样式或整体设计语言。
- 不新增 CSS 视觉规则、不新增依赖、不运行付费 DeepSeek 验收。
- `.venv/` 和 `output/` 不暂存、不提交。

## File Structure

- `backend/app/models/domain.py`：run 生命周期和指标契约。
- `backend/app/services/demo_store.py`：内存模式 Agent run/message upsert。
- `backend/app/services/agent_observability.py`：四状态指标汇总。
- `backend/app/agents/graph.py`：原 thread snapshot 读取和恢复。
- `backend/app/services/agent_service.py`：活动集合、状态流转、幂等收口和恢复规则。
- `backend/app/api/routes_agent.py`：run 列表收口与恢复 HTTP 接口。
- `src/types/domain.ts`、`src/services/*.ts`：前端类型和 adapter 契约。
- `src/pages/AgentPage.tsx`：现有状态面板的恢复和轮询交互。
- `backend/tests/`、`tests/agent-workflow.spec.ts`：分层验收。

---

### Task 1: Run 生命周期模型、幂等存储与指标

**Files:**
- Modify: `backend/app/models/domain.py:375-432`
- Modify: `backend/app/services/demo_store.py:254-286`
- Modify: `backend/app/services/agent_observability.py:1-30`
- Modify: `backend/tests/test_agent_service.py`
- Modify: `backend/tests/test_agent_api.py:291-346`

**Interfaces:**
- Produces: `AgentRun.status = running | interrupted | completed | failed`。
- Produces: `request_input`、`updated_at`、`resume_count`。
- Produces: `AgentRunMetrics.running_runs`、`interrupted_runs`。
- Produces: Demo `save_agent_run()`、`save_agent_message()` 按 ID upsert。

- [ ] **Step 1: 写失败测试**

在 `backend/tests/test_agent_service.py` 增加：

```python
from backend.app.models.domain import AgentMessage, AgentRetryInput, AgentRun
from backend.app.services.agent_observability import summarize_agent_runs
from backend.app.services.demo_seed import timestamp


def test_demo_store_upserts_agent_runs_and_messages_by_id():
    now = timestamp()
    run = AgentRun(
        agent_run_id="run-upsert",
        user_id="demo-user-945",
        status="running",
        started_at=now,
        updated_at=now,
        request_input=AgentRetryInput(message="继续任务", locale="zh-CN"),
    )
    demo_store.save_agent_run(run)
    demo_store.save_agent_run(run.model_copy(update={"status": "interrupted"}))
    message = AgentMessage(
        message_id="msg-agent-run-upsert",
        user_id="demo-user-945",
        role="agent",
        content="旧内容",
        locale="zh-CN",
        created_at=now,
    )
    demo_store.save_agent_message(message)
    demo_store.save_agent_message(message.model_copy(update={"content": "新内容"}))

    assert len(demo_store.list_agent_runs("demo-user-945")) == 1
    assert demo_store.list_agent_runs("demo-user-945")[0].status == "interrupted"
    assert len(demo_store.list_agent_messages("demo-user-945")) == 1
    assert demo_store.list_agent_messages("demo-user-945")[0].content == "新内容"


def test_agent_metrics_exclude_nonterminal_runs_from_rate_and_latency():
    now = timestamp()
    runs = [
        AgentRun(agent_run_id="completed", user_id="demo-user-945", status="completed", started_at=now, updated_at=now, completed_at=now, duration_ms=100),
        AgentRun(agent_run_id="failed", user_id="demo-user-945", status="failed", started_at=now, updated_at=now, completed_at=now, duration_ms=300, error_code="LLM_TIMEOUT"),
        AgentRun(agent_run_id="running", user_id="demo-user-945", status="running", started_at=now, updated_at=now, duration_ms=900),
        AgentRun(agent_run_id="interrupted", user_id="demo-user-945", status="interrupted", started_at=now, updated_at=now, duration_ms=700),
    ]

    metrics = summarize_agent_runs(runs)

    assert (metrics.total_runs, metrics.completed_runs, metrics.failed_runs) == (4, 1, 1)
    assert (metrics.running_runs, metrics.interrupted_runs) == (1, 1)
    assert metrics.success_rate == 0.5
    assert metrics.average_duration_ms == 200
```

在现有 metrics API 预期中增加 `"running_runs": 0` 和 `"interrupted_runs": 0`。

- [ ] **Step 2: 运行测试并确认 RED**

```powershell
python -m pytest backend/tests/test_agent_service.py::test_demo_store_upserts_agent_runs_and_messages_by_id backend/tests/test_agent_service.py::test_agent_metrics_exclude_nonterminal_runs_from_rate_and_latency backend/tests/test_agent_api.py::test_get_agent_metrics_aggregates_success_failure_and_latency -q
```

Expected: FAIL，因为状态、指标字段或 upsert 尚不存在。

- [ ] **Step 3: 实现模型字段**

```python
class AgentRun(ApiModel):
    agent_run_id: str
    user_id: str
    status: Literal["running", "interrupted", "completed", "failed"]
    started_at: str
    updated_at: str | None = None
    completed_at: str | None = None
    duration_ms: float = 0
    provider: str | None = None
    model: str | None = None
    intent: str | None = None
    draft_type: str | None = None
    degraded: bool = False
    degraded_reason: str | None = None
    error_code: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    logical_generations: int = 0
    http_attempts: int = 0
    request_input: AgentRetryInput | None = None
    retry_input: AgentRetryInput | None = None
    retry_of_agent_run_id: str | None = None
    resume_count: int = 0
    trace_steps: list[AgentTraceStep] = []


class AgentRunMetrics(ApiModel):
    total_runs: int
    completed_runs: int
    failed_runs: int
    running_runs: int
    interrupted_runs: int
    success_rate: float
    average_duration_ms: float
    total_input_tokens: int
    total_output_tokens: int
    total_logical_generations: int
    total_http_attempts: int
    failures_by_code: dict[str, int]
```

- [ ] **Step 4: 实现 Demo upsert 和终态指标**

两个 save 函数都使用同一模式，不增加通用抽象：

```python
existing = next((item for item in agent_runs if item.agent_run_id == run.agent_run_id), None)
if existing is None:
    agent_runs.append(run)
else:
    agent_runs[agent_runs.index(existing)] = run
```

消息使用 `message_id` 对应实现。指标实现固定为：

```python
running_runs = [run for run in runs if run.status == "running"]
interrupted_runs = [run for run in runs if run.status == "interrupted"]
terminal_runs = completed_runs + failed_runs
terminal_count = len(terminal_runs)
success_rate = round(len(completed_runs) / terminal_count, 4) if terminal_count else 0.0
average_duration_ms = (
    round(sum(run.duration_ms for run in terminal_runs) / terminal_count, 2)
    if terminal_count
    else 0.0
)
```

其余 token、generation、HTTP attempt 和错误码聚合保持原实现。

- [ ] **Step 5: 验证 GREEN**

```powershell
python -m pytest backend/tests/test_agent_service.py backend/tests/test_agent_api.py -q
```

Expected: PASS。

- [ ] **Step 6: 提交 Task 1**

```powershell
git add backend/app/models/domain.py backend/app/services/demo_store.py backend/app/services/agent_observability.py backend/tests/test_agent_service.py backend/tests/test_agent_api.py
git commit -m "feat: add agent run lifecycle states"
```

---

### Task 2: LangGraph 原 thread checkpoint 恢复

**Files:**
- Modify: `backend/app/agents/graph.py:247-294`
- Modify: `backend/tests/test_agent_graph.py`

**Interfaces:**
- Produces: `AgentCheckpointMissingError`。
- Produces: `resume_agent_graph(request_id, *, provider_router=None) -> AgentGraphResult`。

- [ ] **Step 1: 写恢复行为失败测试**

```python
class CrashOnceRouter:
    def __init__(self):
        self.requests = []

    async def generate(self, request):
        self.requests.append(request)
        if len(self.requests) == 1:
            raise RuntimeError("simulated process interruption")
        return AgentModelResponse(intent="ask_question", reply="恢复完成", provider="stub")

    async def recover(self, request, exc):
        raise exc


def test_agent_graph_resumes_the_same_thread_from_the_failed_node(monkeypatch):
    router = CrashOnceRouter()
    original = agent_graph_module.context_builder
    context_calls = []

    def counting_context_builder(user_id, date):
        context_calls.append((user_id, date))
        return original(user_id, date)

    monkeypatch.setattr(agent_graph_module, "context_builder", counting_context_builder)
    agent_graph_module.get_agent_graph.cache_clear()
    with pytest.raises(RuntimeError, match="simulated process interruption"):
        asyncio.run(run_agent_graph(
            user_id=DEMO_USER_ID,
            locale="zh-CN",
            message="如何热身？",
            context={"date": "2026-07-11"},
            provider_router=router,
            request_id="graph-resume-same-thread",
        ))

    result = asyncio.run(agent_graph_module.resume_agent_graph(
        "graph-resume-same-thread",
        provider_router=router,
    ))

    assert result.reply == "恢复完成"
    assert len(context_calls) == 1
    assert len(router.requests) == 2


def test_agent_graph_returns_completed_snapshot_without_provider_call():
    first = StubRouter([AgentModelResponse(intent="ask_question", reply="已经完成", provider="stub")])
    asyncio.run(run_agent_graph(
        user_id=DEMO_USER_ID,
        locale="zh-CN",
        message="如何热身？",
        provider_router=first,
        request_id="graph-resume-completed",
    ))
    never_called = StubRouter([RuntimeError("provider must not be called")])

    result = asyncio.run(agent_graph_module.resume_agent_graph(
        "graph-resume-completed",
        provider_router=never_called,
    ))

    assert result.reply == "已经完成"
    assert never_called.requests == []


def test_agent_graph_rejects_a_missing_checkpoint():
    with pytest.raises(agent_graph_module.AgentCheckpointMissingError):
        asyncio.run(agent_graph_module.resume_agent_graph("missing-checkpoint"))
```

- [ ] **Step 2: 运行测试并确认 RED**

```powershell
python -m pytest backend/tests/test_agent_graph.py -k "resumes_the_same_thread or completed_snapshot or missing_checkpoint" -q
```

Expected: FAIL，因为恢复函数和异常类型尚不存在。

- [ ] **Step 3: 实现 snapshot 检查与恢复**

```python
class AgentCheckpointMissingError(Exception):
    pass


async def resume_agent_graph(
    request_id: str,
    *,
    provider_router: LLMProviderRouter | None = None,
) -> AgentGraphResult:
    graph = get_agent_graph()
    snapshot = graph.get_state({"configurable": {"thread_id": request_id}})
    values = dict(snapshot.values or {})
    saved_result = values.get("result")
    if saved_result is not None:
        return AgentGraphResult.model_validate(saved_result)
    if not values or not snapshot.next:
        raise AgentCheckpointMissingError(request_id)

    user_id = str(values["user_id"])
    locale = str(values["locale"])
    settings = get_settings()
    state = await graph.ainvoke(
        None,
        config={
            "configurable": {"thread_id": request_id, "provider_router": provider_router},
            "metadata": agent_trace_metadata(
                request_id=request_id,
                user_id=user_id,
                locale=locale,
                provider=settings.llm_provider,
            ),
        },
    )
    result = state.get("result")
    if result is None:
        raise AgentCheckpointMissingError(request_id)
    return AgentGraphResult.model_validate(result)
```

- [ ] **Step 4: 验证 Graph GREEN**

```powershell
python -m pytest backend/tests/test_agent_graph.py -q
```

Expected: PASS，且 `context_builder` 只执行一次。

- [ ] **Step 5: 增加真实 MongoSaver 重建恢复测试**

在现有 Mongo checkpoint 测试旁增加：

```python
@pytest.mark.skipif(
    os.getenv("945_RUN_MONGO_INTEGRATION_TESTS") != "1",
    reason="Set 945_RUN_MONGO_INTEGRATION_TESTS=1 to run against local MongoDB.",
)
def test_mongo_checkpoint_resumes_after_graph_and_saver_recreation(monkeypatch):
    from pymongo import MongoClient

    from backend.app.agents.checkpoint import get_agent_checkpointer
    from backend.app.core.config import get_settings

    database_name = "945_agent_resume_checkpoint_test"
    client = MongoClient("mongodb://127.0.0.1:27017")
    client.drop_database(database_name)
    monkeypatch.setenv("945_STORAGE_BACKEND", "mongo")
    monkeypatch.setenv("945_MONGODB_DATABASE", database_name)
    get_settings.cache_clear()
    get_agent_checkpointer.cache_clear()
    get_agent_graph.cache_clear()
    router = CrashOnceRouter()
    try:
        with pytest.raises(RuntimeError, match="simulated process interruption"):
            asyncio.run(run_agent_graph(
                user_id=DEMO_USER_ID,
                locale="zh-CN",
                message="如何热身？",
                provider_router=router,
                request_id="mongo-resume-after-restart",
            ))

        get_agent_graph.cache_clear()
        get_agent_checkpointer.cache_clear()
        result = asyncio.run(agent_graph_module.resume_agent_graph(
            "mongo-resume-after-restart",
            provider_router=router,
        ))

        assert result.reply == "恢复完成"
    finally:
        client.drop_database(database_name)
        get_agent_graph.cache_clear()
        get_agent_checkpointer.cache_clear()
        get_settings.cache_clear()
```

- [ ] **Step 6: 提交 Task 2**

```powershell
git add backend/app/agents/graph.py backend/tests/test_agent_graph.py
git commit -m "feat: resume agent graph checkpoints"
```

---

### Task 3: Service 状态流转、孤立 run 收口与幂等恢复

**Files:**
- Modify: `backend/app/services/agent_service.py`
- Modify: `backend/tests/conftest.py`
- Modify: `backend/tests/test_agent_service.py`

**Interfaces:**
- Consumes: `resume_agent_graph()`、`AgentCheckpointMissingError`。
- Produces: `list_user_agent_runs(user_id) -> list[AgentRun] | None`。
- Produces: `resume_agent_run(user_id, agent_run_id, *, provider_router=None) -> AgentMessage | None`。
- Produces: `AgentRunResumeError(code, message, status_code=409)`。

- [ ] **Step 1: 让 fixture 隔离 Graph、checkpointer 和活动集合**

在 `backend/tests/conftest.py` 的 autouse fixture 前后增加：

```python
from backend.app.agents.checkpoint import get_agent_checkpointer
from backend.app.agents.graph import get_agent_graph
from backend.app.services import agent_service

get_agent_graph.cache_clear()
get_agent_checkpointer.cache_clear()
agent_service._active_agent_run_ids.clear()
```

yield 后再次执行这三项清理，保留现有 settings/router/demo store 清理顺序。

- [ ] **Step 2: 写 Service 失败测试**

增加 Provider：

```python
from backend.app.llm.models import AgentModelResponse


class InspectingRouter:
    def __init__(self):
        self.observed_status = None

    async def generate(self, request):
        self.observed_status = demo_store.list_agent_runs(request.user_id)[0].status
        return AgentModelResponse(intent="ask_question", reply="执行完成", provider="stub")

    async def recover(self, request, exc):
        raise exc


class RuntimeCrashOnceRouter:
    def __init__(self):
        self.attempts = 0

    async def generate(self, request):
        self.attempts += 1
        if self.attempts == 1:
            raise RuntimeError("simulated interruption")
        return AgentModelResponse(intent="ask_question", reply="恢复后的回复", provider="stub")

    async def recover(self, request, exc):
        raise exc


class CancelledRouter:
    async def generate(self, request):
        raise asyncio.CancelledError()

    async def recover(self, request, exc):
        raise exc
```

增加测试：

```python
def test_agent_service_persists_running_before_provider_execution():
    router = InspectingRouter()
    reply = asyncio.run(create_agent_reply(
        AgentChatInput(user_id="demo-user-945", locale="zh-CN", message="如何热身？"),
        provider_router=router,
    ))

    runs = demo_store.list_agent_runs("demo-user-945")
    assert router.observed_status == "running"
    assert len(runs) == 1
    assert runs[0].status == "completed"
    assert reply.message_id == f"msg-agent-{runs[0].agent_run_id}"


def test_agent_service_resumes_interrupted_run_in_place_without_writes():
    router = RuntimeCrashOnceRouter()
    input_data = AgentChatInput(
        user_id="demo-user-945",
        locale="zh-CN",
        message="今天深蹲 4 组，每组 8 次，80kg，帮我记录",
    )
    with pytest.raises(RuntimeError, match="simulated interruption"):
        asyncio.run(create_agent_reply(input_data, provider_router=router))

    interrupted = demo_store.list_agent_runs("demo-user-945")[0]
    assert interrupted.status == "interrupted"
    assert list_agent_messages("demo-user-945") == []

    reply = asyncio.run(agent_service.resume_agent_run(
        "demo-user-945",
        interrupted.agent_run_id,
        provider_router=router,
    ))

    runs = demo_store.list_agent_runs("demo-user-945")
    messages = list_agent_messages("demo-user-945")
    assert len(runs) == 1
    assert runs[0].agent_run_id == interrupted.agent_run_id
    assert runs[0].status == "completed"
    assert runs[0].resume_count == 1
    assert [message.message_id for message in messages] == [
        f"msg-user-{interrupted.agent_run_id}",
        f"msg-agent-{interrupted.agent_run_id}",
    ]
    assert reply.message_id == f"msg-agent-{interrupted.agent_run_id}"
    assert demo_store.list_workout_logs("demo-user-945") == []
    assert demo_store.list_meal_logs("demo-user-945") == []


def test_agent_service_marks_orphaned_running_run_interrupted():
    now = timestamp()
    demo_store.save_agent_run(AgentRun(
        agent_run_id="orphaned-run",
        user_id="demo-user-945",
        status="running",
        started_at=now,
        updated_at=now,
        request_input=AgentRetryInput(message="继续任务", locale="zh-CN"),
    ))

    runs = agent_service.list_user_agent_runs("demo-user-945")

    assert runs[0].status == "interrupted"


def test_agent_service_fails_explicitly_when_checkpoint_is_missing():
    now = timestamp()
    demo_store.save_agent_run(AgentRun(
        agent_run_id="missing-checkpoint",
        user_id="demo-user-945",
        status="interrupted",
        started_at=now,
        updated_at=now,
        request_input=AgentRetryInput(message="继续任务", locale="zh-CN"),
    ))

    with pytest.raises(agent_service.AgentRunResumeError) as captured:
        asyncio.run(agent_service.resume_agent_run("demo-user-945", "missing-checkpoint"))

    run = demo_store.list_agent_runs("demo-user-945")[0]
    assert captured.value.code == "AGENT_CHECKPOINT_MISSING"
    assert run.status == "failed"
    assert run.error_code == "AGENT_CHECKPOINT_MISSING"
    assert run.retry_input.message == "继续任务"


def test_agent_service_marks_cancelled_execution_interrupted():
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(create_agent_reply(
            AgentChatInput(user_id="demo-user-945", locale="zh-CN", message="如何热身？"),
            provider_router=CancelledRouter(),
        ))

    run = demo_store.list_agent_runs("demo-user-945")[0]
    assert run.status == "interrupted"
    assert list_agent_messages("demo-user-945") == []
```

再增加两个单行为测试：活动集合内的 run 返回 `AGENT_RUN_ACTIVE`；`completed/failed` 返回 `AGENT_RUN_NOT_RESUMABLE`。两者都断言消息数未增加。

- [ ] **Step 3: 运行 Service 测试并确认 RED**

```powershell
python -m pytest backend/tests/test_agent_service.py -q
```

Expected: FAIL，因为执行前 run、活动集合、异常中断和恢复函数尚不存在。

- [ ] **Step 4: 实现活动集合、错误和孤立 run 收口**

```python
import asyncio

from backend.app.agents.graph import (
    AgentCheckpointMissingError,
    AgentGraphResult,
    resume_agent_graph,
    run_agent_graph,
)


class AgentRunResumeError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 409) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


_active_agent_run_ids: set[str] = set()


def list_user_agent_runs(user_id: str) -> list[AgentRun] | None:
    runs = list_agent_runs(user_id)
    if runs is None:
        return None
    normalized = []
    for run in runs:
        if run.status == "running" and run.agent_run_id not in _active_agent_run_ids:
            run = save_agent_run(run.model_copy(update={
                "status": "interrupted",
                "updated_at": timestamp(),
            }))
        normalized.append(run)
    return normalized
```

`_enforce_agent_run_limit` 增加 `exclude_run_id: str | None = None`：小时 run 数排除正在恢复的原 ID，每日 token/generation 仍统计该 run 已记录用量。

- [ ] **Step 5: 实现统一收口 helpers**

实现以下准确签名：

```python
def _request_input(input_data: AgentChatInput) -> AgentRetryInput
def _elapsed_duration(run: AgentRun, started_clock: float) -> float
def _complete_agent_run(run: AgentRun, input_data: AgentChatInput, graph_result: AgentGraphResult, started_clock: float) -> AgentMessage
def _fail_agent_run(run: AgentRun, input_data: AgentChatInput, exc: LLMError, started_clock: float) -> AgentRun
def _interrupt_agent_run(run: AgentRun, started_clock: float) -> AgentRun
```

`_complete_agent_run` 必须使用：

```python
user_message_id = f"msg-user-{run.agent_run_id}"
agent_message_id = f"msg-agent-{run.agent_run_id}"
```

它先 upsert 两条消息，再将同一 run 更新为 `completed`；复制原 `provider/model/intent/draft/usage/trace` 字段。`_fail_agent_run` 设置终态时间、`error_code`、`http_attempts`、`retry_input`；`_interrupt_agent_run` 设置 `status="interrupted"`、`completed_at=None` 且不创建消息。三个 helper 都用 `_elapsed_duration()` 累加本次已记录执行时间。

- [ ] **Step 6: 重构 Chat 并实现 resume**

`create_agent_reply()` 固定顺序：额度检查；生成 ID；加入活动集合；保存带 `request_input` 的 `running` run；执行 Graph；分别用统一 helper 处理成功、`LLMError`、`asyncio.CancelledError`、其他 `Exception`；最后 `discard()` 活动 ID。

`resume_agent_run()` 固定顺序：

1. 用 `list_user_agent_runs()` 查找当前用户的 run。
2. 不存在返回 `None`；活动中抛 `AGENT_RUN_ACTIVE`；非 `interrupted` 抛 `AGENT_RUN_NOT_RESUMABLE`。
3. 无 `request_input` 时将 run 更新为 `failed/AGENT_CHECKPOINT_MISSING` 后抛错。
4. 检查使用额度，小时计数排除当前 ID。
5. 加入活动集合，将原 run 改为 `running`，`resume_count + 1`。
6. 调 `resume_agent_graph(agent_run_id)`。
7. `AgentCheckpointMissingError` 转为 `failed/AGENT_CHECKPOINT_MISSING` 并从 `request_input` 填充 `retry_input`。
8. 其他结果使用与 Chat 相同的成功、失败、中断 helper。
9. `finally` 清理活动集合。

禁止在 checkpoint 缺失分支调用 `create_agent_reply()`。

- [ ] **Step 7: 验证 GREEN**

```powershell
python -m pytest backend/tests/test_agent_service.py backend/tests/test_agent_graph.py -q
```

Expected: PASS，现有 provider-error retry 测试保持通过。

- [ ] **Step 8: 提交 Task 3**

```powershell
git add backend/app/services/agent_service.py backend/tests/conftest.py backend/tests/test_agent_service.py
git commit -m "feat: recover interrupted agent runs"
```

---

### Task 4: Resume HTTP 接口、字段保护与用户隔离

**Files:**
- Modify: `backend/app/api/routes_agent.py`
- Modify: `backend/tests/test_agent_api.py`
- Modify: `backend/tests/test_auth_api.py:67-102`

**Interfaces:**
- Consumes: `list_user_agent_runs()`、`resume_agent_run()`、`AgentRunResumeError`。
- Produces: `POST /api/agent/runs/{agent_run_id}/resume`，请求体沿用 `AgentRunRetryRequest`。

- [ ] **Step 1: 写 API 失败测试**

```python
class RuntimeCrashRouter:
    async def generate(self, request):
        raise RuntimeError("simulated interruption")

    async def recover(self, request, exc):
        raise exc


def test_resume_agent_run_uses_same_run_without_structured_writes():
    input_data = AgentChatInput(
        user_id="demo-user-945",
        locale="zh-CN",
        message="今天深蹲 4 组，每组 8 次，80kg，帮我记录",
    )
    with pytest.raises(RuntimeError):
        asyncio.run(create_agent_reply(input_data, provider_router=RuntimeCrashRouter()))
    run_id = demo_store.list_agent_runs("demo-user-945")[0].agent_run_id

    response = client.post(
        f"/api/agent/runs/{run_id}/resume",
        json={"user_id": "demo-user-945"},
    )

    assert response.status_code == 200
    assert response.json()["data"]["message_id"] == f"msg-agent-{run_id}"
    runs = demo_store.list_agent_runs("demo-user-945")
    assert len(runs) == 1
    assert runs[0].agent_run_id == run_id
    assert runs[0].status == "completed"
    assert demo_store.list_workout_logs("demo-user-945") == []
    assert demo_store.list_meal_logs("demo-user-945") == []


def test_resume_agent_run_maps_missing_checkpoint_to_conflict():
    now = timestamp()
    demo_store.save_agent_run(AgentRun(
        agent_run_id="missing-checkpoint-api",
        user_id="demo-user-945",
        status="interrupted",
        started_at=now,
        updated_at=now,
        request_input=AgentRetryInput(message="继续任务", locale="zh-CN"),
    ))

    response = client.post(
        "/api/agent/runs/missing-checkpoint-api/resume",
        json={"user_id": "demo-user-945"},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "AGENT_CHECKPOINT_MISSING"
```

扩展 run 列表测试，断言 `request_input`、`retry_input`、`trace_steps` 不暴露，且按 `updated_at or completed_at or started_at` 倒序。

在 `test_mongo_session_isolates_two_users` 中为 Alice 保存 `interrupted` run，再让 Bob 用自己的 token 和 `user_id` 请求该 run ID；断言 `404` 且 Alice 的 run 未变化。

- [ ] **Step 2: 运行测试并确认 RED**

```powershell
python -m pytest backend/tests/test_agent_api.py backend/tests/test_auth_api.py -q
```

Expected: FAIL，因为 `/resume` 不存在或字段保护/Service 列表尚未接入。

- [ ] **Step 3: 实现路由**

1. runs、trace、metrics 改用 `list_user_agent_runs()`。
2. run 列表排除 `{request_input, retry_input, trace_steps}`。
3. 提取 `_llm_error_response(exc)`，供 chat/retry/resume 共用。
4. 增加：

```python
@router.post("/runs/{agent_run_id}/resume")
async def resume(
    agent_run_id: str,
    input_data: AgentRunRetryRequest,
    authorization: str | None = Header(default=None),
) -> object:
    denied = authorize_user(input_data.user_id, authorization)
    if denied:
        return denied
    try:
        reply = await resume_agent_run(input_data.user_id, agent_run_id)
    except AgentRunResumeError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content=error(exc.code, exc.message, {"agent_run_id": agent_run_id}),
        )
    except LLMError as exc:
        return _llm_error_response(exc)
    if reply is None:
        return JSONResponse(
            status_code=404,
            content=error("NOT_FOUND", "Agent run not found.", {"agent_run_id": agent_run_id}),
        )
    return ok(reply.model_dump())
```

- [ ] **Step 4: 验证 GREEN**

```powershell
python -m pytest backend/tests/test_agent_api.py backend/tests/test_auth_api.py backend/tests/test_agent_service.py -q
```

Expected: PASS。

- [ ] **Step 5: 提交 Task 4**

```powershell
git add backend/app/api/routes_agent.py backend/tests/test_agent_api.py backend/tests/test_auth_api.py
git commit -m "feat: expose agent run resume api"
```

---

### Task 5: 前端手动恢复、running 轮询与 adapter 对齐

**Files:**
- Modify: `src/types/domain.ts:241-260`
- Modify: `src/services/httpApi.ts:366-387`
- Modify: `src/services/mockApi.ts:485-503`
- Modify: `src/pages/AgentPage.tsx:55-138, 222-251`
- Modify: `tests/agent-workflow.spec.ts`

**Interfaces:**
- Produces: `api.resumeAgentRun({ user_id, agent_run_id })`。
- Consumes: `running` 和 `interrupted` run 状态。
- Produces: 现有“本次请求”区域中的“执行中”“任务中断”“继续任务”“恢复中”。

- [ ] **Step 1: 写手动恢复失败测试**

在 `tests/agent-workflow.spec.ts` 增加：

```typescript
test("manually resumes an interrupted run exactly once", async ({ page }) => {
  let status: "interrupted" | "completed" = "interrupted";
  let resumeCalls = 0;
  await page.route("**/api/agent/runs?*", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        data: [{
          agent_run_id: "run-interrupted",
          user_id: "demo-user-945",
          status,
          started_at: "2026-07-11T09:00:00Z",
          updated_at: "2026-07-11T09:00:01Z",
          completed_at: status === "completed" ? "2026-07-11T09:00:02Z" : null,
          duration_ms: 1000,
          degraded: false,
          input_tokens: 0,
          output_tokens: 0,
          logical_generations: 0,
          http_attempts: 0,
          resume_count: status === "completed" ? 1 : 0,
        }],
        error: null,
      }),
    })
  );
  await page.route("**/api/agent/runs/run-interrupted/resume", async (route) => {
    resumeCalls += 1;
    await new Promise((resolve) => setTimeout(resolve, 300));
    status = "completed";
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        data: {
          message_id: "msg-agent-run-interrupted",
          user_id: "demo-user-945",
          role: "agent",
          content: "恢复后的回复",
          locale: "zh-CN",
          created_at: "2026-07-11T09:00:02Z",
        },
        error: null,
      }),
    });
  });

  await page.goto("/agent");
  const requestStatus = page.getByRole("status").filter({ hasText: "本次请求" });
  const resume = page.getByRole("button", { name: "继续任务" });
  await expect(requestStatus).toContainText("任务中断");
  const click = resume.click();
  await expect(page.getByRole("button", { name: "恢复中" })).toBeDisabled();
  await click;
  await expect(page.getByText("恢复后的回复")).toBeVisible();
  await expect(requestStatus).toContainText("已完成");
  expect(resumeCalls).toBe(1);
});
```

- [ ] **Step 2: 写 running 轮询失败测试**

同文件新增：

```typescript
test("polls a running request until completion and restores only its new draft", async ({ page }) => {
  let runReads = 0;
  await page.route("**/api/agent/runs?*", (route) => {
    runReads += 1;
    const completed = runReads >= 2;
    return route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        data: [{
          agent_run_id: "run-polling",
          user_id: "demo-user-945",
          status: completed ? "completed" : "running",
          started_at: "2026-07-11T09:00:00Z",
          updated_at: "2026-07-11T09:00:02Z",
          completed_at: completed ? "2026-07-11T09:00:02Z" : null,
          duration_ms: completed ? 2000 : 0,
          degraded: false,
          input_tokens: 0,
          output_tokens: 0,
          logical_generations: completed ? 1 : 0,
          http_attempts: 0,
          resume_count: 0,
        }],
        error: null,
      }),
    });
  });
  await page.route("**/api/agent/messages?*", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        data: runReads >= 2 ? [{
          message_id: "msg-agent-run-polling",
          user_id: "demo-user-945",
          role: "agent",
          content: "轮询完成",
          locale: "zh-CN",
          record_draft: {
            type: "workout_log",
            requires_confirmation: true,
            payload: { exercise_name: "深蹲", sets: 4, reps: 8 },
          },
          created_at: "2026-07-11T09:00:02Z",
        }] : [],
        error: null,
      }),
    })
  );

  await page.goto("/agent");
  const requestStatus = page.getByRole("status").filter({ hasText: "本次请求" });
  await expect(requestStatus).toContainText("执行中");
  await expect(requestStatus).toContainText("已完成", { timeout: 5000 });
  await expect(page.getByText("轮询完成")).toBeVisible();
  await expect(page.getByRole("heading", { name: "确认智能教练草稿" })).toBeVisible();
  const completedReadCount = runReads;
  await page.waitForTimeout(2300);
  expect(runReads).toBe(completedReadCount);
});
```

再增加恢复错误测试：

```typescript
test("shows a resume error and moves a missing checkpoint to retry", async ({ page }) => {
  let status: "interrupted" | "failed" = "interrupted";
  await page.route("**/api/agent/runs?*", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        data: [{
          agent_run_id: "run-resume-error",
          user_id: "demo-user-945",
          status,
          started_at: "2026-07-11T09:00:00Z",
          updated_at: "2026-07-11T09:00:01Z",
          duration_ms: 0,
          degraded: false,
          input_tokens: 0,
          output_tokens: 0,
          logical_generations: 0,
          http_attempts: 0,
          resume_count: 0,
        }],
        error: null,
      }),
    })
  );
  await page.route("**/api/agent/runs/run-resume-error/resume", (route) => {
    status = "failed";
    return route.fulfill({
      status: 409,
      contentType: "application/json",
      body: JSON.stringify({
        data: null,
        error: {
          code: "AGENT_CHECKPOINT_MISSING",
          message: "Agent checkpoint is missing.",
          details: { agent_run_id: "run-resume-error" },
        },
      }),
    });
  });

  await page.goto("/agent");
  await page.getByRole("button", { name: "继续任务" }).click();

  await expect(page.getByText("Agent checkpoint is missing.")).toBeVisible();
  await expect(page.getByRole("button", { name: "重试此请求" })).toBeVisible();
});
```

- [ ] **Step 3: 运行 Playwright 并确认 RED**

```powershell
npx playwright test tests/agent-workflow.spec.ts --config=playwright.http.config.ts
```

Expected: FAIL，因为类型、adapter 和页面恢复状态尚不存在。

- [ ] **Step 4: 扩展前端类型和 adapter**

```typescript
export type AgentRun = {
  agent_run_id: string;
  user_id: string;
  status: "running" | "interrupted" | "completed" | "failed";
  started_at: string;
  updated_at?: string | null;
  completed_at?: string | null;
  duration_ms: number;
  provider?: string;
  model?: string;
  intent?: string;
  draft_type?: string;
  degraded: boolean;
  degraded_reason?: string;
  error_code?: string;
  input_tokens: number;
  output_tokens: number;
  logical_generations: number;
  http_attempts: number;
  retry_of_agent_run_id?: string;
  resume_count: number;
};
```

HTTP adapter：

```typescript
async resumeAgentRun(input: { user_id: string; agent_run_id: string }): Promise<ApiResponse<AgentMessage>> {
  return post<AgentMessage>(`/api/agent/runs/${input.agent_run_id}/resume`, {
    user_id: input.user_id
  });
}
```

Mock adapter 使用相同签名，验证 demo 用户后返回 `NOT_FOUND`，不得创建默认中断 run。

- [ ] **Step 5: 实现页面恢复和轮询**

1. 增加 `isResuming` state。
2. `loadMessages()` 返回加载到的数组；普通初始化不从历史消息恢复草稿。
3. `loadLatestRun()` 返回最新 run。
4. 当最新状态为 `running` 时用 effect 每 2 秒读取一次；离开 running 后停止，刷新 messages/today。只有这次状态转换到 completed 时，才把新加载的最后一条 Agent 消息中的 `record_draft` 放入确认区。
5. `resumeLatestRun()` 调 `api.resumeAgentRun()`；成功后设置响应草稿、刷新消息/today/run，并在消息列表缺少响应消息时补入一次；失败使用现有 notice 并刷新 run。
6. 状态优先级固定为本地 `isSending/isRetrying/isResuming`，然后远端 `running/interrupted/failed/completed`。
7. `interrupted` 在现有 `button-row` 渲染“继续任务”；恢复时显示“恢复中”并禁用。
8. 不修改 CSS 文件或 class 名。

`resumeLatestRun()` 的核心调用固定为：

```typescript
const response = await api.resumeAgentRun({
  user_id: DEMO_USER_ID,
  agent_run_id: latestRun.agent_run_id
});
```

- [ ] **Step 6: 验证 GREEN 和构建**

```powershell
npx playwright test tests/agent-workflow.spec.ts --config=playwright.http.config.ts
npm run build
```

Expected: PASS，现有 Chat/retry 测试保持通过。

- [ ] **Step 7: 提交 Task 5**

```powershell
git add src/types/domain.ts src/services/httpApi.ts src/services/mockApi.ts src/pages/AgentPage.tsx tests/agent-workflow.spec.ts
git commit -m "feat: add manual agent run recovery ui"
```

---

### Task 6: 严格跨层验收与阶段收口

**Files:**
- Verify only: no production file changes expected。

**Interfaces:**
- Verifies: 后端、Mongo checkpoint、真实 HTTP、Lv4 回归和前端视觉冻结。

- [ ] **Step 1: 运行全部后端测试**

```powershell
python -m pytest backend/tests -q
```

Expected: 全部通过；普通环境只跳过显式外部服务测试。

- [ ] **Step 2: 运行真实 Mongo checkpoint 恢复测试**

确认本机 Mongo 可用后执行：

```powershell
$env:945_RUN_MONGO_INTEGRATION_TESTS="1"
python -m pytest backend/tests/test_agent_graph.py -k "mongo_checkpoint_resumes_after_graph_and_saver_recreation" -q
Remove-Item Env:945_RUN_MONGO_INTEGRATION_TESTS
```

Expected: PASS，专用 `945_agent_resume_checkpoint_test` 数据库已清理。

- [ ] **Step 3: 运行构建和真实 HTTP QA**

```powershell
npm run build
npm run qa:http
```

Expected: PASS，Chat、retry、resume 前端流程均通过。

- [ ] **Step 4: 运行 Mongo HTTP QA**

```powershell
npm run qa:mongo
```

Expected: PASS，只使用 QA 专用数据库。

- [ ] **Step 5: 运行离线 Lv4 回归**

```powershell
npm run qa:lv4
```

Expected: PASS；不得增加 `--include-deepseek`，结构化写入计数保持 `0`。

- [ ] **Step 6: 核对范围和工作区卫生**

```powershell
git diff df58c19..HEAD --name-only
git diff --check df58c19..HEAD
git status --short
```

Expected:

- 只出现本计划列出的生产文件、测试文件和实施计划文档。
- 不出现 CSS、图标、导航或其他页面视觉文件。
- `.venv/` 和 `output/` 仍为未跟踪本地产物。

- [ ] **Step 7: 汇总验收证据**

最终报告必须列出：

- 后端测试通过/跳过数量。
- Mongo checkpoint 重建恢复测试结果。
- `build`、`qa:http`、`qa:mongo`、离线 `qa:lv4` 结果。
- 恢复前后同一 run/thread 的测试证据。
- 重复消息数和结构化写入数均为 `0` 的测试证据。
- 前端视觉文件改动数为 `0`。
