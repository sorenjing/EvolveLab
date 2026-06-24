"""
自定义工具代码安全审查：基于 AST 扫描危险调用，防止 Agent 生成的代码执行恶意操作。

审查策略：
- 禁止系统命令执行（os.system / subprocess.*）
- 禁止动态执行（eval / exec / compile / __import__）
- 禁止文件系统破坏（shutil.rmtree）
- 禁止底层系统访问（ctypes / socket / threading）
- 允许网络请求（requests / httpx）和常规数据处理
"""
import ast
from logger import get_logger

log = get_logger("tools.code_safety")

# 禁止的函数调用：(模块名, 属性名)，None 表示内置函数
FORBIDDEN_CALLS: set[tuple[str | None, str]] = {
    # 系统命令执行
    ("os", "system"), ("os", "popen"), ("os", "exec"), ("os", "execl"),
    ("os", "execv"), ("os", "execvp"), ("os", "spawnl"), ("os", "spawnv"),
    ("subprocess", "Popen"), ("subprocess", "run"), ("subprocess", "call"),
    ("subprocess", "check_call"), ("subprocess", "check_output"),
    # 动态执行
    (None, "eval"), (None, "exec"), (None, "compile"), (None, "__import__"),
    # 文件系统破坏
    ("shutil", "rmtree"),
    # 底层系统
    ("ctypes", "CDLL"), ("ctypes", "WinDLL"), ("ctypes", "OleDLL"),
    ("importlib", "import_module"),
}

# 禁止导入的模块（顶层包名）
FORBIDDEN_IMPORTS: set[str] = {
    "ctypes", "multiprocessing", "threading", "socket",
    "signal", "pty", "fcntl",
}


def audit_code(code: str) -> tuple[bool, list[str]]:
    """
    审查 Python 代码是否包含危险操作。
    返回 (is_safe, reasons)。is_safe=False 时 reasons 列出违规项。
    """
    reasons: list[str] = []
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, [f"语法错误: {e}"]

    for node in ast.walk(tree):
        # 检测 import 语句
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top in FORBIDDEN_IMPORTS:
                    reasons.append(f"禁止导入模块: {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                top = node.module.split(".")[0]
                if top in FORBIDDEN_IMPORTS:
                    reasons.append(f"禁止导入模块: {node.module}")

        # 检测函数调用
        elif isinstance(node, ast.Call):
            call_name = _get_call_name(node.func)
            if call_name:
                if "." in call_name:
                    mod, attr = call_name.split(".", 1)
                    if (mod, attr) in FORBIDDEN_CALLS:
                        reasons.append(f"禁止调用: {call_name}")
                elif (None, call_name) in FORBIDDEN_CALLS:
                    reasons.append(f"禁止调用内置函数: {call_name}")

        # 检测 __import__ 属性访问
        elif isinstance(node, ast.Attribute):
            if node.attr == "__import__":
                reasons.append("禁止访问 __import__")

    is_safe = len(reasons) == 0
    if not is_safe:
        log.warning("代码审查未通过: %s", "; ".join(reasons))
    return is_safe, reasons


def _get_call_name(node: ast.expr) -> str | None:
    """从 Call.func 提取调用名（如 os.system / eval）。"""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _get_call_name(node.value)
        if base:
            return f"{base}.{node.attr}"
        return node.attr
    return None
