# Agent 分布式任务 Mongo 租约设计

## 1. 背景

945 已支持同一 Agent 任务中断后由用户点击“继续任务”，并使用相同
`agent_run_id/thread_id` 从 LangGraph checkpoint 恢复。当前实现使用
进程内 `_active_agent_run_ids` 判断任务是否仍在执行：

- 当前进程能阻止同一 run 被重复恢复。
- 后端重启后，遗留的 `running` run 会被识别为 `interrupted`。
- 当多个 Uvicorn worker 或多个后端实例共享 Mongo 时，一个实例无法看到
  另一个实例的进程内集合，会把仍在正常执行的任务误判为中断。
- AgentRun、消息和终态通过普通 upsert 保存，没有数据库级所有权校验；
  旧 Worker 晚返回时可能覆盖新 Worker 的结果。

本阶段是 Lv5 的第一个子阶段，只把 Agent 运行所有权升级为 Mongo 原子租约。
任务过期后仍由用户手动恢复，不引入自动接管。

## 2. 目标

- Mongo 模式下允许多个后端 Worker 共享同一组 Agent run。
- 同一时刻，一个 run 最多只有一个有效执行者。
- 有效租约归其他 Worker 所有时，任何实例都不能把 run 误判为中断。
- 租约过期后将 run 标记为 `interrupted`，等待用户点击“继续任务”。
- 新 Worker 获得更高版本租约后，旧 Worker 不能发布消息、终态或可接受的
  checkpoint 进度。
- 保留原 run、原 thread 和最近安全 checkpoint 的恢复语义。
- Demo store 保持相同的状态机和接口语义，默认离线开发不依赖 Mongo。
- 保留“模型生成草稿 -> 用户确认 -> 结构化 API 写入”的产品安全边界。
- 不修改现有前端视觉系统。

## 3. 非目标

- 不引入 Redis、Celery、消息队列或任务调度平台。
- 不实现后台自动接管、自动恢复或定时扫描服务。
- 不在本阶段调整生产 Compose 的 Worker 数量。
- 不实现分布式限流、分布式登录会话或跨服务鉴权。
- 不实现 Agent 主动暂停、流式输出、SSE 或 WebSocket。
- 不保证模型 HTTP 请求内部断点续传；中断发生在模型节点内部时，该节点仍可能
  在恢复后重新执行。
- 不改变 Prompt、工具白名单、草稿类型、训练/饮食/计划写入流程。
- 不改变颜色、字体、图标、导航、玻璃效果、组件视觉样式或整体设计语言。
- 不运行 DeepSeek 或其他付费模型验收。

## 4. 核心不变量

实现必须始终满足以下规则：

1. Mongo 中的 AgentRun 是运行所有权和终态的唯一权威。
2. 所有运行期写入必须携带 `user_id + agent_run_id + lease_owner +
   lease_version`。
3. 运行期写入只在 `status == running` 且租约未过期时成功。
4. `lease_version` 只递增，不回退，不复用。
5. 未成功取得租约的请求不能启动 Graph。
6. 丢失租约的 Worker 立即停止，不把租约丢失记录成业务失败。
7. 只有成功完成带租约条件的终态转换后，Worker 才能发布对话消息。
8. 过期只产生 `interrupted`，不会触发新的模型调用。
9. `completed` 和 `failed` 不允许被租约收口或恢复逻辑覆盖。

## 5. 架构与组件边界

### 5.1 Agent service

`backend/app/services/agent_service.py` 继续负责编排：

- 创建 run 或恢复 run。
- 建立一次执行对应的 `AgentLeaseSession`。
- 启动心跳并调用 LangGraph。
- 根据 Graph 结果调用带租约保护的完成、失败或中断操作。
- 租约丢失时取消当前 Graph 任务并停止收口。

Agent service 不再根据 `_active_agent_run_ids` 决定数据库中的运行状态。
进程内集合可以删除；如果保留，它只能用于本进程任务取消和资源清理，不能作为
分布式所有权依据。

