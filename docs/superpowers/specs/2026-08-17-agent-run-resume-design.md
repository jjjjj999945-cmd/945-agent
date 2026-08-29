# Agent 同一任务中断恢复设计

## 1. 背景

945 当前通过同步 `POST /api/agent/chat` 执行 LangGraph。每次请求都会生成新的 `agent_run_id`，该 ID 同时作为 LangGraph `thread_id`。Graph 已配置 `MemorySaver` 或 `MongoDBSaver`，但服务只在执行成功或已知模型错误后保存 `AgentRun`，因此进程中断时可能只留下 checkpoint，没有可供前端识别和恢复的运行记录。

现有 `POST /api/agent/runs/{agent_run_id}/retry` 会重新提交原输入并创建新 run。它适合已知模型失败，但不属于同一 checkpoint 的恢复。

本阶段采用“原 run、原 thread 原地恢复”：用户看到任务中断后手动点击“继续任务”，系统从最近的安全 checkpoint 继续。

## 2. 目标

- 在 Graph 执行前持久化运行状态，使进程中断后仍能识别原任务。
- 使用相同 `agent_run_id/thread_id` 从 LangGraph checkpoint 继续。
- 由用户手动触发恢复，不在页面加载时自动产生模型调用或费用。
- 防止重复恢复、重复消息和跨用户恢复。
- 在 Mongo 模式下支持后端进程重启后的恢复。
- 保留现有模型错误重试流程以及“模型只生成草稿，用户确认后结构化 API 写入”的安全边界。
- 只调整 Agent 页现有状态区域的内容和交互，不改变前端视觉系统。

## 3. 非目标

- 不实现用户主动暂停正在运行的 DeepSeek HTTP 请求。
- 不实现流式输出、SSE、WebSocket 或后台任务队列。
- 不实现多 Uvicorn worker 或多实例之间的分布式锁。
- 不引入 Redis、任务租约、心跳或自动恢复。
- 不改变 Prompt、工具白名单、训练/饮食/计划写入流程。
- 不修改颜色、字体、图标、导航、玻璃效果、组件视觉样式或整体设计语言。
- 不运行付费 DeepSeek 验收；恢复逻辑使用 deterministic/fake Provider 验证。

## 4. 运行状态机

`AgentRun.status` 扩展为：

- `running`：当前进程正在执行该 run。
- `interrupted`：执行未形成终态，并且当前进程没有继续执行该 run。
- `completed`：结果和对应消息已完成幂等保存。
- `failed`：发生已知模型错误，或者 checkpoint 缺失，不能继续原任务。

允许的状态流转：

```text
running -> completed
running -> failed
running -> interrupted
interrupted -> running
```

恢复后的 `running` 仍只能进入 `completed`、`failed` 或 `interrupted`。

`completed` 和 `failed` 不允许调用恢复接口。`failed` 保留现有 retry 能力；retry 仍会创建一个新 run，并设置 `retry_of_agent_run_id`。

## 5. 数据模型

`AgentRun` 增加或调整以下字段：

- `status`: `running | interrupted | completed | failed`。
- `completed_at`: 改为可选；只有终态 run 才有值。
- `updated_at`: 每次状态转换时更新，用于列表排序和前端获取最新 run。
- `resume_count`: 成功进入恢复执行的次数，默认 `0`。
- `request_input`: 原始消息、语言和上下文，仅供恢复收口和故障处理使用。

`duration_ms` 只累计当前进程实际完成并记录下来的执行时长。恢复开始时保留已有值，恢复结束时加上本次执行时长；进程被直接终止而来不及记录的时间不做估算。运行中和中断 run 不参与平均耗时指标。

`request_input`、现有 `retry_input` 和 `trace_steps` 不通过 run 列表接口暴露。

为保证恢复幂等，新创建的消息使用基于 run ID 的确定性 ID：

```text
msg-user-{agent_run_id}
msg-agent-{agent_run_id}
```

Demo store 与 Mongo repository 的消息和 run 保存都按 ID 执行 upsert。旧消息和旧 run 无需迁移；新增字段使用兼容默认值读取历史文档。

## 6. 当前进程活动集合

后端服务维护仅限当前进程的活动 run ID 集合：

- `/chat` 或 `/resume` 在第一次 `await` 前将 run 加入活动集合并保存为 `running`。
- 执行进入任一终态或中断态后，从活动集合移除。
- 同一进程收到重复恢复请求时，如果 ID 已在活动集合中，返回 `409 AGENT_RUN_ACTIVE`。

