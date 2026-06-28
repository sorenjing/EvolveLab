"""
统一异常处理：自定义异常类 + FastAPI 全局异常处理器。
成功响应保持原格式（不破坏前端），仅统一错误响应为 {code, message}。
"""
from fastapi import Request
from fastapi.responses import JSONResponse
from logger import get_logger

log = get_logger("exceptions")


# ---------- 自定义异常 ----------

class AppError(Exception):
    """应用异常基类。"""
    status_code: int = 400
    code: str = "app_error"

    def __init__(self, message: str, code: str | None = None, status_code: int | None = None):
        self.message = message
        if code:
            self.code = code
        if status_code:
            self.status_code = status_code
        super().__init__(message)


class SessionNotFound(AppError):
    code = "session_not_found"
    status_code = 404


class PermissionDenied(AppError):
    code = "permission_denied"
    status_code = 403


# ---------- 全局异常处理器 ----------

async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    log.warning("AppError: code=%s msg=%s path=%s", exc.code, exc.message, request.url.path)
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "message": exc.message},
    )


def register_exception_handlers(app) -> None:
    """注册全局异常处理器到 FastAPI 应用。

    只注册 AppError，避免干扰 FastAPI 默认的 HTTPException / 参数校验处理。
    """
    app.add_exception_handler(AppError, app_error_handler)
