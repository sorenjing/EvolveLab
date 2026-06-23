# 会自我进化的 Agent — 设计方案

## 1. 技术选型

| 层级 | 选型 | 理由 |
|------|------|------|
| 前端框架 | Next.js 15 (App Router) + TypeScript | 全栈一体，API Route 直接作为 Agent 后端，无需额外服务 |
| 样式 | Tailwind CSS | 快速搭建执行轨迹展示界面 |
| 大模型接入 | Vercel AI SDK (`ai` + `@ai-sdk/openai`) | 底层仍是自己实现循环，SDK 只做流式调用与类型安全 |
| 模型 | OpenAI-compatible (via Moonshot/baseUrl) | 使用提供的 API Key，支持流式输出 |
| 运行时 | Node.js 20+ | 支持原生 `fetch`、`structuredClone` |

---

## 2. Agent 内核设计

### 2.1 核心抽象

```
┌─────────────────────────────────────────────────────────────┐
│                        Agent Kernel                          │
│  ┌─────────────┐   ┌─────────────┐   ┌──────────────────┐  │
│  │  ReAct Loop │ → │ Tool Router │ → │ Executor (Sandbox)│  │
│  └─────────────┘   └─────────────┘   └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

#### ReAct 推理循环（自己实现）

不使用 LangChain/AutoGen 等现成框架，自行控制每一步：

```
while (step < maxSteps && !taskDone) {
  1. 构造 Prompt：System Prompt + 历史 Thought/Action/Observation + 当前任务
  2. 调用 LLM，要求输出 JSON：{ thought, action, actionInput }
  3. 解析 JSON（失败则重试/容错）
  4. 若 action === "final_answer" → 结束循环
  5. 否则，路由到对应 Tool，执行得到 Observation
  6. 将 Thought/Action/Observation 写入历史，继续循环
}
```

**Prompt 格式（强制 JSON 输出）**：

```
你是一个能使用工具的 Agent。你必须按以下格式思考并行动：

{
  "thought": "分析当前情况，决定下一步",
  "action": "工具名或 final_answer",
  "actionInput": { ...参数... }
}

可用工具：
- readFile: { path }
- writeFile: { path, content }
- executeCommand: { command, cwd? }
- searchFiles: { pattern, path? }
- listFiles: { path }