当前 Dockerfile 使用单 Uvicorn worker，因此该集合足以覆盖本阶段的并发防重。多 worker 场景需要 Redis 或数据库原子租约，留到 Lv5 基础设施阶段。

## 7. 重启后的孤立 run 识别

`GET /api/agent/runs` 通过 Agent service 获取 run，而不是直接读取 store。读取时执行一次收口：

- `status != running`：不处理。
- `status == running` 且 ID 位于当前进程活动集合：仍返回 `running`。
- `status == running` 且 ID 不在当前进程活动集合：持久化为 `interrupted` 后返回。

后端进程重启后活动集合为空，因此 Mongo 中遗留的 `running` run 会在用户打开 Agent 页并读取列表时转换为 `interrupted`。Demo store 不承诺跨进程恢复，因为其数据和 MemorySaver 都只存在于内存中。

## 8. Chat 执行流程

`POST /api/agent/chat` 的执行顺序调整为：

1. 验证用户并执行现有使用额度限制。
2. 创建 run ID，将 ID 加入活动集合。
3. 保存包含 `request_input` 的 `running` run。
4. 使用该 ID 作为 `thread_id` 调用 LangGraph。
5. Graph 成功后，以确定性消息 ID upsert 用户消息和 Agent 消息，再将原 run 更新为 `completed`。
6. 捕获已知 `LLMError` 时，将原 run 更新为 `failed`，保留 `retry_input`，继续返回现有模型错误响应。
7. 捕获 `asyncio.CancelledError` 或非 `LLMError` 执行异常时，将原 run 更新为 `interrupted`，随后继续抛出原异常。
8. 在 `finally` 中从活动集合移除 run ID。

如果操作系统直接终止进程，步骤 7 无法执行；步骤 7 的状态由下一次 run 列表读取按第 7 节收口。

## 9. 恢复接口

新增：

```http
POST /api/agent/runs/{agent_run_id}/resume
Content-Type: application/json

{
  "user_id": "..."
}
```

成功响应沿用 `ApiResponse<AgentMessage>`，便于前端继续处理 `record_draft`。

执行顺序：

1. 使用现有鉴权逻辑验证请求中的 `user_id`。
2. 只在该用户的 run 列表中查找 ID；其他用户的 run 返回 `404 NOT_FOUND`。
3. 将不属于当前活动集合的孤立 `running` run 先收口为 `interrupted`。
4. 仅允许 `interrupted` run 进入恢复。
5. 在第一次 `await` 前将 ID 加入活动集合、状态改为 `running` 并增加 `resume_count`。
6. 使用相同 `thread_id` 读取 LangGraph state snapshot。
7. snapshot 已包含最终 `result` 时，不再次调用模型，直接执行消息和 run 的幂等收口。
8. snapshot 有待执行节点时，调用 `graph.ainvoke(None, config=原 thread 配置)` 从 checkpoint 继续。
9. 完成、模型失败、中断和活动集合清理使用与 Chat 相同的收口函数。

LangGraph 以节点为 checkpoint 边界。若中断发生在模型节点内部，该节点会整体重新执行，因此可能再次产生一次 Provider 调用；系统不会声称能够从 DeepSeek HTTP 请求内部继续。

## 10. 恢复错误

- `409 AGENT_RUN_ACTIVE`：同一 run 当前正在本进程执行。
- `409 AGENT_RUN_NOT_RESUMABLE`：run 已是 `completed` 或 `failed`。
- `409 AGENT_CHECKPOINT_MISSING`：没有可用 checkpoint，或 checkpoint 既无待执行节点也无最终结果。
- `404 NOT_FOUND`：当前用户不存在，或该 run 不属于当前用户。

checkpoint 缺失时，run 转为 `failed`，`error_code` 设为 `AGENT_CHECKPOINT_MISSING`，并从 `request_input` 填充 `retry_input`。系统不在恢复接口中静默从头执行；用户可以明确点击现有“重试此请求”创建新 run。

恢复期间的已知 `LLMError` 转为 `failed`。恢复期间的取消或非模型执行异常重新转为 `interrupted`。

## 11. 幂等与写入边界

