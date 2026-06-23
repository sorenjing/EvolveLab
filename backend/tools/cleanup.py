"""
沙箱垃圾清除模块。
负责清理 Agent 运行过程中产生的临时文件：
- .bak 备份文件
- 过期截图
- __pycache__ 目录
- .next 缓存
"""
import os
import time
from pathlib import Path
from typing import Any

from config import PROJECT_ROOT, SCREENSHOT_DIR


def cleanup_backups(max_age_hours: int = 24) -> dict[str, Any]:
    """清理超过 max_age_hours 小时的 .bak 备份文件。"""
    removed = []
    kept = []
    cutoff = time.time() - max_age_hours * 3600

    for root, dirs, files in os.walk(PROJECT_ROOT):
        # 跳过 node_modules / venv / .git
        dirs[:] = [d for d in dirs if d not in ("node_modules", "venv", ".git", "__pycache__")]
        for f in files:
            if f.endswith(".bak"):
                fp = Path(root) / f
                try:
                    if fp.stat().st_mtime < cutoff:
                        fp.unlink()
                        removed.append(str(fp.relative_to(PROJECT_ROOT)))
                    else:
                        kept.append(str(fp.relative_to(PROJECT_ROOT)))
                except Exception:
                    pass

    return {"removed": removed, "kept": kept, "removed_count": len(removed)}


def cleanup_screenshots(max_age_hours: int = 2, max_count: int = 20) -> dict[str, Any]:
    """清理过期或超量的截图文件。"""
    removed = []

    if not SCREENSHOT_DIR.exists():
        return {"removed": [], "removed_count": 0}

    # 获取所有截图，按修改时间排序
    screenshots = sorted(
        SCREENSHOT_DIR.glob("*.png"),
        key=lambda p: p.stat().st_mtime,
    )

    cutoff = time.time() - max_age_hours * 3600

    # 先删过期的
    for fp in screenshots:
        if fp.stat().st_mtime < cutoff:
            try:
                fp.unlink()
                removed.append(str(fp.name))
            except Exception:
                pass

    # 如果仍超量，删最旧的
    remaining = sorted(
        SCREENSHOT_DIR.glob("*.png"),
        key=lambda p: p.stat().st_mtime,
    )
    while len(remaining) > max_count:
        oldest = remaining.pop(0)
        try:
            oldest.unlink()
            removed.append(str(oldest.name))
        except Exception:
            pass

    return {"removed": removed, "removed_count": len(removed)}


def cleanup_pycache() -> dict[str, Any]:
    """清理所有 __pycache__ 目录。"""
    removed = []

    for root, dirs, files in os.walk(PROJECT_ROOT):
        dirs[:] = [d for d in dirs if d not in ("node_modules", "venv", ".git")]
        if "__pycache__" in dirs:
            cache_dir = Path(root) / "__pycache__"
            try:
                for f in cache_dir.iterdir():
                    f.unlink()
                cache_dir.rmdir()
                removed.append(str(cache_dir.relative_to(PROJECT_ROOT)))
            except Exception:
                pass
            dirs.remove("__pycache__")

    return {"removed": removed, "removed_count": len(removed)}


def cleanup_all() -> dict[str, Any]:
    """执行全部清理操作。"""
    return {
        "backups": cleanup_backups(),
        "screenshots": cleanup_screenshots(),
        "pycache": cleanup_pycache(),
    }
