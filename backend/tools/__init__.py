"""
工具注册表：集中注册所有可用工具，供 Agent Kernel 动态调用。
"""
from typing import Callable, Dict, Any
from . import file_tools, system_tools, screenshot, cleanup, safety, lifecycle
from . import registry

# 工具名称 -> 执行函数的映射
TOOLS: Dict[str, Callable[..., str]] = {
    "read_file": file_tools.read_file,
    "write_file": file_tools.write_file,
    "edit_file": file_tools.edit_file,
    "delete_file": file_tools.delete_file,
    "execute_command": system_tools.execute_command,
    "list_files": system_tools.list_files,
    "search_files": system_tools.search_files,
    "screenshot": screenshot.screenshot,
    "cleanup": cleanup.cleanup_all,
    # 自我修改安全层
    "create_snapshot": safety.create_snapshot,
    "verify_build": safety.verify_build,
    "rollback": safety.rollback,
    "list_snapshots": safety.list_snapshots,
    # 工具生命周期管理（Phase 3：Agent 自主扩展能力）
    "create_tool": lifecycle.create_tool,
    "list_tools": lifecycle.list_tools,
    "delete_tool": lifecycle.delete_tool,
}

# 工具元数据（供 Prompt 描述）
TOOLS_META: list[dict[str, Any]] = [
    {
        "name": "read_file",
        "description": "读取指定路径的文本文件内容。参数: {\"path\": \"文件路径\"}",
        "args": ["path"],
    },
    {
        "name": "write_file",
        "description": "向指定路径写入或覆盖文件。参数: {\"path\": \"文件路径\", \"content\": \"文件内容\"}",
        "args": ["path", "content"],
    },
    {
        "name": "edit_file",
        "description": "基于 search/replace 修改文件。参数: {\"path\", \"search\", \"replace\"}",
        "args": ["path", "search", "replace"],
    },
    {
        "name": "delete_file",
        "description": "删除文件（需高权限）。参数: {\"path\"}",
        "args": ["path"],
    },
    {
        "name": "execute_command",
        "description": "执行白名单内的命令。参数: {\"command\": \"命令字符串\", \"cwd?\": \"可选工作目录\"}",
        "args": ["command", "cwd"],
    },
    {
        "name": "list_files",
        "description": "列出目录内容。参数: {\"path?\": \"目录路径，默认当前目录\"}",
        "args": ["path"],
    },
    {
        "name": "search_files",
        "description": "搜索文件内容或文件名。参数: {\"pattern\", \"path?\", \"by_content?\": true/false}",
        "args": ["pattern", "path", "by_content"],
    },
    {
        "name": "screenshot",
        "description": "截取当前屏幕，返回 base64 图片数据。参数: {\"save_path?\", \"return_base64?\": true}",
        "args": ["save_path", "return_base64"],
    },
    {
        "name": "cleanup",
        "description": "清理沙箱垃圾（.bak备份、过期截图、pycache）。无需参数。",
        "args": [],
    },
    {
        "name": "create_snapshot",
        "description": "修改自身源码前创建 Git 快照。无需参数。返回快照ID。",
        "args": [],
    },
    {
        "name": "verify_build",
        "description": "运行构建验证（后端语法+前端类型）。无需参数。修改代码后必须调用。",
        "args": [],
    },
    {
        "name": "rollback",
        "description": "回滚到指定快照。参数: {\"snapshot_id\": \"快照ID\"}。验证失败时调用。",
        "args": ["snapshot_id"],
    },
    {
        "name": "list_snapshots",
        "description": "列出所有已创建的快照。无需参数。",
        "args": [],
    },
    {
        "name": "create_tool",
        "description": "创建自定义工具并注册（立即可用，持久化到本地）。参数: {\"name\": \"工具名(小写下划线)\", \"description\": \"描述\", \"args\": [\"参数名列表\"], \"code\": \"Python代码(可空,空则用模板)\"}。代码需定义 TOOL_NAME/TOOL_DESCRIPTION/TOOL_ARGS 和 run(**kwargs)->str。",
        "args": ["name", "description", "args", "code"],
    },
    {
        "name": "list_tools",
        "description": "列出所有可用工具（内置+自定义）。无需参数。用于查看当前能力边界。",
        "args": [],
    },
    {
        "name": "delete_tool",
        "description": "删除自定义工具（仅限自定义工具）。参数: {\"name\": \"工具名\"}。",
        "args": ["name"],
    },
    {
        "name": "final_answer",
        "description": "任务已完成，返回最终结果。参数: {\"result\": \"最终答案\"}",
        "args": ["result"],
    },
]

# 启动时加载所有自定义工具（从 backend/tools/custom/ 目录）
_loaded = registry.load_all_custom_tools(TOOLS, TOOLS_META)
if _loaded:
    print(f"[tools] 已加载 {_loaded} 个自定义工具")


def get_tool(name: str) -> Callable[..., str] | None:
    return TOOLS.get(name)


def list_tool_names() -> list[str]:
    return list(TOOLS.keys()) + ["final_answer"]
