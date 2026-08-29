# 945 项目工作规范

## 适用范围

- 本文件适用于整个仓库。
- 通用编程习惯保留在全局 `AGENTS.md` 中；本文件只记录 945 项目专属的行为边界、命令和验证要求。
- 保留工作区中与当前任务无关的用户改动。除非用户明确要求，否则不要清理、丢弃、暂存或提交这些改动。

## 仓库结构

- `src/`：React 19、TypeScript 和 Vite 前端。
- `tests/`：Playwright 前端测试和真实 HTTP 集成测试。
- `backend/app/`：FastAPI 应用、数据仓库、Agent 工作流和大模型提供方。
- `backend/tests/`：Pytest 后端测试。
- `stitch-reference/`：视觉参考资料，仅用于参考，不是生产代码。

## 产品边界

- 重构时保留现有前端视觉系统。不要主动修改颜色、字体、图标、导航外观、玻璃质感、组件视觉样式或整体设计语言。
- 任务需要时，可以调整内容排版、页面职责、信息架构、路由和交互流程。
- 修改视觉系统前必须获得用户明确确认。
- Agent 和模型输出不能直接写入训练、饮食、计划或其他结构化记录。必须保留“生成草稿—用户确认”的流程，并且只能在用户确认后通过结构化 API 写入。

## 工作方式

- 优先采用小范围、直接解决需求的修改。
- 不要把任务扩大为无关重构或预设未来需求的抽象设计。
- 新增实现前，先搜索仓库中已有的 API、组件、数据仓库或测试模式。
- 除非任务明确要求改变接口，否则前端 mock 模式与真实 HTTP 模式应保持兼容的 API 行为。

## 安装和开发命令

安装依赖：

```powershell
npm ci
python -m pip install -r backend/requirements.txt
```

启动前端 mock 模式：

```powershell
npm run dev
```

启动 FastAPI 后端：

```powershell
python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

启动前端真实 HTTP 模式（读取 `.env.http`，使用 5177 端口）：

```powershell
npm run dev:http
```

## 验证规则

普通 UI、页面职责、表单流程、常规 API 适配和 UI 状态修改：

1. 运行 `npm run build`。
2. 运行一到两个与改动直接相关的测试。

常用前端命令：

```powershell
npm run build
npx playwright test tests/app-smoke.spec.ts
npx playwright test tests/prd-foundation.spec.ts
npm run qa:app
```

常用后端命令：

```powershell
python -m pytest backend/tests -q
python -m pytest backend/tests/test_health.py -q
```

修改计划启用、结构化训练或饮食写入、Agent 草稿确认、MongoDB 模型或数据仓库，以及跨前后端 HTTP 行为时，需要执行一次严格的端到端验证。选择相关的后端测试；如果改动跨越前后端边界，还要运行真实 HTTP 集成测试：

```powershell
npm run build
python -m pytest backend/tests -q
npm run qa:http
```

- `qa:app` 不运行 `tests/http-integration.spec.ts`，使用浏览器 mock 模式。
- `qa:http` 会在 8000 端口启动 FastAPI，在 5177 端口启动 Vite；它使用 demo store 和 deterministic Agent，不需要 MongoDB 或 OpenAI API Key。
- Playwright 使用本机安装的 Chrome。
- 如果完整测试出现疑似时序问题，先单独重跑失败测试，再判断是否属于产品回归。

## 外部服务和仓库卫生

- 默认开发环境使用 demo store 和 deterministic LLM Provider。
- 除非用户明确要求，否则不要运行真实 OpenAI 冒烟测试或产生 API 费用。真实测试需要配置 `945_RUN_OPENAI_SMOKE_TESTS=1`、`945_LLM_PROVIDER=openai`、`OPENAI_API_KEY` 和 `945_OPENAI_MODEL`。
- 不要暴露或提交密钥。
- `.venv/`、`dist/`、`test-results/`、日志和生成的输出文件默认视为本地产物；除非用户明确要求，否则不要提交。
- 除非任务明确需要，否则不要切换到 MongoDB，也不要修改持久化数据库。MongoDB 模式使用 `945_STORAGE_BACKEND=mongo`、`945_MONGODB_URI` 和 `945_MONGODB_DATABASE`。

## AI 输出与测试边界

- 测试输入、mock 数据、prompt 示例、模型实验字段不得视为产品需求。
- Agent 生成的字段、枚举、结构化类型只有在用户明确确认后才能进入产品设计。
- 不得因为某个模型输出包含新的字段、分类或建议，就新增对应的数据模型、接口或 UI。
- 当发现潜在产品能力时，应先记录为建议，不得直接实现。
