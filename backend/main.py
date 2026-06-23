"""
FastAPI 入口：Agent Evolution 后端服务。
提供 SSE 流式 Agent 接口、权限管理、LLM 能力探测。
"""
from dotenv import load_dotenv

# 在导入 config 之前加载 .env（默认从 backend/ 目录读取）
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import router

app = FastAPI(title="Agent Evolution Backend", version="0.1.0")

# 允许前端跨域（开发环境）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
