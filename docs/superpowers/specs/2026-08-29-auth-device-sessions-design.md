# 生产鉴权第一子阶段：单设备 Refresh Token 会话设计

## 1. 目标与范围

本阶段是生产鉴权增强的第一子阶段。目标是在不改变 945 现有视觉系统、Agent
安全边界或 demo/mock 开发路径的前提下，将当前的单一 HMAC Bearer token 升级为：

- 15 分钟有效的 access token；
- 每台设备独立、30 天有效且可轮换的 refresh token；
- 用户可在设置页查看并撤销单台设备；
- 用户可主动退出全部设备；
- 修改密码后立即撤销全部设备；
- 已被撤销设备的 access token 在下一次受保护请求时立即失效。

本阶段只实现上述会话能力。邮箱验证、忘记密码、Redis 分布式限流、第三方登录、
跨服务身份提供方和新的整体视觉设计不在范围内。

## 2. 当前问题

当前后端为用户签发 7 天 HMAC token，并通过 `AuthCredential.session_version`
实现全局撤销。前端将该 token 保存在 `localStorage`。因此存在以下限制：

- 长期凭证可被页面脚本读取；
- 无法识别或管理单台登录设备；
- 无法单独撤销某台设备；
- access token 不能安全地缩短到生产可接受的短时有效期。

## 3. 方案选择

采用 Mongo 持久化设备会话，而不是纯签名 refresh token 或第三方身份平台。

- 纯签名 refresh token 无法可靠列出和撤销单台设备。
- 第三方身份平台会引入外部账户、服务依赖和费用，当前没有必要。
- 持久化会话可直接满足单设备管理、刷新轮换和立即撤销，并沿用现有 Mongo
  repository 边界。

## 4. 数据模型

新增 `AuthDeviceSession`，写入 Mongo 的 `auth_device_sessions` 集合。每台登录设备
对应一条记录：

```text
session_id              UUID
user_id                 用户 ID
refresh_token_hash      refresh token 的 HMAC-SHA256 摘要
device_name             从 User-Agent 生成的简短设备名称
created_at              创建时间
last_used_at            最近刷新时间
expires_at              refresh token 过期时间
revoked_at              撤销时间，未撤销时为空
```

`AuthCredential.session_version` 保留，作为修改密码和“退出全部设备”的全局撤销
版本。`AuthDeviceSession` 是单设备撤销的权威记录。

Mongo 需要为 `session_id`、`refresh_token_hash` 和 `user_id` 建立查询所需索引。
refresh token 的明文绝不写入数据库、日志、错误响应、测试快照或前端状态。

## 5. Token 与 Cookie

### 5.1 Access token

- 使用现有 HMAC 格式，payload 增加 `sid`（设备 session_id）。
- 有效期改为 15 分钟。
- 每次鉴权都验证签名、过期时间、`session_version` 和对应设备会话是否未撤销、
  未过期。
- 前端只在运行内存保存 access token；页面刷新后不从 `localStorage` 恢复它。

### 5.2 Refresh token

- 使用高熵随机值，数据库只保存以 `945_AUTH_SECRET` 为密钥计算的 HMAC-SHA256
  摘要。
- 登录、注册和 refresh 都会签发新 refresh token；refresh 时原摘要立即替换，
  旧 token 立刻失效。
- refresh token 通过名为 `945_refresh_token` 的 HttpOnly Cookie 发送。
- Cookie 使用 `SameSite=Lax`、`Path=/api/auth`、30 天 `Max-Age`；生产环境添加
  `Secure`，本机 HTTP 开发环境不添加 `Secure`。
- 由于 refresh 仅在同源 `/api/auth` 下使用，前端不读取 Cookie；跨站请求不能读取
  access token 响应。

## 6. API 合约

保持现有 JSON 信封 `{ data, error }`，并新增或调整以下端点：

