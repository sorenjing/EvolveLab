# EvolveLab

<p align="center">
  <strong>一个可视化、可定制的 AI Agent 实验平台</strong><br>
  看清 Agent 的每一步思考，给它装上你想要的任何工具
</p>

<p align="center">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-blue.svg">
  <img alt="Python" src="https://img.shields.io/badge/python-3.10+-3776AB.svg">
  <img alt="Next.js" src="https://img.shields.io/badge/Next.js-16-000000.svg">
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-0.115-009688.svg">
  <img alt="PRs Welcome" src="https://img.shields.io/badge/PRs-welcome-brightgreen.svg">
</p>

<p align="center">
  <a href="#这是什么">这是什么</a> ·
  <a href="#和-cursorcodexclaude-code-有什么不同">差异化</a> ·
  <a href="#能做什么">能做什么</a> ·
  <a href="#快速开始">快速开始</a> ·
  <a href="#架构">架构</a> ·
  <a href="#安全设计">安全设计</a>
</p>

---

## 这是什么？

EvolveLab 是一个**白盒的 AI Agent 实验平台**。

大多数 AI 工具（Cursor、Trae、Copilot）是**黑盒**——你输入需求，它给结果，中间过程你看不到。EvolveLab 反过来：Agent 的每一次思考、每一次工具调用、每一个观察结果，都实时展示在 Timeline 上，让你**看清 AI 是怎么想的**。

同时，EvolveLab 是**可定制的**——Agent 不只能用内置工具，还能自己创建新工具并持久化保存。你也可以手动给它加工具，把它改造成你专属的 Agent。

> 适合谁用？
> - 想学习 AI Agent 原理的开发者
> - 想调试 / 研究 Agent 行为的人
> - 想搭建个人自动化工作流的极客
> - 对"AI 能怎么思考"感到好奇的人

## 和 Cursor/Codex/Claude Code 有什么不同？

| 维度 | Cursor / Codex / Claude Code | EvolveLab |
|------|------------------------------|-----------|
| **过程可见性** | 黑盒，只给结果 | 白盒，每步思考可见 |
| **工具系统** | 固定内置 | 可动态创建/删除，Agent 能自举新工具 |
| **定位** | 代码助手（需求驱动） | Agent 实验平台（探索驱动） |
| **内核** | 闭源 | 自研 ReAct 内核，完全开源 |
| **数据** | 部分经过云端 | 完全本地运行 |

**一句话**：它们帮你写代码，EvolveLab 帮你理解 Agent 是怎么工作的。

## 能做什么

### 示例 1：让 Agent 分析你的项目

```
任务：分析这个项目的结构，找出主要模块

Agent 执行轨迹：
  Step 1  THOUGHT  我需要先看根目录有哪些文件
          ACTION   list_files(path=".")
          OBSERVE  backend/  src/  package.json  README.md ...

  Step 2  THOUGHT  有 backend 和 src，先看 backend 结构
          ACTION   list_files(path="backend")
          OBSERVE  agent/  api/  auth/  tools/  main.py ...

  Step 3  THOUGHT  读 main.py 了解入口
          ACTION   read_file(path="backend/main.py")
          OBSERVE  FastAPI 应用，注册了路由...

  ✅ 结果：这是一个前后端分离的 Agent 实验平台，后端 FastAPI
          提供 ReAct 内核和工具系统，前端 Next.js 做 Timeline 可视化...
```

### 示例 2：让 Agent 给自己加一个新工具

```
任务：我需要一个能把文本翻译成英文的工具，你创建一下

Agent 执行轨迹：
  Step 1  THOUGHT  现有工具没有翻译能力，我用 create_tool 创建
          ACTION   create_tool(
                     name="translate_to_en",
                     description="将中文文本翻译为英文",
                     args=["text"],
                     code="def run(**kwargs): ..."
                   )
          OBSERVE  [成功] 工具 'translate_to_en' 已创建并注册

  Step 2  THOUGHT  测试一下新工具
          ACTION   translate_to_en(text="你好世界")
          OBSERVE  Hello World

  ✅ 结果：已创建翻译工具，持久化保存，重启后仍可用
```

### 示例 3：让 Agent 修改代码并安全验证

```
任务：在 backend/tools 下加一个计算器工具

Agent 执行轨迹：
  Step 1  THOUGHT  修改项目源码前必须先创建快照
          ACTION   create_snapshot()
          OBSERVE  [成功] 快照 ID: a1b2c3d4

  Step 2  THOUGHT  写入计算器工具代码
          ACTION   write_file(path="backend/tools/custom/calc.py", content="...")
          OBSERVE  文件已写入

  Step 3  THOUGHT  验证修改没有破坏项目
          ACTION   verify_build()
          OBSERVE  [成功] 构建验证通过

  ✅ 结果：计算器工具已添加，构建验证通过
```

## 核心特性

- **白盒 Timeline** — 实时渲染 Agent 的 Thought → Action → Observation 闭环，每一步都看得见
- **自研 ReAct 内核** — 不依赖 LangChain/AutoGen，从零实现推理循环，强制结构化 JSON 输出，死循环检测 + 上下文压缩
- **可定制工具系统** — 16 个内置工具 + Agent 运行时自举新工具，持久化到本地，重启后自动加载
- **自我修改安全层** — Git 快照 → 修改 → 构建验证 → 失败自动回滚，让 Agent 改自己的代码也不会崩
- **多层安全沙箱** — 命令注入三层防御、路径越界防护、角色权限分级、管理接口认证
- **完全本地运行** — 代码不离开你的电脑，API Key 存浏览器 localStorage，不碰文件系统

