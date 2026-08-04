# Agent Eval Quality Gate Design

## Goal

将 945 的 Agent 验收从当前 30 条 deterministic 冒烟基准扩展为可重复的 50 条离线质量门槛，并提供一个只在开发者显式执行时才调用 DeepSeek 的 8 条小样本验收。

## Scope

- 不修改前端 UI、路由、Agent 产品功能、提示词或结构化数据模型。
- 不修改默认 CI 的零费用路径；CI 只运行 deterministic 50 条基准。
- DeepSeek 只在本机显式命令、存在 `DEEPSEEK_API_KEY` 时运行，不写入训练、饮食或计划记录。
- 不根据可能变化的模型价格计算金额；报告只记录 token、耗时与 HTTP 尝试次数，实际费用以 DeepSeek 控制台为准。

## Case Sets

### Deterministic Baseline

基准总数为 50 条，分为三组：

| 组别 | 数量 | 覆盖内容 |
| --- | ---: | --- |
| 基础问答 | 20 | 训练、饮食、恢复、英文问答与当天计划问题 |
| 操作意图 | 20 | 训练记录、饮食记录、计划调整、中文/英文变体与上下文输入 |
| 安全与异常 | 10 | 疼痛、胸闷、呼吸困难、晕厥、危险训练请求和无明确记录请求 |

每一条都断言：预期 intent、预期草稿类型，以及运行期间没有产生结构化写入。

### DeepSeek Sample

固定 8 条小样本，覆盖训练记录、饮食记录、计划调整、训练问答、饮食问答、安全风险、英文请求和边界请求。DeepSeek 的输出存在非确定性，因此只检查安全边界与类别级结果：

- intent 与预期一致；
- 草稿类型与预期一致；
- 不直接写入结构化记录；
- 不产生未允许的第二轮工具调用。

小样本通过门槛为至少 7/8，且结构化写入必须为 0。缺少 Key、网络错误或模型限流视为“未执行”或“运行失败”，不会被当作通过。

## Execution Interface

保留现有入口 `python -m backend.evals.run_agent_eval`，新增 provider 选择：

```powershell
# 零费用 deterministic 基准，供本机与 CI 使用
python -m backend.evals.run_agent_eval --provider deterministic --json-output output/agent-eval.json

# DeepSeek 小样本。只有显式执行时才会产生 API 费用
$env:DEEPSEEK_API_KEY="..."
python -m backend.evals.run_agent_eval --provider deepseek --json-output output/deepseek-eval.json
```

默认 provider 为 `deterministic`。`--provider deepseek` 不接受 CI 自动调用，也不读取或输出 Key。

## Report Contract

JSON 报告新增但不移除现有字段：

- `provider`、`suite`、`total_cases`、`passed_cases`、`pass_rate`、`passed`；
- `structured_writes`、`failure_categories`；
- `total_duration_ms`、`average_duration_ms`；
- `total_input_tokens`、`total_output_tokens`、`total_http_attempts`；
- 每个 case 的 `duration_ms`、token、HTTP 尝试次数、失败分类与现有断言详情。

deterministic 报告必须 50/50 且 `structured_writes=0`。DeepSeek 报告必须至少 7/8 且 `structured_writes=0`。

## Error Handling

DeepSeek Key 缺失时命令快速失败并说明需要 `DEEPSEEK_API_KEY`，不调用网络。每个案例遇到 Provider、超时、限流或输出校验错误时记录失败分类并继续执行其余案例，最终根据阈值返回非零退出码。

## Testing

- 单元测试验证 50 条 deterministic 用例、报告聚合、门槛、失败分类和零结构化写入。
- DeepSeek 测试使用 fake provider 验证样本选择和报告，不调用网络。
- 保留现有可选真实 DeepSeek smoke test；它不进入默认测试或 CI。
- 运行 `python -m pytest backend/tests -q`、`python -m backend.evals.run_agent_eval --provider deterministic` 与 `npm run build`。

## Non-Goals

- 不将 DeepSeek 50 条全量评测加入日常流程。
- 不把模型输出推导为新的产品能力、字段、计划或 UI。
- 不估算人民币或美元成本，不新增外部观察平台。
