"""
管理接口认证：localhost 限制 + Token 认证。
- 默认仅允许 127.0.0.1 / ::1 访问 /api/admin/*
- 若设置了 ADMIN_TOKEN 环境变量，则额外要求请求头 X-Admin-Token 匹配
- 外网访问需同时满足：设置 ADMIN_TOKEN 且请求带正确 token
"""
import os
from fastapi import Request, HTTPException
from fastapi.security import APIKeyHeader

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")
_admin_token_header = APIKeyHeader(name="X-Admin-Token", auto_error=False)


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