规则：
- 必须输出合法 JSON，不含其他文字
- 若任务已完成，action 填 "final_answer"，actionInput 填结果
- 不要假设文件内容，不确定时先 readFile
```

### 2.2 工具层设计

| 工具 ID | 功能 | 安全边界 |
|---------|------|----------|
| `readFile` | 读取文件内容（文本） | 只允许项目目录内 |
| `writeFile` | 写入/覆盖文件 | 只允许项目目录内，写前备份 |
| `editFile` | 基于 Search/Replace 修改文件 | 同上，失败时回滚 |
| `executeCommand` | 执行 shell 命令 | 白名单机制：只允许 `npm`, `node`, `npx`, `git status` 等只读/构建命令；禁止 `rm -rf /` 等 |
| `listFiles` | 列出目录结构 | 项目目录内 |
| `searchFiles` | 按内容或文件名搜索 | 项目目录内 |
| `final_answer` | 结束任务，返回结果 | — |

**工具定义（Zod Schema）**：
每个工具有 `name`、`description`、`parameters`（Zod Object）、`execute` 函数。
Agent Kernel 在每次循环时，将工具列表以 JSON Schema 形式注入 Prompt，让模型知道可调用的工具签名。

### 2.3 多轮调用与状态管理

- **服务端状态**：由于 Next.js API Route 是无状态的，每次流式请求在服务端维护一个 `AgentSession` 对象（存在内存 Map 中，以 `sessionId` 为键）。
- **前端状态**：SSE (Server-Sent Events) 实时推送每一步的 `thought`、`action`、`observation`、`status`。
- **容错**：
  - LLM 返回非 JSON：尝试正则提取 JSON；失败则重试（最多 2 次）。
  - 工具执行报错：`Observation` 中返回错误信息，让 LLM 自行决定重试或换方案。
  - 死循环检测：若连续 3 次 `action` 完全相同，强制终止并提示用户。

---

## 3. 前端设计

### 3.1 页面结构

```
┌────────────────────────────────────┐
│  Header: Agent Evolution           │
├────────────────────────────────────┤
│  Input Area                        │
│  [ 请输入任务...          ] [执行] │
├────────────────────────────────────┤
│  Execution Timeline                │
│  ┌─ Step 1 ───────────────────┐   │
│  │ 🤔 Thought: 分析需求...     │   │
│  │ 🔧 Action: readFile(...)    │   │
│  │ 📋 Observation: 文件内容... │   │
│  └─────────────────────────────┘   │
│  ┌─ Step 2 ───────────────────┐   │
│  │ ...                         │   │
│  └─────────────────────────────┘   │
├────────────────────────────────────┤
│  Final Result                      │
└────────────────────────────────────┘
```

### 3.2 交互流程

1. 用户在输入框填入任务，点击「执行」。
2. 前端通过 `fetch('/api/agent', { body: { task, sessionId } })` 建立 SSE 连接。
3. 服务端启动 ReAct Loop，每完成一步通过 `data: { type, payload }` 推送给前端。
4. 前端解析 SSE，按时间顺序渲染 Timeline。
5. 任务结束（`final_answer` 或异常）后，SSE 关闭，展示最终结果。

---

## 4. 自我修改机制设计（进阶）

### 4.1 核心思想

Agent 的源码对它而言只是**另一组可读写文件**。只要给它正确的工具和自我认知，它就能像修改业务代码一样修改自己的工具集合或 Prompt。

### 4.2 自我修改的层级

| 层级 | 修改对象 | 实现方式 | 风险等级 |
|------|----------|----------|----------|
| L1 增加工具 | `src/lib/tools/` 下新增工具文件 | 模型生成代码 → writeFile → 动态 import | 中 |
| L2 修改 Prompt | `src/lib/prompts/system.ts` | 模型生成新 Prompt → editFile | 中 |
| L3 修改内核 | `src/lib/agent.ts`（循环逻辑） | 模型重写核心循环 | **高** |
| L4 修改配置 | `next.config.js`、依赖列表 | 模型增删依赖或构建配置 | **高** |

### 4.3 安全与隔离机制（关键）

直接让 Agent 改自己的源码极易导致系统崩溃。必须设计**沙箱与回滚**：

#### A. 版本快照（Snapshot）

- 在 Agent 启动自我修改前，自动对 `src/` 目录做 Git 快照：
  ```bash
  git stash push -m "pre-self-modify-$(timestamp)"
  ```
- 每次修改后尝试 `npm run build`：
  - 构建通过 → 保留修改，提示用户。
  - 构建失败 → 自动 `git stash pop` 回滚，Observation 返回错误让模型重试。

#### B. 工具白名单与能力声明

- Agent 的 Prompt 中显式列出「你能修改的文件范围」。
- `writeFile`/`editFile` 对核心文件（如 `agent.ts`、`package.json`）增加二次确认：
  - 修改核心文件前，必须先生成一个 `.patch` 文件，经用户确认或自动测试通过后再应用。

#### C. 最小权限原则

- 新增工具（L1）最安全：只需在约定目录新增文件，并导出到 `tools/index.ts` 的注册表中。
- 修改内核（L3）默认关闭，需用户显式授权 `allowKernelMutation: true`。

### 4.4 自举流程（示范）

用户任务："给自己增加一个能计算数学表达式的工具"

```
Step 1: Thought → 需要新增一个 mathEval 工具
Step 2: Action  → readFile({ path: "src/lib/tools/index.ts" })
         Observation → 看到工具注册表结构
Step 3: Action  → writeFile({
           path: "src/lib/tools/mathEval.ts",
           content: "...导出 mathEval 工具..."
         })
Step 4: Action  → editFile({
           path: "src/lib/tools/index.ts",
           search: "export const tools = [",
           replace: "export const tools = [\n  mathEval,"
         })
