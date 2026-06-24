"""
管理接口认证：localhost 限制 + Token 认证。
- 默认仅允许 127.0.0.1 / ::1 访问 /api/admin/*
- 若设置了 ADMIN_TOKEN 环境变量，则额外要求请求头 X-Admin-Token 匹配
- 外网访问需同时满足：设置 ADMIN_TOKEN 且请求带正确 token

Agent 流接口鉴权：
- 未设置 AGENT_TOKEN 时不鉴权（本地开发默认）
- 设置后 /api/agent/stream 必须携带正确的 X-Agent-Token
"""
import os
from fastapi import Request, HTTPException
from fastapi.security import APIKeyHeader

from config import AGENT_TOKEN
from logger import get_logger

log = get_logger("auth")

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")
_admin_token_header = APIKeyHeader(name="X-Admin-Token", auto_error=False)
_agent_token_header = APIKeyHeader(name="X-Agent-Token", auto_error=False)


def _is_localhost(request: Request) -> bool:
    """判断请求是否来自 localhost。"""
    client = request.client
    if client is None:
        return False
    host = client.host
    return host in ("127.0.0.1", "::1", "localhost")


async def require_admin(request: Request) -> None:
    """
    管理接口认证依赖：
    1. localhost 请求直接放行（本地开发无风险）
    2. 非 localhost 请求必须携带正确的 X-Admin-Token
    """
    if _is_localhost(request):
        return  # 本地访问放行

    # 非 localhost：必须有 token 才能访问
    if not ADMIN_TOKEN:
        raise HTTPException(
            status_code=403,
            detail="管理接口仅限本地访问。如需远程访问，请在后端 .env 中设置 ADMIN_TOKEN 环境变量。",
        )

    token = await _admin_token_header(request)
    if token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="无效的管理 Token")

    return


async def require_agent(request: Request) -> None:
    """
    Agent 流接口鉴权：
    - 未设置 AGENT_TOKEN：不鉴权（本地开发默认，向后兼容）
    - 设置了 AGENT_TOKEN：所有请求必须携带正确的 X-Agent-Token
    """
    if not AGENT_TOKEN:
        return  # 未配置 token，不鉴权

    token = await _agent_token_header(request)
    if token != AGENT_TOKEN:
        log.warning("Agent 接口鉴权失败，来源: %s", request.client.host if request.client else "unknown")
        raise HTTPException(status_code=403, detail="无效的 Agent Token（需在请求头携带 X-Agent-Token）")

    return
