# LangSmith Observability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不记录用户训练、饮食正文或模型推理内容的前提下，为 945 Agent 提供可选的 LangSmith 运行追踪。

**Architecture:** `Settings` 读取 LangSmith 开关和凭据；启动时仅在显式启用且存在 API Key 时设置 LangSmith SDK 环境变量。LangGraph 自动追踪图节点，run metadata 只包含本地 `request_id`、用户匿名标识、locale 和 provider，不传递消息正文。

**Tech Stack:** FastAPI, Pydantic Settings, LangGraph 0.6.11, LangSmith SDK.

## Global Constraints

- 默认关闭，未配置 LangSmith Key 时不影响 deterministic、OpenAI、demo 或 Mongo 模式。
- 只使用 `request_id`、匿名用户标识、locale、provider 等元数据；禁止发送用户消息、训练/饮食记录、profile、RAG 原文、模型推理过程。
- 不改前端视觉、页面或 API 响应格式。

---

### Task 1: 配置与安全追踪初始化

**Files:**
- Modify: `backend/app/core/config.py`
- Create: `backend/app/observability/langsmith.py`
- Test: `backend/tests/test_langsmith_observability.py`

**Interfaces:**
- Produces: `configure_langsmith_tracing(settings: Settings) -> bool`。
- Consumes: `Settings.langsmith_tracing`, `Settings.langsmith_api_key`, `Settings.langsmith_project`。

- [x] **Step 1: Write failing tests**

```python
def test_enabled_langsmith_sets_hidden_input_and_output_environment(monkeypatch):
    enabled = configure_langsmith_tracing(Settings(langsmith_tracing=True, langsmith_api_key="key"))
    assert enabled is True
    assert os.environ["LANGSMITH_HIDE_INPUTS"] == "true"
    assert os.environ["LANGSMITH_HIDE_OUTPUTS"] == "true"
```

- [x] **Step 2: Run the new test and verify import failure**

Run: `D:\Codex\945\.venv\Scripts\python.exe -m pytest backend/tests/test_langsmith_observability.py -q`

- [x] **Step 3: Add Settings fields and minimal initializer**

```python
if not settings.langsmith_tracing or settings.langsmith_api_key is None:
    return False
os.environ.update({"LANGSMITH_TRACING": "true", "LANGSMITH_HIDE_INPUTS": "true", "LANGSMITH_HIDE_OUTPUTS": "true"})
return True
```

- [x] **Step 4: Run targeted tests**

Run: `D:\Codex\945\.venv\Scripts\python.exe -m pytest backend/tests/test_langsmith_observability.py -q`

### Task 2: 在 Agent 图运行时应用配置并写中文说明

**Files:**
- Modify: `backend/app/agents/graph.py`
- Modify: `backend/README.md`
- Test: `backend/tests/test_agent_graph.py`

**Interfaces:**
- Consumes: `configure_langsmith_tracing(get_settings())`。
- Preserves: `/api/agent/chat` 响应和 `RecordDraft` 确认边界。

- [x] **Step 1: Write failing graph integration test**

```python
def test_agent_graph_initialization_configures_langsmith(monkeypatch):
    monkeypatch.setattr(graph, "configure_langsmith_tracing", lambda _: True)
    graph.get_agent_graph()
    assert configured == [True]
```

- [x] **Step 2: Run it and verify it fails**

Run: `D:\Codex\945\.venv\Scripts\python.exe -m pytest backend/tests/test_agent_graph.py -q`

- [x] **Step 3: Call the initializer before compiling the graph and document the three required variables**

```text
945_LANGSMITH_TRACING=true
LANGSMITH_API_KEY=...
LANGSMITH_PROJECT=945
```

- [x] **Step 4: Verify the backend, eval suite and Mongo checkpoint tests**

Run: `D:\Codex\945\.venv\Scripts\python.exe -m pytest backend/tests -q`

Run: `D:\Codex\945\.venv\Scripts\python.exe -m backend.evals.run_agent_eval`
