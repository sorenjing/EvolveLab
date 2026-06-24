"""
Agent 上下文压缩模块。
当历史步骤过多时，对旧步骤进行摘要压缩，但严格遵守以下约束：
- 禁止丢失任务 todo 及其完成状态
- 禁止丢失任务整体完成状态
- 保留关键工具调用结果（文件路径、命令输出摘要）
"""
from typing import Any


# 触发压缩的步数阈值
COMPRESS_THRESHOLD = 8
# 压缩后保留的近期步数（不压缩最近 N 步）
KEEP_RECENT_STEPS = 4


def extract_todos(history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """从历史步骤中提取所有 todo 项及其状态。"""
    todos = []
    for h in history:
        obs = h.get("observation", "")
        thought = h.get("thought", "")
        # 检测 todo 模式：模型在 thought 或 observation 中提到的任务清单
        text = f"{thought}\n{obs}"
        # 简单提取包含 [x] / [ ] /已完成/未完成 的行
        for line in text.splitlines():
            line = line.strip()
            if any(marker in line for marker in ["[x]", "[ ]", "[X]", "已完成", "未完成", "TODO:", "DONE:"]):
                todos.append({
                    "step": h.get("step", 0),
                    "content": line,
                    "context": h.get("action", ""),
                })
    return todos


def compress_history(history: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    压缩历史步骤。
    返回 (compressed_summary, recent_steps)。
    - compressed_summary: 被压缩的旧步骤的摘要（作为单条伪步骤）
    - recent_steps: 保留的近期原始步骤
    """
    if len(history) <= COMPRESS_THRESHOLD:
        return [], history

    # 分割：旧步骤压缩，近期步骤保留
    old_steps = history[:-KEEP_RECENT_STEPS]
    recent_steps = history[-KEEP_RECENT_STEPS:]

    # 提取 todo 项（绝对不能丢失）
    todos = extract_todos(old_steps)

    # 构建压缩摘要
    summary_lines = ["[上下文压缩 - 保留关键信息]", ""]

    # 1. 保留 todo 状态
    if todos:
        summary_lines.append("任务进度（不可丢失）：")
        for t in todos:
            summary_lines.append(f"  - {t['content']}")
        summary_lines.append("")

    # 2. 保留关键文件操作结果
    summary_lines.append("已完成的操作摘要：")
    for h in old_steps:
        summary_lines.append(_summarize_step(h))

    # 3. 保留任务完成状态
    has_final = any(h.get("action") == "final_answer" for h in old_steps)
    if has_final:
        summary_lines.insert(0, "[重要] 任务已在之前的步骤中完成！")

    compressed = [{
        "thought": "\n".join(summary_lines),
        "action": "context_compressed",
        "observation": f"已压缩 {len(old_steps)} 步历史，保留 todo 和完成状态。",
    }]

    return compressed, recent_steps


def build_compressed_user_prompt(
    task: str,
    history: list[dict[str, Any]],
    todos: list[dict[str, Any]] | None = None,
) -> str:
    """
    构建压缩后的 user prompt。
    即使历史被压缩，todo 和完成状态始终完整保留。
    """
    lines = [f"任务：{task}", ""]

    # 始终显式输出 todo 状态（即使未压缩）
    if todos:
        lines.append("当前任务进度（不可遗忘）：")
        for t in todos:
            lines.append(f"  - {t['content']}")
        lines.append("")

    lines.append("历史步骤：")
    if not history:
        lines.append("（无）")

    for i, h in enumerate(history, 1):
        lines.append(f"Step {i}:")
        lines.append(f"  Thought: {h.get('thought', '')}")
        lines.append(f"  Action: {h.get('action', '')}")
        # 压缩步骤的 observation 可能很长，截断
        obs = h.get("observation", "")
        if h.get("action") == "context_compressed":
            lines.append(f"  Observation: {obs}")
        else:
            lines.append(f"  Observation: {obs[:500]}")

    lines.extend(["", "请输出下一步的 JSON："])
    return "\n".join(lines)


def _summarize_step(h: dict[str, Any]) -> str:
    """将单步历史压缩为一行结构化摘要，按工具类型保留关键信息。"""
    action = h.get("action", "")
    thought = h.get("thought", "")
    obs = h.get("observation", "")
    is_error = "[错误]" in obs

    # 失败操作保留更多错误信息（可能需要重试决策）
    if is_error:
        return f"  Step({action})[失败]: {thought[:80]} | 错误: {obs[:200]}"

    # 按工具类型提取关键信息
    if action == "read_file":
        # 文件内容不保留（太长），只标记已读
        return f"  Step(read_file)[成功]: {thought[:80]}（文件内容已省略）"
    if action in ("write_file", "edit_file"):
        return f"  Step({action})[成功]: {obs[:120]}"
    if action == "execute_command":
        return f"  Step(execute_command)[成功]: {thought[:80]} | 输出: {obs[:150]}"
    if action == "list_files":
        first_line = obs.split("\n")[0] if obs else ""
        return f"  Step(list_files)[成功]: {first_line}"
    if action in ("create_snapshot", "create_tool", "delete_tool"):
        return f"  Step({action})[成功]: {obs[:120]}"
    if action == "final_answer":
        return f"  Step(final_answer): {obs[:150]}"
    return f"  Step({action})[成功]: {thought[:80]} | 结果: {obs[:150]}"
