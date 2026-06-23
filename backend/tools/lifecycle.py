"""
工具生命周期管理：Agent 可通过这些函数创建、查看、删除自定义工具。
这是 Phase 3 的核心——Agent 能自主扩展自身能力。
"""
from typing import Any
from . import registry

# 自定义工具代码模板：Agent 创建工具时参考此结构
_TOOL_TEMPLATE = '''"""
自定义工具: {name}
描述: {description}
"""
import requests  # 按需替换为其他依赖


TOOL_NAME = "{name}"
TOOL_DESCRIPTION = "{description}"
TOOL_ARGS = {args}


def run(**kwargs) -> str:
    """
    工具执行入口。kwargs 的 key 与 TOOL_ARGS 一致。
    必须返回 str。
    """
    # TODO: 在此实现工具逻辑
    return "工具 {name} 执行完成（请替换为真实逻辑）"
'''


def create_tool(name: str, description: str, args: list[str], code: str = "") -> str:
    """
    创建一个自定义工具并注册到工具系统。
    创建后该工具立即可用，无需重启服务。
    参数:
      name: 工具名（小写字母+下划线，如 http_get）
      description: 工具描述（供 Agent 理解用途）
      args: 参数名列表，如 ["url", "method"]
      code: 工具代码（Python）。若为空则使用模板生成骨架。
    """
    from . import TOOLS, TOOLS_META
    if not code:
        code = _TOOL_TEMPLATE.format(
            name=name,
            description=description,
            args=args,
        )

    ok, msg = registry.register_tool(name, description, args, code, TOOLS, TOOLS_META)
    return f"[{'成功' if ok else '失败'}] {msg}"


def list_tools() -> str:
    """
    列出所有可用工具（内置 + 自定义）。
    """
    from . import TOOLS_META
    lines = ["=== 可用工具列表 ===", ""]
    # 内置工具
    builtin = [m for m in TOOLS_META if not m.get("custom")]
    custom = [m for m in TOOLS_META if m.get("custom")]
    lines.append(f"内置工具 ({len(builtin)}):")
    for m in builtin:
        args_str = ", ".join(m.get("args", [])) or "无"
        lines.append(f"  - {m['name']}({args_str}): {m['description'][:60]}")
    lines.append("")
    lines.append(f"自定义工具 ({len(custom)}):")
    if not custom:
        lines.append("  （暂无，使用 create_tool 创建）")
    else:
        for m in custom:
            args_str = ", ".join(m.get("args", [])) or "无"
            lines.append(f"  - {m['name']}({args_str}): {m['description'][:60]}")
    return "\n".join(lines)


def delete_tool(name: str) -> str:
    """
    删除一个自定义工具（仅限自定义工具，内置工具不可删除）。
    参数:
      name: 工具名
    """
    from . import TOOLS, TOOLS_META
    # 检查是否是自定义工具
    is_custom = any(m.get("name") == name and m.get("custom") for m in TOOLS_META)
    if not is_custom:
        return f"[失败] '{name}' 不是自定义工具或不存在（内置工具不可删除）"

    # 从注册表移除
    registry.unregister_tool(name, TOOLS, TOOLS_META)
    # 删除文件
    ok, msg = registry.delete_tool_file(name)
    prefix = "成功" if ok else "部分成功"
    return f"[{prefix}] 已移除工具 '{name}'，{msg}"
