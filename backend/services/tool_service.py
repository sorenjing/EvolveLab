"""
工具管理服务：列表与删除。
"""
from tools import TOOLS_META
from tools import lifecycle
from logger import get_logger

log = get_logger("tool_service")


def list_tools() -> dict:
    """列出所有可用工具（内置 + 自定义）。"""
    builtin = [m for m in TOOLS_META if not m.get("custom")]
    custom = [m for m in TOOLS_META if m.get("custom")]
    return {"builtin": builtin, "custom": custom, "total": len(TOOLS_META)}


def delete_tool(name: str) -> dict:
    """删除一个自定义工具，返回 {ok, message}。"""
    result = lifecycle.delete_tool(name)
    ok = result.startswith("[成功]")
    return {"ok": ok, "message": result}
