# 运行与打包指南

## 环境要求

- Python 3.10+
- Node.js 18+
- Windows / Linux / macOS

## 1. 环境配置

LLM 配置通过环境变量读取（见 `backend/.env.example`）：
1. 复制 `backend/.env.example` 为 `backend/.env`
2. 填入你自己的 API Key（以智谱 AI 为例，可在 https://open.bigmodel.cn/ 申请）
3. 可选调整 `LLM_BASE_URL` / `LLM_MODEL` / `MAX_STEPS`

默认值（除 API Key 外）：
- BaseURL: `https://open.bigmodel.cn/api/paas/v4`（智谱AI）
- Model: `glm-4-flash`

## 2. 启动后端（Python FastAPI）

```bash
cd backend

# 创建虚拟环境（首次）
python -m venv venv

# Windows
.\venv\Scripts\pip install -r requirements.txt
.\venv\Scripts\uvicorn main:app --host 0.0.0.0 --port 8001 --reload

# Linux / macOS
# source venv/bin/activate
# pip install -r requirements.txt
# uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

后端接口：
- SSE Agent 流式接口：`POST http://localhost:8001/api/agent/stream`
- 健康检查：`GET http://localhost:8001/health`
- 权限管理：`POST /api/admin/role`、`POST /api/admin/whitelist`
- 能力探测：`GET /api/admin/capability`
- 沙箱垃圾清除：`POST /api/admin/cleanup`

## 3. 启动前端（Next.js）

```bash
# 在项目根目录
npm install
npm run dev
```

前端默认运行在 `http://localhost:3000`，已配置 CORS 允许跨域访问后端。

## 4. 打包部署

### 前端打包

```bash
npm run build
# 产物在 .next/ 目录，可配合 next start 或导出为静态文件
```

### 后端打包（单文件可执行）

```bash
cd backend
.\venv\Scripts\pip install pyinstaller
.\venv\Scripts\pyinstaller -F -n self-evolving-agent-server main.py
# 产物在 dist/self-evolving-agent-server.exe（Windows）
```

### Docker 打包（可选）

```dockerfile
# 阶段1：构建前端
FROM node:20-alpine AS frontend
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# 阶段2：Python 后端
FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install -r requirements.txt
COPY backend/ ./backend/
COPY --from=frontend /app/.next ./frontend/.next
ENV PYTHONPATH=/app/backend
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8001"]
```

构建与运行：

```bash
docker build -t self-evolving-agent .
docker run -p 8001:8001 self-evolving-agent
```

## 5. 快速启动脚本

Windows（PowerShell）：`start.ps1`

```powershell
.\start.ps1
```
