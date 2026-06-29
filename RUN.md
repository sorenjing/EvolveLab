# 运行与部署指南

EvolveLab 是前后端分离架构：后端 FastAPI（端口 8001）+ 前端 Next.js（端口 3000）。提供**两种启动方式**——本地开发与 Docker 一键部署。

## 环境要求

- Python 3.10+
- Node.js 18+
- Windows / Linux / macOS
- 一个 LLM API Key（默认智谱 AI，可在 https://open.bigmodel.cn/ 免费申请）

## 方式一：本地开发启动

### 1. 配置后端环境变量

```bash
cd backend
cp .env.example .env       # Windows: copy .env.example .env
```

编辑 `backend/.env`，至少填入 `LLM_API_KEY`。其余配置有默认值，可选。完整变量见 [环境变量参考](#环境变量参考)。

> 也可不在 .env 配置，直接在前端「设置」面板填 API Key（存浏览器 localStorage，不写文件）。前端配置会覆盖后端默认值。

### 2. 启动后端

```bash
# 创建虚拟环境（首次）
python -m venv venv

# Windows
.\venv\Scripts\pip install -r requirements.txt
.\venv\Scripts\uvicorn main:app --host 127.0.0.1 --port 8001 --reload

# Linux / macOS
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 8001 --reload
```

看到 `Uvicorn running on http://127.0.0.1:8001` 即成功。

### 3. 启动前端

新开终端，回到项目根目录：

```bash
npm install
npm run dev
```

浏览器访问 **http://localhost:3000**。

### 4. Windows 一键启动

项目根目录有 `start.ps1`，PowerShell 直接运行：

```powershell
.\start.ps1
```

## 方式二：Docker 一键部署（推荐用于体验/部署）

无需本地安装 Python / Node 环境，一条命令启动前后端全套服务。

```bash
docker compose up
```

- 前端：http://localhost:3000
- 后端：http://localhost:8001

可选环境变量通过 `.env` 或 shell 注入：

```bash
AGENT_TOKEN=your_secret_token REDIS_URL=redis://redis:6379 docker compose up
```

仅重新构建某个服务：

```bash
docker compose build backend    # 重建后端
docker compose build frontend   # 重建前端
```

> Docker 模式下后端镜像含 libGL 依赖（Pillow 需要），前端用 Next.js standalone 产物，镜像体积较小。

## 环境变量参考

后端配置位于 `backend/.env`（从 `.env.example` 复制），通过环境变量读取：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `LLM_API_KEY` | LLM API 密钥（必填，也可在前端设置面板填） | — |
| `LLM_BASE_URL` | LLM API 地址 | `https://open.bigmodel.cn/api/paas/v4` |
| `LLM_MODEL` | 模型名称 | `glm-4-flash` |
| `MAX_STEPS` | Agent 最大推理步数 | `15` |
| `AGENT_TOKEN` | Agent 流接口鉴权 token（空=不鉴权；公网部署务必设置） | 空 |
| `REDIS_URL` | 会话持久化 Redis URL（空=内存存储，重启即丢） | 空 |
| `HOST` | 后端监听地址（默认仅 localhost；外网访问设 `0.0.0.0`） | `127.0.0.1` |
| `PORT` | 后端端口 | `8001` |
| `ALLOWED_ORIGINS` | CORS 允许的前端地址（逗号分隔） | `http://localhost:3000,http://127.0.0.1:3000` |

**支持的 LLM 提供商**（任意 OpenAI-compatible 接口）：

| 提供商 | BASE_URL | 推荐 Model |
|--------|----------|-----------|
| 智谱 AI | `https://open.bigmodel.cn/api/paas/v4` | `glm-4-flash` |
| Moonshot | `https://api.moonshot.cn/v1` | `moonshot-v1-8k` |
| OpenAI | `https://api.openai.com/v1` | `gpt-4o-mini` |
| DeepSeek | `https://api.deepseek.com` | `deepseek-chat` |

## 后端 API 一览

| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|------|
| POST | `/api/agent/stream` | 启动 Agent 任务，SSE 流式返回 | `AGENT_TOKEN`（可选） |
| GET | `/api/agent/session/{id}` | 查询会话状态 | — |
| GET | `/api/tools` | 列出所有工具（内置+自定义） | — |
| DELETE | `/api/tools/{name}` | 删除自定义工具 | — |
| POST | `/api/config/test` | 测试 LLM 配置连通性 | — |
| GET | `/api/admin/role` | 查询当前角色 | localhost / `ADMIN_TOKEN` |
| POST | `/api/admin/role` | 设置角色 | localhost / `ADMIN_TOKEN` |
| POST | `/api/admin/whitelist` | 增删命令白名单 | localhost / `ADMIN_TOKEN` |
| GET/POST | `/api/admin/capability` | 查询/设置模型能力（视觉支持） | localhost / `ADMIN_TOKEN` |
| POST/GET | `/api/admin/cleanup` | 触发/查询沙箱垃圾清理 | localhost / `ADMIN_TOKEN` |
| GET | `/health` | 健康检查 | — |

> 管理接口（`/api/admin/*`）默认仅允许 localhost 访问；远程访问需在请求头携带 `X-Admin-Token`。Agent 流接口默认不鉴权，设置 `AGENT_TOKEN` 后需携带 `X-Agent-Token`。

## 前端功能

启动后访问 http://localhost:3000，可用功能：

- **任务模板**：首页 6 个高频任务（分析项目结构 / 代码审查 / 生成 README 等），点击一键填入输入框
- **暗黑模式**：右上角 ☾/☀ 切换，跟随系统偏好并记忆选择
- **Timeline 可视化**：每步显示状态色徽章（成功/失败/运行中），点击标题折叠步骤，长内容自动折叠可展开
- **工具面板**：查看所有内置+自定义工具，支持删除自定义工具
- **配置面板**：填入 API Key 并测试连通性，配置存浏览器 localStorage

详细使用说明见 [docs/usage.md](docs/usage.md)。

## 生产部署建议

- **必须设置 `AGENT_TOKEN`**：公网暴露时 `/api/agent/stream` 会被滥用消耗 LLM 额度
- **建议设置 `REDIS_URL`**：内存存储重启即丢，Redis 支持多实例且会话 TTL 自动过期
- **设 `HOST=0.0.0.0`** 才能让容器/外网访问；本地开发保持 `127.0.0.1`
- **配置 `ALLOWED_ORIGINS`** 指向你的前端域名，收紧 CORS
- 默认速率限制：全局 30/min，Agent 接口 10/min，可防滥用

## 打包为单文件可执行（可选）

后端可用 PyInstaller 打包为单文件：

```bash
cd backend
pip install pyinstaller
pyinstaller -F -n evolvelab-server main.py
# 产物在 dist/evolvelab-server(.exe)
```

前端可用 `npm run build` 产出 `.next/`，配合 `next start` 或导出静态文件。