### 5.2 Store facade

`backend/app/services/demo_store.py` 继续作为当前 service 使用的存储入口，
但 AgentRun 生命周期改为语义明确的操作，不再通过通用
`save_agent_run()` 完成并发状态转换。

建议接口职责如下，具体函数名可在实施计划中按现有命名规范确定：

- 原子创建 run 并取得首个租约。
- 原子取得 `interrupted` run 的新租约。
- 校验和续租。
- 带租约保护地完成、失败或中断 run。
- 原子收口已过期的 `running` run。
- 读取用户 run 和单个 run。

Demo 和 Mongo 实现必须通过同一组 service 级契约测试。

### 5.3 RepositoryStore 与 MongoRepository

`backend/app/services/repository_store.py` 负责 AgentRun 领域操作；
`backend/app/repositories/mongo.py` 提供所需的
`find_one_and_update`、条件更新和服务端时间表达式。

通用 `upsert_model()` 保留给不需要并发控制的数据，但 AgentRun 的运行期
状态转换不能再调用它。

### 5.4 AgentLeaseSession

一次创建或恢复尝试对应一个内存中的租约会话，至少保存：

- `user_id`
- `agent_run_id`
- `lease_owner`
- `lease_version`
- 心跳任务
- 租约丢失事件

`lease_owner` 每次执行尝试都生成新值，可由进程标识和随机执行 ID 组合；
不能只使用固定 Worker 名称，否则同一 Worker 内的并发请求无法区分。

### 5.5 LangGraph checkpoint 边界

Graph 执行配置携带 run ID、租约所有者和租约版本，但这些信息不进入 Prompt、
模型输入或 LangSmith 的用户内容字段。

checkpoint 写入采用两层保护：

1. Graph 节点在执行前和返回结果前校验当前租约；模型调用期间丢失租约时，
   节点结果不能作为有效输出返回。
2. checkpoint metadata 标记 `agent_run_id` 和 `lease_version`；
   checkpoint 写入前再次校验租约。

用户恢复时，在成功取得新租约后固定本次恢复使用的起始 checkpoint ID。
后续即使旧 Worker 晚写入低版本 checkpoint，新 Worker 也不会切换到该写入。
AgentRun 终态和可见消息仍是最终权威；没有通过终态租约条件的 Graph 结果不能
作为用户可见结果发布。

## 6. 数据模型

`AgentRun` 增加以下内部字段：

- `lease_owner: str | None`
- `lease_version: int`，历史数据默认 `0`，新 run 首次租约为 `1`
- `lease_expires_at: datetime | None`
- `last_heartbeat_at: datetime | None`
- `resume_checkpoint_id: str | None`，恢复取得租约后固定的起始 checkpoint
- `messages_persisted: bool`，终态消息是否已完成幂等收口

租约时间使用 BSON datetime 保存，不使用字符串比较。现有
`started_at/updated_at/completed_at` 暂不做无关迁移。

公开的 run 列表继续排除 `request_input`、`retry_input` 和
`trace_steps`，并额外排除全部租约字段、`resume_checkpoint_id` 与
`messages_persisted`。前端 TypeScript 类型不增加这些内部字段。

历史文档兼容规则：

- `completed` 和 `failed` 文档缺少租约字段时按原终态读取。
- `interrupted` 文档缺少租约字段时可以正常手动恢复，首次恢复将版本从
  `0` 增加到 `1`。
- `running` 文档缺少有效租约时，在首次列表、详情或恢复检查时原子转为
  `interrupted`。
- 不执行全库批量迁移。

## 7. 租约时间与配置

默认参数：

- `945_AGENT_LEASE_TTL_SECONDS=60`
- `945_AGENT_LEASE_HEARTBEAT_SECONDS=15`

配置校验要求心跳间隔大于零，并且不超过 TTL 的三分之一。Mongo 模式使用
Mongo 服务端 `$$NOW` 完成到期判断、心跳时间和新到期时间计算，避免不同
Worker 的本机时钟偏差。

