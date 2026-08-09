# 认证用户与 Agent 后端定向回迁设计

## 目标

在当前 `master` 的后端基础上接入 Mongo 注册用户与 Bearer 会话，使注册用户可安全使用 Agent，并让所有业务 API 按登录用户隔离数据。

## 范围

- 只修改 `backend/`、后端测试和后端文档。
- 不修改 `src/`、样式、图标、页面布局、前端路由或前端交互。
- 不修改 DeepSeek、Prompt、RAG、Agent 工具定义或模型调用策略。

## 存储与认证边界

- `945_STORAGE_BACKEND=mongo` 时，MongoDB 保存用户、邮箱密码凭据和业务数据。
- `POST /api/auth/register` 只允许 Mongo 模式；其他存储模式返回 `503 STORAGE_CONFIG_ERROR`。
- `demo` 模式只保留 `demo-user-945`，不创建临时注册账号。
- 密码使用 PBKDF2-HMAC-SHA256 加盐哈希保存，API 不返回密码或哈希。
- 登录返回带有效期的 HMAC Bearer token。修改密码和退出登录通过会话版本撤销旧 token。

## 业务 API 隔离

- 所有业务 API 从 Bearer token 解析当前用户。
- 请求中的 `user_id` 必须与 token 所属用户一致；不一致返回 `403 FORBIDDEN`。
- 生产环境默认要求 token；开发和 demo 环境可用 `945_AUTH_REQUIRED=false` 保持现有演示兼容。
- 未认证或无效 token 返回 `401 UNAUTHORIZED`。

## Agent 边界

- Agent 在 Mongo 模式接受已注册用户，而不是只接受 `demo-user-945`。
- Agent 消息、运行记录、上下文读取和业务数据均按 `user_id` 隔离。
- `/api/agent/chat` 只能返回建议和 `RecordDraft`；不直接写入训练、饮食或计划记录。
- 用户确认后，结构化 API 才能写入相应数据。

## 回迁策略

不直接合并历史功能分支。新分支从当前 `master` 出发，按当前代码结构定向移植认证、Mongo 用户凭据、路由鉴权与 Agent 用户校验所需的后端实现，并补齐最小测试夹具。历史提交中混杂的前端文件不进入本次改动。

## 验收标准

1. Mongo 模式可注册、登录、读取当前会话，并能调用 Agent。
2. 两个注册用户无法读取或写入对方的训练、饮食、计划、资料、Agent 消息或运行记录。
3. demo 模式注册返回 `503 STORAGE_CONFIG_ERROR`，`demo-user-945` 仍可走现有演示流程。
4. Agent 记录请求只产生待确认草稿，不自动写入结构化记录。
5. 运行后端全量测试、前端构建和 `git diff --check`。