- 活动集合防止同一进程中的并发恢复。
- 确定性消息 ID 和 upsert 防止“Graph 已完成、消息已保存、run 尚未更新”时再次恢复产生重复消息。
- Graph checkpoint 已有最终 `result` 时直接收口，不再次执行节点。
- 恢复只保存 Agent 对话消息、run 和 checkpoint，不调用训练、饮食、计划或身体数据写入 API。
- `RecordDraft` 仍只随 Agent 消息返回；必须由用户确认后才能调用结构化写入 API。

## 12. 可观察性

`AgentRunMetrics` 增加：

- `running_runs`
- `interrupted_runs`

`total_runs` 仍包含全部状态。`success_rate` 使用终态 run 计算：

```text
completed / (completed + failed)
```

没有终态 run 时为 `0`。平均耗时只统计 `completed` 和 `failed`，避免正在运行或中断的任务扭曲延迟指标。现有 token、逻辑生成次数、HTTP 尝试次数和错误码聚合保持不变。

## 13. 前端交互

只修改 Agent 页现有“本次请求”状态区域：

- `running`：显示“执行中”。页面每 2 秒刷新 run；进入终态后停止轮询并刷新消息和今日数据。若轮询发现刚刚完成的最新 Agent 消息包含 `record_draft`，本次状态转换同时把该草稿放入现有草稿确认区；普通页面初始化不自动恢复历史草稿。
- `interrupted`：显示“任务中断”和“继续任务”按钮。
- 点击恢复后：按钮显示“恢复中”并禁用；调用恢复接口。
- 成功：使用响应中的 `record_draft` 更新草稿，并刷新消息、今日数据和 run。
- 失败：使用现有 notice 区域显示 API 错误，并刷新 run 状态。
- `failed`：保留现有“需要重试”和“重试此请求”。
- `completed`：保持现有“已完成”。

HTTP adapter 和 Mock adapter 同时增加 `resumeAgentRun({ user_id, agent_run_id })`。Mock 默认数据不制造中断 run，因此默认页面外观和使用路径不改变。

本阶段不新增 CSS 视觉规则；复用现有 `business-panel`、`button-row`、按钮和状态文字样式。

## 14. 测试设计

实现采用测试先行，每项行为先观察测试因缺少功能而失败，再写最小实现。

后端重点测试：

- Chat 在 Graph 前保存 `running`，结束后原 ID 更新为 `completed`。
- 非模型异常形成 `interrupted`，不保存结构化记录。
- 同一 thread 的失败节点恢复后完成，已成功节点不重新执行。
- Graph 已有最终结果时恢复不再次调用 Provider。
- 后端“重启”后孤立 `running` run 转为 `interrupted`。
- 恢复前后 run ID 不变，`resume_count` 增加。
- checkpoint 缺失返回指定错误并转为可 retry 的 `failed`。
- 重复恢复、终态恢复和跨用户恢复被拒绝。
- 多次收口只产生一条用户消息和一条 Agent 消息。
- 指标正确区分四种状态。
- MongoSaver 重新创建后仍能读取原 checkpoint 并完成恢复。

前端重点测试：

- `interrupted` 显示“继续任务”。
- 点击只发送一次恢复请求，期间按钮禁用。
- 成功后显示 Agent 回复或草稿，并变为“已完成”。
- `running` 状态轮询，终态后停止。
- 恢复错误使用现有提示区域展示。

## 15. 验收命令

先运行直接相关测试，再执行严格验收：

```powershell
python -m pytest backend/tests -q
npm run build
npm run qa:http
npm run qa:mongo
npm run qa:lv4
```

`npm run qa:lv4` 使用默认离线模式，不增加 `--include-deepseek`。

完成标准：

- 所有命令通过。
- Mongo 模式下证明 checkpoint 跨 saver/进程模拟后可恢复。
- 恢复前后 `agent_run_id/thread_id` 相同。
- 重复消息数为 `0`。
- 训练、饮食和计划结构化写入数为 `0`。
- 未修改前端视觉系统文件或视觉规则。

## 16. 预计修改范围

- `backend/app/models/domain.py`
- `backend/app/agents/graph.py`
- `backend/app/services/agent_service.py`
- `backend/app/services/agent_observability.py`
- `backend/app/services/demo_store.py`
- `backend/app/api/routes_agent.py`
- `src/types/domain.ts`
- `src/services/httpApi.ts`
- `src/services/mockApi.ts`
- `src/pages/AgentPage.tsx`
- 与上述行为直接对应的后端和 Playwright 测试

除非测试证明当前边界无法实现，否则不新增依赖、不拆分无关模块、不修改其他页面。
