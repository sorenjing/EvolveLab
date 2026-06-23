"""
自我修改安全层：Git 快照 + 构建验证 + 回滚。
确保 Agent 修改自身源码后能自动验证，失败则回滚。

工作流：
1. create_snapshot()  —— 修改前创建快照（保存 HEAD + 工作区差异）
2. write_file/edit_file —— Agent 修改文件
3. verify_build()     —— 运行构建验证（py_compile + tsc）
4. rollback(snapshot_id) —— 验证失败时回滚到快照
"""
import subprocess
import threading
from typing import Any

from config import PROJECT_ROOT


class SafetyManager:
    """管理 Git 快照、构建验证与回滚。线程安全。"""

    def __init__(self):
        self.root = PROJECT_ROOT
        self._lock = threading.Lock()
        # snapshot_id -> {"head": str, "stash": str | None}
        self._snapshots: dict[str, dict[str, Any]] = {}

    # ---------- Git 辅助 ----------

    def _git(self, *args: str) -> tuple[int, str, str]:
        """执行 git 命令，返回 (returncode, stdout, stderr)。"""
        result = subprocess.run(
            ["git"] + list(args),
            cwd=self.root,
            capture_output=True,
            text=True,
            timeout=30,
            encoding="utf-8",
            errors="replace",
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()

    def _is_git_repo(self) -> bool:
        rc, _, _ = self._git("rev-parse", "--is-inside-work-tree")
        return rc == 0

    # ---------- 快照管理 ----------

    def create_snapshot(self) -> str:
        """
        创建快照，返回 snapshot_id。
        快照保存当前 HEAD 和工作区差异（通过 git stash create）。
        """
        if not self._is_git_repo():
            return "[错误] 当前目录不是 git 仓库，无法创建快照"

        # 记录 HEAD commit
        rc, head, err = self._git("rev-parse", "HEAD")
        if rc != 0:
            return f"[错误] 获取 HEAD 失败: {err}"

        # git stash create：创建反映当前工作区差异的 commit 对象，但不改变工作区
        # 工作区干净时返回空字符串（正常情况）
        rc, stash_hash, _ = self._git("stash", "create")

        # 记录当前 untracked 文件列表，用于 rollback 时删除 Agent 新建的文件
        rc, untracked_out, _ = self._git("ls-files", "--others", "--exclude-standard")
        untracked = set(filter(None, untracked_out.split("\n"))) if untracked_out else set()

        snapshot_id = head[:8]
        with self._lock:
            self._snapshots[snapshot_id] = {
                "head": head,
                "stash": stash_hash if stash_hash else None,
                "untracked": untracked,
            }
        return f"[成功] 快照已创建，ID: {snapshot_id}（修改代码后请调用 verify_build 验证，失败则 rollback 回滚）"

    def list_snapshots(self) -> str:
        """列出所有已创建的快照。"""
        with self._lock:
            if not self._snapshots:
                return "当前无快照"
            lines = ["已创建的快照："]
            for sid, snap in self._snapshots.items():
                has_stash = "有工作区修改" if snap["stash"] else "工作区干净"
                lines.append(f"  - {sid} (HEAD: {snap['head'][:8]}, {has_stash})")
            return "\n".join(lines)

    def rollback(self, snapshot_id: str) -> str:
        """
        回滚到指定快照。
        1. git checkout -- . 丢弃 Agent 对已跟踪文件的修改
        2. 删除 Agent 新建的 untracked 文件（快照后新增的）
        3. 若快照有 stash，git stash apply 恢复修改前的工作区状态
        """
        with self._lock:
            snapshot = self._snapshots.get(snapshot_id)
        if snapshot is None:
            return f"[错误] 快照不存在: {snapshot_id}。可用: {list(self._snapshots.keys())}"

        if not self._is_git_repo():
            return "[错误] 不是 git 仓库"

        # 1. 丢弃已跟踪文件的工作区修改（Agent 的修改）
        rc, _, err = self._git("checkout", "--", ".")
        if rc != 0:
            return f"[错误] 丢弃修改失败: {err}"

        # 2. 删除 Agent 新建的 untracked 文件
        rc, current_out, _ = self._git("ls-files", "--others", "--exclude-standard")
        current_untracked = set(filter(None, current_out.split("\n"))) if current_out else set()
        old_untracked = snapshot.get("untracked", set())
        new_files = current_untracked - old_untracked
        removed_new = []
        for f in new_files:
            fp = self.root / f
            if fp.exists() and fp.is_file():
                try:
                    fp.unlink()
                    removed_new.append(f)
                except Exception:
                    pass

        # 3. 恢复快照时的工作区状态（如果有未提交的修改）
        stash = snapshot.get("stash")
        if stash:
            rc, _, err = self._git("stash", "apply", stash)
            if rc != 0:
                return f"[警告] 已丢弃 Agent 修改并删除 {len(removed_new)} 个新文件，但恢复原工作区状态失败: {err}"

        msg = f"[成功] 已回滚到快照 {snapshot_id}"
        if removed_new:
            msg += f"（删除了 {len(removed_new)} 个 Agent 新建的文件）"
        return msg

    # ---------- 构建验证 ----------

    def verify_build(self) -> str:
        """
        运行构建验证，检查 Agent 的修改是否破坏了项目。
        - 后端：python -m compileall（语法检查）
        - 前端：npx tsc --noEmit（类型检查，如果 node_modules 存在）
        """
        errors = []

        # 1. 后端 Python 语法检查
        backend_dir = self.root / "backend"
        if backend_dir.exists():
            try:
                result = subprocess.run(
                    ["python", "-m", "compileall", str(backend_dir), "-q"],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    encoding="utf-8",
                    errors="replace",
                )
                if result.returncode != 0:
                    err_msg = result.stderr.strip() or result.stdout.strip()
                    errors.append(f"后端语法错误:\n{err_msg[:500]}")
            except subprocess.TimeoutExpired:
                errors.append("后端语法检查超时（>60s）")
            except Exception as e:
                errors.append(f"后端检查异常: {e}")

        # 2. 前端 TypeScript 类型检查
        if (self.root / "node_modules" / ".bin" / "tsc").exists() or (self.root / "node_modules").exists():
            try:
                result = subprocess.run(
                    ["npx", "tsc", "--noEmit"],
                    cwd=self.root,
                    capture_output=True,
                    text=True,
                    timeout=120,
                    encoding="utf-8",
                    errors="replace",
                )
                if result.returncode != 0:
                    err_msg = result.stdout.strip() or result.stderr.strip()
                    errors.append(f"前端类型错误:\n{err_msg[:500]}")
            except subprocess.TimeoutExpired:
                errors.append("前端类型检查超时（>120s），跳过")
            except Exception as e:
                # tsc 不可用不算失败，只跳过
                pass

        if not errors:
            return "[成功] 构建验证通过，修改安全"
        return "[失败] 构建验证未通过，建议 rollback 回滚:\n" + "\n---\n".join(errors)


# 模块级单例
_safety_manager: SafetyManager | None = None
_safety_lock = threading.Lock()


def get_safety_manager() -> SafetyManager:
    global _safety_manager
    if _safety_manager is None:
        with _safety_lock:
            if _safety_manager is None:
                _safety_manager = SafetyManager()
    return _safety_manager


# ---------- 工具函数（供 Agent 调用） ----------

def create_snapshot() -> str:
    """修改自身源码前创建快照。无需参数。"""
    return get_safety_manager().create_snapshot()


def verify_build() -> str:
    """运行构建验证（后端语法 + 前端类型）。无需参数。"""
    return get_safety_manager().verify_build()


def rollback(snapshot_id: str) -> str:
    """回滚到指定快照。参数: {"snapshot_id": "快照ID"}"""
    return get_safety_manager().rollback(snapshot_id)


def list_snapshots() -> str:
    """列出所有快照。无需参数。"""
    return get_safety_manager().list_snapshots()