Step 5: Action  → executeCommand({ command: "npm run build" })
         Observation → build success
Step 6: Action  → final_answer({ result: "已新增 mathEval 工具" })
```

---

## 5. 系统架构图

```
┌──────────────────────────────────────────────────────────────┐
│                        Browser                               │
│  ┌──────────────┐    ┌──────────────────────────────────┐  │
│  │  Task Input  │───→│  Timeline (SSE Stream Renderer)  │  │
│  └──────────────┘    └──────────────────────────────────┘  │
└────────────────────────────┬─────────────────────────────────┘
                             │ POST /api/agent (SSE)
┌────────────────────────────▼─────────────────────────────────┐
│                    Next.js API Route                         │
│  ┌──────────────┐    ┌──────────────┐    ┌─────────────┐   │
│  │ Agent Kernel │───→│  Tool Router │───→│  Tool Impl  │   │
│  │ (ReAct Loop) │    │ (Zod Schema) │    │ (File/Exec) │   │
│  └──────────────┘    └──────────────┘    └─────────────┘   │
│         ↑                                   │                │
│         └────────── LLM API ────────────────┘                │
│                          (OpenAI-compatible)                 │
└──────────────────────────────────────────────────────────────┘
```

---

## 6. 目录结构（规划）

```
agent-evolution/
├── src/
│   ├── app/
│   │   ├── page.tsx              # 主界面（输入 + Timeline）
│   │   ├── layout.tsx            # 根布局
│   │   └── api/
│   │       └── agent/
│   │           └── route.ts      # SSE Agent 接口
│   ├── lib/
│   │   ├── agent.ts              # Agent Kernel（ReAct 循环）
│   │   ├── llm.ts                # LLM 调用封装（AI SDK）
│   │   ├── session.ts            # Session 管理（内存 Map）
│   │   ├── tools/
│   │   │   ├── index.ts          # 工具注册表
│   │   │   ├── readFile.ts
│   │   │   ├── writeFile.ts
│   │   │   ├── editFile.ts
│   │   │   ├── executeCommand.ts
│   │   │   ├── listFiles.ts
│   │   │   ├── searchFiles.ts
│   │   │   └── mathEval.ts       # （可由 Agent 自己新增）
│   │   └── prompts/
│   │       └── system.ts         # System Prompt 模板
│   └── types/
│       └── agent.ts              # 共享类型定义
├── DESIGN.md                     # 本设计文档
└── package.json
```

---

## 7. 关键接口

### SSE 事件格式

```ts
type AgentEvent =
  | { type: 'thought'; content: string; step: number }
  | { type: 'action'; tool: string; input: unknown; step: number }
  | { type: 'observation'; result: string; step: number }
  | { type: 'error'; message: string; step: number }
  | { type: 'complete'; result: string };
```

### Agent 配置

```ts
interface AgentConfig {
  maxSteps: number;           // 默认 15
  model: string;              // 默认 'moonshot-v1-8k'
  apiKey: string;
  baseURL: string;
  allowKernelMutation: boolean; // 默认 false（安全开关）
}
```

---

## 8. 启动说明（后续交付）

```bash
# 1. 进入项目
cd agent-evolution

# 2. 配置环境变量
cp .env.local.example .env.local
# 编辑 .env.local，填入 API Key 与 BaseURL

# 3. 开发模式启动
npm run dev

# 4. 浏览器访问 http://localhost:3000
```

---

## 9. 演进路线

1. **Phase 1（必做）**：实现基础 ReAct Loop + 6 个文件/命令工具 + 前端 Timeline，确保能跑通多轮调用。
2. **Phase 2（进阶）**：增加「自我修改」安全层（Git 快照 + 构建验证 + 回滚）。
3. **Phase 3（进阶）**：实现 L1「新增工具」的端到端自举（Agent 自己写工具文件并注册）。
4. **Phase 4（顶尖）**：实现 L2/L3 的 Prompt/内核修改，并能在修改后继续稳定运行。
