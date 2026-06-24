"""
FastAPI 路由：提供 SSE 流式 Agent 接口，以及工具/权限管理接口。
"""
import json
import asyncio
from typing import Any

from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agent.kernel import AgentKernel, AgentEvent
from auth.permissions import get_permission_cache
from auth.capability import get_llm_capability
from auth.admin import require_admin, require_agent
from tools.cleanup import cleanup_all
from config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, AGENT_TOKEN
from logger import get_logger
import httpx

log = get_logger("api.routes")

# 速率限制器（从 main 注入，避免循环导入）
from slowapi import Limiter
from slowapi.util import get_remote_address
limiter = Limiter(key_func=get_remote_address)

router = APIRouter()

from session_store import get_session_store

_session_store = get_session_store()


class TaskRequest(BaseModel):
    task: str
    role: str = "standard"
    model: str = LLM_MODEL
    api_key: str = LLM_API_KEY
    base_url: str = LLM_BASE_URL


@router.post("/agent/stream")
@limiter.limit("10/minute")
async def agent_stream(request: Request, req: TaskRequest, _: None = Depends(require_agent)):
    """启动 Agent 任务，以 SSE 流式返回执行轨迹。"""
    log.info("Agent 任务启动: task=%r role=%s model=%s", req.task[:80], req.role, req.model)
    kernel = AgentKernel(
        task=req.task,
        role=req.role,
        model=req.model,
        api_key=req.api_key,
        base_url=req.base_url,
    )
    _session_store.save(kernel.session_id, kernel.to_dict())

    async def event_generator():
        try:
            async for ev in kernel.run():
                # SSE 格式
                yield f"data: {json.dumps({'type': ev.type, 'step': ev.step, 'payload': ev.payload}, ensure_ascii=False)}\n\n"
                _session_store.save(kernel.session_id, kernel.to_dict())
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
    data = _session_store.get(session_id)
    if not data:
        raise HTTPException(status_code=404, detail="Session not found")
    return data


# ---------- 权限管理路由 ----------

class RoleUpdate(BaseModel):
    role: str
    config: dict[str, Any] | None = None


@router.post("/admin/role", dependencies=[Depends(require_admin)])
async def set_role(body: RoleUpdate):
    perm = get_permission_cache()
    perm.set_role(body.role)
    return {"role": body.role, "config": perm.get_role_config(body.role)}


@router.get("/admin/role", dependencies=[Depends(require_admin)])
async def get_role():
    perm = get_permission_cache()
    return {"role": perm.get_role(), "config": perm.get_role_config()}


class WhitelistUpdate(BaseModel):
    command_prefix: str
    action: str  # add | remove


@router.post("/admin/whitelist", dependencies=[Depends(require_admin)])
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

@router.get("/admin/capability", dependencies=[Depends(require_admin)])
async def get_capability(model: str = LLM_MODEL):
    cap = get_llm_capability(model)
    return {
        "model": model,
        "supports_vision": cap.supports_vision,
    }


@router.post("/admin/capability", dependencies=[Depends(require_admin)])
async def set_capability(model: str, vision: bool):
    cap = get_llm_capability(model)
    cap.force_set(vision)
    return {"model": model, "supports_vision": cap.supports_vision}


# ---------- 沙箱垃圾清除 ----------

@router.post("/admin/cleanup", dependencies=[Depends(require_admin)])
async def run_cleanup():
    """手动触发沙箱垃圾清除。"""
    result = cleanup_all()
    return result


@router.get("/admin/cleanup", dependencies=[Depends(require_admin)])
async def cleanup_status():
    """查看可清理的垃圾文件数量（不实际删除）。"""
    from tools.cleanup import cleanup_backups, cleanup_screenshots
    backups = cleanup_backups(max_age_hours=0)  # 列出所有
    screenshots = cleanup_screenshots(max_age_hours=0, max_count=999)
    return {
        "backups_count": len(backups.get("kept", [])),
        "screenshots_count": len(screenshots.get("removed", [])),
    }


# ---------- LLM 配置测试 ----------

class ConfigTestRequest(BaseModel):
    api_key: str = ""
    base_url: str = LLM_BASE_URL
    model: str = LLM_MODEL


@router.get("/tools")
async def list_all_tools():
    """列出所有可用工具（内置 + 自定义），供前端展示。"""
    from tools import TOOLS_META
    builtin = [m for m in TOOLS_META if not m.get("custom")]
    custom = [m for m in TOOLS_META if m.get("custom")]
    return {
        "builtin": builtin,
        "custom": custom,
        "total": len(TOOLS_META),
    }


@router.delete("/tools/{name}")
async def delete_custom_tool(name: str):
    """删除一个自定义工具。"""
    from tools import lifecycle
    result = lifecycle.delete_tool(name)
    ok = result.startswith("[成功]")
    return {"ok": ok, "message": result}


@router.post("/config/test")
async def test_llm_config(req: ConfigTestRequest):
    """
    测试 LLM 配置是否可用。
    发送一个最小请求，检查 API Key 和连通性。
    """
    if not req.api_key:
        return {"ok": False, "message": "API Key 不能为空"}

    base = req.base_url.rstrip("/")
    headers = {
        "Authorization": f"Bearer {req.api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": req.model,
        "messages": [{"role": "user", "content": "hi"}],
        "max_tokens": 5,
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{base}/chat/completions",
                headers=headers,
                json=payload,
            )
        if resp.status_code == 200:
            return {"ok": True, "message": f"连接成功，模型 {req.model} 可用"}
        # 常见错误：401 鉴权失败、404 模型名错误、429 限流
        return {"ok": False, "message": f"HTTP {resp.status_code}: {resp.text[:200]}"}
    except httpx.ConnectError:
        return {"ok": False, "message": f"无法连接到 {base}，请检查地址"}
    except httpx.TimeoutException:
        return {"ok": False, "message": "请求超时，请检查网络或 Base URL"}
    except Exception as e:
        return {"ok": False, "message": f"测试失败: {e}"}
