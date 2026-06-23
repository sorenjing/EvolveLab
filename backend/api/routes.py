"""
FastAPI 路由：提供 SSE 流式 Agent 接口，以及工具/权限管理接口。
"""
import json
import asyncio
import time
from typing import Any

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agent.kernel import AgentKernel, AgentEvent
from auth.permissions import get_permission_cache
from auth.capability import get_llm_capability
from tools.cleanup import cleanup_all
from config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL

router = APIRouter()

# 内存中的会话缓存（生产环境建议换 Redis）
session_cache: dict[str, dict[str, Any]] = {}
SESSION_TTL = 3600      # 会话保留时长（秒），默认 1 小时
SESSION_MAX = 100       # 最多保留的会话数量


def _prune_sessions() -> None:
    """清理过期或超量的会话，防止内存无限增长。"""
    now = time.time()
    # 1. 删除超过 TTL 的会话
    expired = [
        sid for sid, data in session_cache.items()
        if now - data.get("_ts", 0) > SESSION_TTL
    ]
    for sid in expired:
        del session_cache[sid]
    # 2. 超量时按最后更新时间删除最旧的
    if len(session_cache) > SESSION_MAX:
        sorted_items = sorted(session_cache.items(), key=lambda x: x[1].get("_ts", 0))
        for sid, _ in sorted_items[:len(session_cache) - SESSION_MAX]:
            del session_cache[sid]


def _save_session(session_id: str, data: dict[str, Any]) -> None:
    data["_ts"] = time.time()
    session_cache[session_id] = data
    _prune_sessions()


class TaskRequest(BaseModel):
    task: str
    role: str = "standard"
    model: str = LLM_MODEL
    api_key: str = LLM_API_KEY
    base_url: str = LLM_BASE_URL


@router.post("/agent/stream")
async def agent_stream(req: TaskRequest):
    """启动 Agent 任务，以 SSE 流式返回执行轨迹。"""
    kernel = AgentKernel(
        task=req.task,
        role=req.role,
        model=req.model,
        api_key=req.api_key,
        base_url=req.base_url,
    )
    _save_session(kernel.session_id, kernel.to_dict())

    async def event_generator():
        try:
            async for ev in kernel.run():
                # SSE 格式
                yield f"data: {json.dumps({'type': ev.type, 'step': ev.step, 'payload': ev.payload}, ensure_ascii=False)}\n\n"
                _save_session(kernel.session_id, kernel.to_dict())
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'step': kernel.step, 'payload': {'message': str(e)}}, ensure_ascii=False)}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/agent/session/{session_id}")
async def get_session(session_id: str):
    """查询会话状态。"""
    data = session_cache.get(session_id)
    if not data:
        raise HTTPException(status_code=404, detail="Session not found")
    return data


# ---------- 权限管理路由 ----------

class RoleUpdate(BaseModel):
    role: str
    config: dict[str, Any] | None = None


@router.post("/admin/role")
async def set_role(body: RoleUpdate):
    perm = get_permission_cache()
    perm.set_role(body.role)
    return {"role": body.role, "config": perm.get_role_config(body.role)}


@router.get("/admin/role")
async def get_role():
    perm = get_permission_cache()
    return {"role": perm.get_role(), "config": perm.get_role_config()}


class WhitelistUpdate(BaseModel):
    command_prefix: str
    action: str  # add | remove


@router.post("/admin/whitelist")
async def update_whitelist(body: WhitelistUpdate):
    perm = get_permission_cache()
    if body.action == "add":
        perm.add_whitelist(body.command_prefix)
    elif body.action == "remove":
        perm.remove_whitelist(body.command_prefix)
    else:
        raise HTTPException(status_code=400, detail="action must be add or remove")
    return {"whitelist": sorted(perm._cmd_whitelist)}


# ---------- LLM 能力探测 ----------

@router.get("/admin/capability")
async def get_capability(model: str = LLM_MODEL):
    cap = get_llm_capability(model)
    return {
        "model": model,
        "supports_vision": cap.supports_vision,
    }


@router.post("/admin/capability")
async def set_capability(model: str, vision: bool):
    cap = get_llm_capability(model)
    cap.force_set(vision)
    return {"model": model, "supports_vision": cap.supports_vision}


# ---------- 沙箱垃圾清除 ----------

@router.post("/admin/cleanup")
async def run_cleanup():
    """手动触发沙箱垃圾清除。"""
    result = cleanup_all()
    return result


@router.get("/admin/cleanup")
async def cleanup_status():
    """查看可清理的垃圾文件数量（不实际删除）。"""
    from tools.cleanup import cleanup_backups, cleanup_screenshots
    backups = cleanup_backups(max_age_hours=0)  # 列出所有
    screenshots = cleanup_screenshots(max_age_hours=0, max_count=999)
    return {
        "backups_count": len(backups.get("kept", [])),
        "screenshots_count": len(screenshots.get("removed", [])),
    }