Demo 模式使用可注入 UTC clock 和进程内锁实现相同语义，便于无等待测试。

心跳是当前运行任务的一部分，不是扫描器，也不会发现或接管其他 Worker 的任务。

## 8. 原子存储契约

### 8.1 创建

创建使用唯一 `agent_run_id` 原子插入：

- `status = running`
- `lease_owner = 当前执行尝试`
- `lease_version = 1`
- `last_heartbeat_at = $$NOW`
- `lease_expires_at = $$NOW + TTL`

插入成功后才能启动 Graph。重复 ID 不覆盖原文档。

### 8.2 获取恢复租约

恢复使用单次 `find_one_and_update`：

- 条件包含 `user_id`、`agent_run_id` 和 `status = interrupted`。
- 设置新的 `lease_owner`。
- `lease_version` 原子加一。
- 状态改为 `running`，清除旧终态错误字段。
- 使用服务端时间设置心跳和到期时间。
- `resume_count` 原子加一。

只有拿到更新后文档的请求可以启动恢复。并发请求中其余请求返回最新状态，不启动
第二次 Graph。

### 8.3 续租

续租条件必须包含：

```text
user_id
agent_run_id
status == running
lease_owner == 当前 owner
lease_version == 当前 version
lease_expires_at > $$NOW
```

成功时同时更新 `last_heartbeat_at` 和 `lease_expires_at`。匹配数为零即
租约丢失，不能通过普通 save 重新获得所有权。

### 8.4 运行期校验

Graph 节点边界、checkpoint 写入和终态转换使用同一租约条件。只读取
`lease_owner` 后在应用层比较不构成有效校验。

### 8.5 过期收口

列表或详情读取前执行条件更新：

```text
status == running
AND (lease_expires_at <= $$NOW OR lease metadata missing)
-> status = interrupted
```

更新同时清除 `lease_owner` 和 `lease_expires_at`，保留
`lease_version`、请求输入、checkpoint 和运行指标。条件竞争失败时重新读取
最新文档，不能覆盖终态或新租约。

### 8.6 状态转换后的租约字段

`completed`、`failed` 和由当前 Worker 主动写入的 `interrupted` 都必须通过
当前租约条件更新。转换成功后清除 `lease_owner` 和 `lease_expires_at`，保留
`lease_version` 与 `last_heartbeat_at` 作为 fencing 和诊断依据。任何后续幂等
收口只能按 `user_id + agent_run_id + status + lease_version` 更新，不能重新获得
运行权。

## 9. 新任务执行流程

1. 完成现有鉴权和使用限制检查。
2. 生成 run ID 与本次 `lease_owner`。
3. 原子创建 `running` run 和版本 `1` 租约。
4. 启动心跳任务。
5. 使用 run ID 作为 LangGraph `thread_id`，并把租约 token 放入运行配置。
6. Graph 节点和 checkpoint 写入执行租约校验。
7. Graph 返回后执行带租约条件的终态转换。
8. 停止心跳并清理当前执行任务。

未成功完成步骤 3 时，不得执行步骤 4 以后内容。

## 10. 完成、失败与消息发布

### 10.1 正常完成

为避免旧 Worker 先写入用户可见消息，完成顺序调整为：

1. 使用当前租约原子把 run 从 `running` 转为 `completed`，保存指标和
   `completed_at`，并设置 `messages_persisted = false`。
2. 只有步骤 1 成功的 Worker 才能使用确定性消息 ID 幂等 upsert 用户消息和
   Agent 消息。
3. 消息保存成功后，按 `completed + lease_version` 条件把该 run 的
   `messages_persisted` 改为 `true`。

如果 Worker 在步骤 1 后崩溃，后续 run 或消息读取会对
`messages_persisted = false` 的已完成 run 进行幂等收口：从
`request_input` 和同一 thread 的最终 checkpoint 重建消息，不重新调用模型。
这保证终态先确定所有权，同时不会永久丢失回复。