## 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/sorenjing/evolvingAI.git
cd evolvingAI
```

### 2. 启动后端

```bash
cd backend
python -m venv venv

# Windows
.\venv\Scripts\pip install -r requirements.txt
.\venv\Scripts\uvicorn main:app --host 127.0.0.1 --port 8001 --reload

# Linux / macOS
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 8001 --reload
```

### 3. 启动前端

```bash
# 回到项目根目录
npm install
npm run dev
```

浏览器访问 **http://localhost:3000**：

1. 点击右上角「设置」→ 填入 API Key → 测试连接 → 保存
2. 输入任务（如"分析这个项目的结构"）→ 点「执行」
3. 观察 Timeline 上 Agent 的实时思考过程

> **Windows 一键启动**：`.\start.ps1`

### 配置 API Key

API Key 在前端界面配置，保存在浏览器 localStorage，**不写入文件、不上传 GitHub**：

| 字段 | 说明 | 默认值 |
|------|------|--------|
| API Key | LLM API 密钥（必填） | — |
| Base URL | LLM API 地址 | `https://open.bigmodel.cn/api/paas/v4` |
| Model | 模型名称 | `glm-4-flash` |

<details>
<summary>支持的 LLM 提供商</summary>

| 提供商 | BASE_URL | 推荐 Model |
|--------|----------|-----------|
| 智谱 AI | `https://open.bigmodel.cn/api/paas/v4` | `glm-4-flash` |
| Moonshot | `https://api.moonshot.cn/v1` | `moonshot-v1-8k` |
| OpenAI | `https://api.openai.com/v1` | `gpt-4o-mini` |
| DeepSeek | `https://api.deepseek.com` | `deepseek-chat` |

</details>

## 架构

```mermaid
graph TB
    subgraph Browser["Browser (Next.js 16)"]
        UI["任务输入 + Timeline 可视化<br/>配置面板 + 工具列表"]
    end

    subgraph Backend["Python FastAPI Backend"]
        Kernel["ReAct 内核<br/>Thought→Action→Observation"]
        Router["工具路由<br/>16 内置 + 动态自举"]
        Tools["工具实现<br/>File / Exec / Safety / Lifecycle"]
        Sandbox["安全沙箱<br/>权限 + 路径 + 命令防御"]
    end

    LLM["LLM API<br/>OpenAI-compatible"]

    UI -->|"POST /api/agent/stream (SSE)"| Kernel
    Kernel -->|"生成 Action"| Router
    Router --> Tools
    Tools --> Sandbox
    Sandbox -->|"Observation"| Kernel
    Kernel -->|"流式事件"| UI
    Kernel <-->|"推理"| LLM
```

## 技术栈

| 层级 | 选型 | 说明 |
|------|------|------|
| 前端 | Next.js 16 + React 19 + TypeScript | App Router, Tailwind CSS v4 |
| 后端 | Python 3.10+ + FastAPI + Uvicorn | SSE 流式推送 |
| LLM | OpenAI-compatible API | 默认智谱 GLM-4-Flash，可换任意兼容模型 |
| 通信 | SSE (Server-Sent Events) | 端到端流式 |

## 安全设计

Agent 能执行命令和修改文件，因此安全是第一优先级：

### 命令注入防御（三层）

1. **黑名单正则** — 拦截 `rm -rf`、`format`、`del /f` 等危险命令
2. **元字符禁用** — 禁止 `;` `&` `|` `` ` `` `$` `>` `<` 等 shell 元字符
3. **精确白名单** — `shlex` 解析后精确匹配白名单（`npm install` 放行，`npm; rm -rf` 拦截）

### 其他安全机制

- **路径沙箱** — 文件操作限制在项目目录内
- **写前备份** — 修改前自动创建 `.bak` 备份
- **角色权限** — 只读 / 标准 / 管理员三级权限
- **管理接口认证** — `/api/admin/*` 默认仅 localhost，远程需 `ADMIN_TOKEN`
- **速率限制** — 全局 30/min，Agent 接口 10/min，防止额度滥用
- **默认 localhost** — 服务默认监听 `127.0.0.1`，不暴露公网

### 自我修改安全层

Agent 修改自身源码时的保护流程：

| 阶段 | 操作 | 工具 |
|------|------|------|
| 修改前 | 创建 Git 快照 | `create_snapshot` |
| 修改 | 写入/编辑文件 | `write_file` / `edit_file` |
| 验证 | 后端语法 + 前端类型检查 | `verify_build` |
| 回滚 | 验证失败时恢复 | `rollback` |

## 演进路线

- [x] **Phase 1**：基础 ReAct Loop + 工具系统 + 前端 Timeline
- [x] **安全加固**：命令注入防御、会话 TTL、JSON 解析容错、速率限制、管理接口认证
- [x] **Phase 2**：自我修改安全层（Git 快照 + 构建验证 + 回滚）
- [x] **Phase 3**：Agent 自主扩展工具（create_tool + 本地持久化 + 工具列表）
- [ ] **Phase 4**：L2/L3 Prompt/内核修改

## 贡献

欢迎 Issue 和 PR！提 PR 前请确保：

1. 后端代码通过 `python -m py_compile` 语法检查
2. 前端代码通过 `npm run build` 构建检查
3. 不要提交 `.env` 等含敏感信息的文件

## License

[MIT](LICENSE) © 2026 sorenjing
