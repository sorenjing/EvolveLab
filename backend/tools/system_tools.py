"""
系统级工具：执行命令、列出目录、搜索文件。
"""
import os
import subprocess
import fnmatch
from pathlib import Path
from typing import Any

from config import PROJECT_ROOT
from auth.permissions import get_permission_cache
from logger import get_logger

log = get_logger("tools.system")
_perm = get_permission_cache()

# 单条命令输出上限，防止撑爆 LLM 上下文
MAX_OUTPUT = 10000


def execute_command(command: str, cwd: str = "") -> str:
    """执行白名单内的命令，返回标准输出/错误。"""
    allowed, reason = _perm.check_command(command)
    if not allowed:
        log.warning("命令被拦截: %s (%s)", command[:80], reason)
        return f"[错误] 命令被拦截: {reason}"

    role = _perm.get_role_config()
    timeout = role.get("max_cmd_timeout", 60)

    run_dir = PROJECT_ROOT
    if cwd:
        try:
            run_dir = _perm.resolve_within_root(cwd, PROJECT_ROOT)
        except PermissionError as e:
            return f"[错误] cwd 越界: {e}"

    log.info("执行命令: %s (cwd=%s, timeout=%ss)", command[:100], run_dir, timeout)

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=run_dir,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
        out = (result.stdout or "").strip()
        err = (result.stderr or "").strip()

        # 截断超长输出，防止撑爆 LLM 上下文
        if len(out) > MAX_OUTPUT:
            out = out[:MAX_OUTPUT] + f"\n... [输出已截断，共 {len(out)} 字符]"
        if len(err) > MAX_OUTPUT:
            err = err[:MAX_OUTPUT] + f"\n... [错误输出已截断，共 {len(err)} 字符]"

        if result.returncode != 0:
            return f"[退出码 {result.returncode}] stdout:\n{out}\nstderr:\n{err}"
        return out or "[成功] 命令执行完毕，无输出"
    except subprocess.TimeoutExpired:
        return f"[错误] 命令超时（>{timeout}s）"
    except Exception as e:
        log.error("命令执行异常: %s", e)
        return f"[错误] 执行异常: {e}"


def list_files(path: str = ".") -> str:
    """列出目录内容（树状或列表）。"""
    try:
        target = _perm.resolve_within_root(path, PROJECT_ROOT)
        if not target.exists():
            return f"[错误] 目录不存在: {target}"
        if not target.is_dir():
            return f"[错误] 路径不是目录: {target}"

        lines = [f"目录: {target}"]
        for root, dirs, files in os.walk(target):
            level = len(Path(root).relative_to(target).parts)
            indent = "  " * level
            lines.append(f"{indent}{os.path.basename(root)}/")
            sub_indent = "  " * (level + 1)
            for f in files[:50]:  # 限制文件数
                lines.append(f"{sub_indent}{f}")
            if len(files) > 50:
                lines.append(f"{sub_indent}... 还有 {len(files)-50} 个文件")
            if level >= 2:
                del dirs[:]  # 只展开两层
        return "\n".join(lines)
    except PermissionError as e:
        return f"[错误] 权限拒绝: {e}"
    except Exception as e:
        return f"[错误] 列出失败: {e}"


def search_files(pattern: str, path: str = ".", by_content: bool = True) -> str:
    """按内容或文件名搜索文件。"""
    try:
        target = _perm.resolve_within_root(path, PROJECT_ROOT)
        if not target.exists():
            return f"[错误] 路径不存在: {target}"

        matches = []
        for root, dirs, files in os.walk(target):
            for filename in files:
                if filename.endswith(".bak"):
                    continue
                file_path = Path(root) / filename
                if not by_content:
                    if fnmatch.fnmatch(filename.lower(), pattern.lower()):
                        matches.append(str(file_path.relative_to(PROJECT_ROOT)))
                else:
                    try:
                        if file_path.stat().st_size > 2 * 1024 * 1024:
                            continue
                        text = file_path.read_text(encoding="utf-8", errors="replace")
                        if pattern in text:
                            snippet = text[text.find(pattern) : text.find(pattern) + 200]
                            matches.append(
                                f"{file_path.relative_to(PROJECT_ROOT)}:\n  ...{snippet}..."
                            )
                    except Exception:
                        continue
            if len(matches) > 50:
                break

        if not matches:
            return "未找到匹配结果"
        return "\n---\n".join(matches[:20])
    except PermissionError as e:
        return f"[错误] 权限拒绝: {e}"
    except Exception as e:
        return f"[错误] 搜索失败: {e}"
