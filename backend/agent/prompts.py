"""
System Prompt 模板：强制模型输出 JSON 格式的 Thought / Action。
"""
import json
from typing import Any


def build_system_prompt(tools_meta: list[dict[str, Any]], allow_screenshot: bool) -> str:
    """根据可用工具动态构建 System Prompt。"""
    lines = [
        "你是一个能使用工具的 Agent。你必须按以下格式思考并行动：",
        "",
        '{',
        '  "thought": "分析当前情况，决定下一步（用中文）",',
        '  "action": "工具名或 final_answer",',
        '  "actionInput": { ...参数... }',
        '}',
        "",
        "可用工具：",
    ]
    for t in tools_meta:
        if t["name"] == "screenshot" and not allow_screenshot:
            continue
        lines.append(f"- {t['name']}: {t['description']}")

    lines.extend([
        "",
        "规则：",
        "- 必须输出合法 JSON，不含其他文字（不要 markdown 代码块）。",
        "- 若任务已完成，action 填 'final_answer'，actionInput 填 {\"result\": \"答案\"}。",
        "- 不确定文件内容时，先用 read_file 查看，不要假设。",
        "- 不要重复执行已经成功的相同操作。",
        "- 命令执行工具受白名单限制，如被拒绝请换用文件工具。",
        "",
        "自我修改安全流程（修改本项目源码时必须遵守）：",
        "1. 修改前：调用 create_snapshot 创建快照，记住返回的快照ID",
        "2. 修改：用 write_file 或 edit_file 修改文件",
        "3. 验证：调用 verify_build 检查修改是否破坏项目",
        "4. 若验证失败：调用 rollback 回滚到快照，不要带着错误继续",
    ])
    return "\n".join(lines)


def build_user_prompt(task: str, history: list[dict[str, Any]]) -> str:
    """构建用户 Prompt，包含任务和历史步骤。"""
    lines = [f"任务：{task}", "", "历史步骤："]
    if not history:
        lines.append("（无）")
    for i, h in enumerate(history, 1):
        lines.append(f"Step {i}:")
        lines.append(f"  Thought: {h.get('thought', '')}")
        lines.append(f"  Action: {h.get('action', '')}")
        lines.append(f"  Observation: {h.get('observation', '')}")
    lines.extend(["", "请输出下一步的 JSON："])
    return "\n".join(lines)
