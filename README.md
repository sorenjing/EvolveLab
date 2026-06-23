# Evolving AI

> 一个能读懂、修改并进化自身源码的 ReAct Agent。

基于自研 ReAct 推理循环，Agent 不仅能调用工具完成用户任务，还能像修改普通业务代码一样修改自己的工具集、Prompt 甚至内核——只要给它正确的工具与自我认知。

## 核心特性

- **自研 ReAct 内核**：不依赖 LangChain/AutoGen，自行控制 Thought → Action → Observation 循环，强制 LLM 输出结构化 JSON
- **工具系统**：文件读写/编辑、命令执行、目录搜索、屏幕截图等，均受沙箱与权限边界约束
- **自我修改机制**：Agent 的源码对它而言只是另一组可读写文件，支持 L1 新增工具 / L2 修改 Prompt / L3 修改内核（演进中）
- **安全沙箱**：路径越界防护、命令白名单 + 元字符禁用 + 黑名单正则三层防御、写前自动备份、角色权限分级
- **上下文压缩**：长任务自动压缩历史步骤，但严格保留 todo 与完成状态，防止"失忆"
- **SSE 实时轨迹**：前端 Timeline 实时渲染每一步思考/动作/观察

## 架构

```
┌──────────────────────────────────────────────────────────────┐
│                        Browser (Next.js)                     │
│  ┌──────────────┐    ┌──────────────────────────────────┐  │
│  │  Task Input  │───→│  Timeline (SSE Stream Renderer)  │  │
│  └──────────────┘    └──────────────────────────────────┘  │
└────────────────────────────┬─────────────────────────────────┘
                             │ POST /api/agent/stream (SSE)
┌────────────────────────────▼─────────────────────────────────┐
│                    FastAPI Backend                           │
│  ┌──────────────┐    ┌──────────────┐    ┌─────────────┐   │
│  │ Agent Kernel │───→│  Tool Router │───→│  Tool Impl  │   │
│  │ (ReAct Loop) │    │ (Zod Schema) │    │ (File/Exec) │   │
│  └──────────────┘    └──────────────┘    └─────────────┘   │
│         ↑                                   │                │
│         └────────── LLM API ────────────────┘                │
│                   (OpenAI-compatible)                        │
└──────────────────────────────────────────────────────────────┘
```

## 技术栈

| 层级 | 选型 |
|------|------|
| 前端 | Next.js 16 (App Router) + React 19 + TypeScript + Tailwind CSS v4 |
| 后端 | Python 3.10+ + FastAPI + Uvicorn |
| LLM | OpenAI-compatible（默认智谱 GLM-4-Flash，可换 Moonshot/OpenAI 等） |
| 通信 | SSE (Server-Sent Events) 流式推送 |

## 快速开始

### 1. 配置 LLM

```bash
cd backend
cp .env.example .env
# 编辑 .env，填入你的 API Key
```

### 2. 启动后端

```bash
cd backend
python -m venv venv
# Windows
.\venv\Scripts\pip install -r requirements.txt
.\venv\Scripts\uvicorn main:app --host 0.0.0.0 --port 8001 --reload
# Linux / macOS
# source venv/bin/activate
# pip install -r requirements.txt
# uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

### 3. 启动前端

```bash
npm install
npm run dev
```

浏览器访问 http://localhost:3000，输入任务即可看到 Agent 实时执行轨迹。

> Windows 一键启动：`.\start.ps1`

## 目录结构

```
evolvingAI/
├── backend/
│   ├── agent/          # ReAct 内核、LLM 封装、Prompt、上下文压缩
│   ├── api/            # FastAPI 路由（SSE 接口、权限管理）
│   ├── auth/           # 权限缓存、命令白名单、LLM 能力探测
│   ├── tools/          # 工具实现（文件/命令/截图/清理）
│   ├── config.py
│   └── main.py
├── src/app/            # Next.js 前端（任务输入 + Timeline）
├── DESIGN.md           # 详细设计方案
└── RUN.md              # 运行与打包指南
```

## 演进路线

- [x] **Phase 1**：基础 ReAct Loop + 工具系统 + 前端 Timeline
- [x] **安全加固**：命令注入防护、会话 TTL、JSON 解析容错、单例修复
- [ ] **Phase 2**：自我修改安全层（Git 快照 + 构建验证 + 回滚）
- [ ] **Phase 3**：L1 新增工具的端到端自举
- [ ] **Phase 4**：L2/L3 Prompt/内核修改

## License

MIT