| 端点 | 行为 |
| --- | --- |
| `POST /api/auth/register` | 创建账号与当前设备会话，返回短期 access token 并设置 refresh Cookie。 |
| `POST /api/auth/login` | 创建当前设备会话，返回短期 access token 并设置 refresh Cookie。 |
| `POST /api/auth/refresh` | 读取 refresh Cookie，验证且轮换 token，返回新的短期 access token。 |
| `GET /api/auth/sessions` | 返回当前用户设备会话摘要，包含当前会话标记，不返回 refresh 摘要。 |
| `DELETE /api/auth/sessions/{session_id}` | 撤销指定的本人设备会话。 |
| `POST /api/auth/logout` | 撤销当前设备会话并清除 refresh Cookie。 |
| `POST /api/auth/logout-all` | 递增 session_version、撤销全部设备会话并清除当前 refresh Cookie。 |
| `POST /api/auth/change-password` | 成功后递增 session_version、撤销全部设备会话并清除当前 refresh Cookie。 |

`GET /api/auth/me` 保持不变，但会基于 access token 的 `sid` 校验设备会话。
不存在、已撤销、过期或不属于当前用户的 session_id 一律返回现有的 `401` 或 `403`
语义；不得泄露其他用户的会话信息。

## 7. 前端行为

### 7.1 会话恢复与请求重试

应用启动时先调用 `POST /api/auth/refresh`：

- 成功：仅将新的 access token 和当前用户保存在内存，继续加载应用；
- 缺少、过期或已撤销的 Cookie：清空内存会话并显示现有登录页；
- 受保护 API 收到 `401`：只调用一次 refresh 后重试原请求一次；再次 `401` 时清空
  内存会话并回到登录页，禁止循环刷新。

mock 模式保持当前行为，不请求 refresh endpoint。

### 7.2 设置页

在现有设置页增加“已登录设备”内容区，沿用当前字体、颜色、玻璃效果、按钮和
间距体系。内容包括：

- 当前设备与其他设备的简短名称；
- 最近使用时间；
- 当前设备标记；
- 其他设备的“退出此设备”操作；
- 全部设备的“退出所有设备”确认操作。

当前顶部退出登录操作改为只退出当前设备。密码修改成功后，当前页面回到登录页，
并提示所有设备均需重新登录。

## 8. 错误处理与安全边界

- refresh token 缺失、无效、过期、轮换后重放或已撤销：返回 `401`，清除 Cookie，
  不创建新会话。
- 设备撤销请求只能操作当前用户自己的 session_id；跨用户请求返回 `404`，避免
  枚举会话。
- 单设备退出、全部退出与改密码均不写入训练、饮食、计划或 Agent 草稿数据。
- Agent 继续保持“模型生成草稿，用户确认后通过结构化 API 写入”的边界。
- refresh token、密码、Authorization header 和完整模型输出不得写入日志。

## 9. 验收标准

后端与 HTTP 验收至少覆盖：

1. 注册和登录设置 HttpOnly refresh Cookie，返回 15 分钟 access token。
2. refresh 成功后生成新的 access token 和 refresh token；旧 refresh token 不能再次使用。
3. 两次登录产生两条独立设备会话；列表只显示当前用户自己的会话。
4. 撤销设备后，该设备 refresh token 与 access token 均不能访问受保护 API；另一台
   设备仍可使用。
5. “退出全部设备”和修改密码会使所有设备的 refresh 与 access token 失效。
6. 页面刷新会经 refresh 自动恢复；refresh 失败会显示登录页；普通 `401` 最多刷新和
   重试一次。
7. demo/mock 模式、现有注册/登录、Agent 草稿确认和跨用户授权测试不回归。
8. 前端构建、相关 Pytest、真实 HTTP QA 与 Mongo QA 均通过。

## 10. 实施边界

实现会限定在鉴权模型、repository/store、auth service/routes、前端会话服务、设置页
内容与对应测试。不会重构 Agent 工作流、计划/记录 API、颜色、字体、图标、导航外观、
玻璃效果或其他页面。
