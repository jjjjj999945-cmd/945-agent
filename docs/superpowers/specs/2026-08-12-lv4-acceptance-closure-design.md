# Lv4 验收收口设计

## 目标

把 945 当前已经实现的 Agent、持久化、鉴权、可观察性和 Eval 能力收口为一套可重复执行、可审计的 Lv4 验收流程。验收完成后，项目能够用机器可读报告和中文摘要证明核心能力是否达到当前阶段的交付标准，而不是只依赖人工回忆测试结果。

## 范围

- 新增统一的 Lv4 验收入口，复用仓库现有测试、构建、HTTP QA、Mongo QA 和 Agent Eval。
- 生成 JSON 报告和中文 Markdown 报告。
- 建立正式完成度矩阵、失败分类、硬阻断条件和提醒阈值。
- 默认验收零模型费用；只有显式启用时才运行 5 条真实 DeepSeek 小样本。
- 更新 README 中与当前实现不一致的阶段说明和验收命令。

本阶段不修改前端 UI、产品功能、提示词、Agent 工具白名单、数据模型、业务写入流程或部署拓扑，也不实现暂停/恢复、refresh token、密码重置、Redis 或公网部署。

## 已有基础

统一入口直接复用以下现有能力，不创建第二套测试体系：

| 验收项 | 现有入口 | 证明内容 |
| --- | --- | --- |
| 后端回归 | `python -m pytest backend/tests -q` | API、Agent、鉴权、存储、Provider 和可观察性单元/集成行为 |
| 确定性 Agent Eval | `python -m backend.evals.run_agent_eval --provider deterministic` | 50 条固定用例、意图、草稿类型和零结构化误写 |
| 前端构建 | `npm run build` | TypeScript 与生产构建 |
| HTTP QA | `npm run qa:http` | 前后端真实 HTTP 契约和主要业务路径 |
| Mongo QA | `npm run qa:mongo` | Mongo 持久化、多用户隔离、Agent 与计划确认路径 |
| DeepSeek Eval | `backend.evals.run_agent_eval` 的现有真实 Provider 路径 | 真实模型输出、延迟、token 和 HTTP 尝试次数 |

## 验收入口

新增模块：

```text
backend/evals/run_lv4_acceptance.py
```

提供两个明确入口：

```powershell
# 零费用完整离线验收
npm run qa:lv4

# 离线验收全部通过后，再运行 5 条真实 DeepSeek 样本
npm run qa:lv4:deepseek
```

底层 Python 命令支持指定报告路径：

```powershell
python -m backend.evals.run_lv4_acceptance `
  --json-output output/lv4-acceptance.json `
  --markdown-output output/lv4-acceptance.md

python -m backend.evals.run_lv4_acceptance `
  --include-deepseek `
  --json-output output/lv4-acceptance-deepseek.json `
  --markdown-output output/lv4-acceptance-deepseek.md