### 10.2 已知模型失败

持有有效租约时，现有 `LLMError` 通过条件更新转为 `failed`，保留
`retry_input` 和错误码。失败流程不发布 Agent 回复，现有 retry 仍创建新 run。

### 10.3 非模型异常与取消

持有有效租约时，取消或非模型异常通过条件更新转为 `interrupted`，随后继续
抛出原异常。若条件更新失败，按租约丢失处理，不覆盖数据库最新状态。

## 11. 心跳与租约丢失

心跳作为与 Graph 并行的异步任务运行：

- 续租成功时继续等待下一次心跳。
- Mongo 暂时失败时，只能在当前租约到期前有限重试。
- 在到期前无法确认续租成功时，设置租约丢失事件并取消 Graph 任务。
- Graph、模型或工具调用稍后返回时，节点出口校验和终态条件更新会再次拒绝结果。

租约丢失使用内部 `AgentLeaseLostError` 表示：

- 不写 `failed`。
- 不写 `interrupted`，因为当前 Worker 已不再拥有状态转换权限。
- 不保存用户可见消息。
- API 重新读取并返回 run 的最新状态或对应冲突错误。

## 12. 手动恢复流程

1. 用户读取 run 列表或详情。
2. 后端原子收口该用户已过期的 `running` run。
3. 前端看到 `interrupted`，显示现有“继续任务”按钮。
4. 用户点击后调用现有 resume 接口。
5. 后端只允许当前用户的 `interrupted` run 原子取得新租约。
6. 取得租约后读取并固定最近安全 checkpoint ID。
7. 使用相同 `agent_run_id/thread_id` 和固定 checkpoint 恢复 Graph。
8. 完成、失败、中断和消息发布使用第 10 节相同流程。

读取页面、心跳停止或租约过期都不会自动执行步骤 4 以后内容。

## 13. 并发与错误响应

- 两个恢复请求竞争：一个成功；其余请求重新读取状态。最新状态为 `running`
  时返回 `409 AGENT_RUN_ACTIVE`；如果任务已经迅速进入终态，则返回现有
  `409 AGENT_RUN_NOT_RESUMABLE`，并附带最新 run 状态。
- 有效租约属于其他 Worker：列表保持 `running`，不改状态。
- 终态恢复：继续返回 `409 AGENT_RUN_NOT_RESUMABLE`。
- checkpoint 缺失：当前有效 Worker 将 run 转为
  `failed / AGENT_CHECKPOINT_MISSING`，允许用户使用现有 retry。
- Mongo 暂时不可用：返回现有服务错误边界；不得降级到无租约写入。
- 跨用户访问：条件和查询始终包含 `user_id`，继续返回 `404`，不泄露
  run 是否存在。
- 过期收口与完成竞争：只有一个条件更新成功；失败方重新读取，不能覆盖结果。

## 14. Demo 模式

Demo store 使用进程内锁和租约元数据实现同一组操作：

- 支持创建、续租、过期、手动恢复和版本 fencing。
- 使用注入 clock 直接推进时间，不在测试中真实等待 60 秒。
- 同一进程中的两个独立 service/owner 可以模拟并发竞争。
- 不承诺跨进程持久化；这与 Demo store 的既有边界一致。

Mock 前端和真实 HTTP 模式继续共享相同公开 API 状态，不增加仅 Mongo 才存在的
前端分支。

## 15. API 与前端兼容

现有接口路径保持不变：

- `GET /api/agent/runs`
- `POST /api/agent/chat`
- `POST /api/agent/runs/{agent_run_id}/resume`
- `POST /api/agent/runs/{agent_run_id}/retry`

公开状态仍为 `running | interrupted | completed | failed`。前端继续使用
现有状态文字、“继续任务”按钮和轮询逻辑。

本阶段不新增 CSS，不修改现有页面结构、图标、颜色、字体、导航、卡片或玻璃效果。
允许的前端修改仅限于必要的并发错误处理或响应字段适配；如果后端兼容性允许，
则不修改前端生产组件。

## 16. 测试设计

实现采用测试先行，先增加失败测试，再做最小实现。

### 16.1 Repository 和数据模型

- 首次创建取得版本 `1` 租约。
- 正确 owner/version 可以续租。
- 错误 owner、旧 version、过期租约或非 `running` 状态不能续租或终结。
- 多 owner 并发恢复只有一个成功。
- 过期 `running` 原子转为 `interrupted`。
- `completed` 和 `failed` 不被过期收口覆盖。
- 新版本取得后，旧版本不能完成、失败、中断或发布消息。
- 历史缺少租约字段的四种状态按第 6 节兼容规则读取。
- API 序列化不暴露内部租约字段。

### 16.2 Agent service 与 Graph

- 其他 Worker 持有有效租约时，列表不再误判孤儿 run。
- 心跳失败触发 Graph 取消，且不写业务失败。
- 节点入口、出口和 checkpoint 写入拒绝旧租约。
- 恢复固定起始 checkpoint，不采用旧 Worker 后续低版本写入。
- 终态 CAS 失败时不保存消息。
- 完成后消息写入中断可以从最终 checkpoint 幂等修复，不调用 Provider。
- Demo store 与 Mongo store 通过同一组租约契约测试。

### 16.3 HTTP 集成

```text
创建任务
-> running
-> 模拟租约过期
-> interrupted
-> 用户点击继续任务
-> running
-> completed
```

另外覆盖：

- 双击恢复只启动一次。
- 并发失败返回明确冲突，不产生重复消息。
- 跨用户不能获取或续租。
- run 列表和消息接口不暴露内部租约数据。
- 现有 retry、草稿确认、结构化写入边界保持不变。

### 16.4 双实例 Mongo 验收

使用两个独立 owner/service 实例连接同一测试 Mongo：

1. 同时争抢同一 run，只有一个获得执行权。
2. 第一个 owner 的有效租约存在时，第二个实例读取仍为 `running`。
3. 第一个 owner 停止心跳并过期，读取后状态变为 `interrupted`。
4. 没有用户 resume 请求时，第二个实例不能执行。
5. 用户触发 resume 后，第二个 owner 获得更高版本租约。
6. 第一个 owner 晚返回，无法覆盖第二个 owner 的 checkpoint 选择、消息或终态。

所有并发测试使用 deterministic/fake Provider，不调用 DeepSeek。

## 17. 验收命令

先运行直接相关测试，再执行严格验收：

```powershell
python -m pytest backend/tests -q
npm run build
npm run qa:http
npm run qa:mongo
npm run qa:lv4
```

`npm run qa:lv4` 使用默认离线模式，不运行
`npm run qa:lv4:deepseek`。

完成标准：

- 所有命令通过。
- 同一 run 同时最多有一个有效租约。
- 有效的外部 Worker 不被误判为中断。
- 租约过期不触发自动模型调用。
- 用户手动恢复后沿用同一 `agent_run_id/thread_id`。
- 旧 Worker 不能发布消息、终态或被新执行采用的 checkpoint。
- 重复消息数为 `0`。
- 训练、饮食和计划结构化写入数为 `0`。
- 公共 API 不暴露租约字段。
- 未改变前端视觉系统。

## 18. 预计修改范围

- `backend/app/core/config.py`
- `backend/app/models/domain.py`
- `backend/app/repositories/mongo.py`
- `backend/app/services/repository_store.py`
- `backend/app/services/demo_store.py`
- `backend/app/services/agent_service.py`
- `backend/app/agents/checkpoint.py`
- `backend/app/agents/graph.py`
- `backend/app/api/routes_agent.py`
- 与上述行为直接对应的后端、Mongo 和 HTTP 测试

除非测试证明公开接口无法保持兼容，否则不修改前端生产组件。不新增第三方依赖，
不重构无关 store、模型、页面或工具。