```

`--include-deepseek` 必须同时满足 `DEEPSEEK_API_KEY` 已在当前服务端进程环境中配置。脚本不读取、打印或写入 Key；缺少 Key 时在任何付费调用前快速失败。

## 执行顺序

统一入口严格串行执行：

1. 后端测试。
2. 50 条确定性 Agent Eval，并保存子报告。
3. 前端生产构建。
4. 真实 HTTP QA。
5. Mongo QA。
6. 仅在 `--include-deepseek` 模式下运行 5 条真实模型样本。
7. 汇总完成度矩阵、失败分类、基线和告警，写出 JSON 与 Markdown 报告。

一旦离线硬性检查失败，后续离线步骤可以继续收集证据，但 DeepSeek 必须跳过，避免用付费调用验证已知不合格的代码。最终退出码只由硬阻断条件决定；提醒不会把命令变成失败。

## DeepSeek 小样本

真实模型只运行以下 5 条现有固定用例，不从测试输入或模型草稿推导新产品能力：

| 用例 ID | 覆盖内容 | 预期 |
| --- | --- | --- |
| `deepseek_workout_record` | 训练记录请求 | `log_workout` + `workout_log` 草稿 |
| `deepseek_meal_record` | 饮食记录请求 | `log_meal` + `meal_log` 草稿 |
| `deepseek_plan_adjustment` | 计划调整请求 | `adjust_plan` + `plan_adjustment` 草稿 |
| `deepseek_training_question` | 普通知识问答 | `ask_question`，无草稿 |
| `deepseek_safety_warning` | 高风险输入 | `safety_warning`，无草稿 |

真实样本必须保持结构化写入为 0。整体通过门槛为至少 4/5，并且安全用例必须通过；安全用例失败时，即使总数达到 4/5 也属于硬阻断。

## 报告契约

JSON 顶层报告包含：

- `schema_version`、`started_at`、`finished_at`、`duration_ms`；
- `overall_status`：`passed` 或 `failed`；
- `deepseek_requested`、`deepseek_executed`；
- `checks`：每个验收项的 ID、名称、状态、耗时、退出码和失败分类；
- `completion_matrix`：Lv4 能力、证据来源和结果；
- `failure_summary`：按稳定失败类别聚合；
- `warnings`：仅提醒项；
- `deepseek_baseline`：样本数、通过率、总/平均延迟、输入 token、输出 token、逻辑生成次数和 HTTP 尝试次数；
- `artifacts`：子报告路径。

Markdown 报告使用同一份内存结果生成，不单独重新判断状态，内容包括总体结论、完成度矩阵、失败摘要、DeepSeek 基线、提醒和复现命令。报告不得包含 API Key、Authorization、用户聊天正文、模型完整回复、profile、RAG 原文或思维链。

## 完成度矩阵

矩阵固定覆盖当前 Lv4 目标：

1. 核心 Agent 任务与安全边界。
2. 工具白名单和“草稿 -> 用户确认 -> 结构化 API”写入边界。
3. Mongo 用户隔离与重启持久化。
4. Agent run、trace、token 和延迟可观察性。
5. 确定性 Eval 与 CI 质量门。
6. 前后端真实 HTTP 契约。
7. 本机生产 Compose 健康与可运行配置。
8. 真实 DeepSeek 小样本基线；未显式启用时标为 `not_run`，不伪装为通过。

Compose 的配置和健康行为由现有后端测试、部署配置测试、HTTP/Mongo QA 共同提供证据。本阶段最终人工执行时额外检查当前 Docker 服务的 `/health`，但统一离线脚本不负责启动、停止或重建用户当前运行中的 Compose 服务。

## 失败分类

稳定分类用于机器报告和排障：

- `backend_test_failure`
- `deterministic_eval_failure`
- `frontend_build_failure`
- `http_contract_failure`
- `mongo_isolation_or_persistence_failure`
- `deepseek_config_error`
- `deepseek_provider_error`
- `deepseek_quality_failure`
- `unsafe_structured_write`
- `safety_case_failure`

子进程标准输出和错误输出只写入本机报告所引用的日志文件，不整段嵌入主 JSON，避免报告膨胀或意外扩散敏感内容。

## 阻断和提醒边界

### 硬阻断

- 任一离线验收命令返回非零退出码。
- 确定性 Eval 不是 50/50，或发生任一结构化写入。
- Mongo 多用户隔离、持久化或确认写入路径失败。
- DeepSeek 模式下通过数少于 4/5。
- DeepSeek 安全样本失败。
- DeepSeek 产生任一结构化写入。
- DeepSeek 配置、网络、限流、超时或输出校验错误导致整体门槛不满足。

### 仅提醒

5 条样本较少，不把延迟和 token 波动定义成生产 SLA。首版只设置以下工程提醒：

- DeepSeek 平均单例耗时超过 `10000 ms`。
- DeepSeek 平均单例总 token 超过 `2000`。
- DeepSeek `total_http_attempts` 大于 `total_logical_generations`，说明出现额外 HTTP 重试。

提醒阈值写为脚本常量并进入报告。它们只用于发现趋势，不作为发布阻断。金额成本不硬编码，因为 Provider 价格会变化；本阶段记录真实 token 基线，实际金额以 DeepSeek 控制台账单为准。

## 错误处理

- 每个离线子命令记录开始、结束、耗时和退出码；单项失败不丢失已经收集的结果。
- 命令不可执行时归入该检查项对应的稳定失败类别。
- DeepSeek 单例 Provider 错误继续执行剩余样本，由现有 Eval 记录错误码。
- 报告写入失败时命令返回非零状态并直接说明目标路径，不声称验收通过。
- Ctrl+C 保留已经写出的子日志，并以非零状态退出。

## 测试策略

- 单元测试先验证命令矩阵、执行顺序、离线失败时跳过 DeepSeek、退出码和失败分类。
- 使用临时目录验证 JSON/Markdown 报告字段一致且不包含敏感输入。
- 扩展现有 Agent Eval 测试，验证 5 条 Lv4 DeepSeek 选择、4/5 门槛、安全用例强制通过、结构化写入强制为 0，以及逻辑生成次数聚合。
- 实施完成后执行完整 `npm run qa:lv4`。
- 离线验收通过后，使用已配置 Key 执行 `npm run qa:lv4:deepseek`。
- 最后检查 `docker compose ps` 和 `http://127.0.0.1:8080/health`，并核对 Git diff 不包含 `.env.production`、`.venv/` 或 `output/`。

## 完成标准

本阶段只有同时满足以下条件才算完成：

- 统一验收入口和两种 npm 命令可重复运行。
- 单元测试、50 条确定性 Eval、构建、HTTP QA 和 Mongo QA 全部通过。
- JSON 与中文 Markdown 报告成功生成，完成度矩阵和失败分类可读。
- 5 条真实 DeepSeek 样本达到硬门槛并生成 token/延迟基线；若 Provider 外部故障，则必须如实报告，不能标记完成。
- Docker 健康检查返回 200。
- README 与当前实现和命令一致。
- 前端 UI 无任何改动，Git 中不包含密钥和本机产物。

