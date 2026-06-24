"""
code_safety 模块的单元测试。
运行方式：
    cd backend && python -m pytest tests/test_code_safety.py -v
    或直接：python tests/test_code_safety.py
"""
import sys
import os

# 将 backend 目录加入 path，使 from tools.xxx 可用
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.code_safety import audit_code


# ---------- 安全代码应通过 ----------

def test_safe_code():
    code = "def add(a, b):\n    return a + b\nresult = add(1, 2)\nprint(result)"
    is_safe, reasons = audit_code(code)
    assert is_safe, f"安全代码不应被拦截: {reasons}"
    assert reasons == []


def test_safe_math():
    code = "import math\nmath.sqrt(16)"
    is_safe, reasons = audit_code(code)
    assert is_safe, f"math 应是安全的: {reasons}"


def test_safe_json():
    code = "import json\njson.dumps({'a': 1})"
    is_safe, reasons = audit_code(code)
    assert is_safe, f"json 应是安全的: {reasons}"


def test_open_allowed():
    """open 内置函数默认允许（文件权限由 registry 层白名单处理）。"""
    code = "f = open('file.txt', 'r')\nf.close()"
    is_safe, reasons = audit_code(code)
    assert is_safe, f"open 不应被 code_safety 拦截: {reasons}"


# ---------- 危险调用应被拦截 ----------

def test_os_system_call():
    code = "import os\nos.system('ls')"
    is_safe, reasons = audit_code(code)
    assert not is_safe
    assert any("os.system" in r for r in reasons)


def test_os_popen_call():
    code = "import os\nos.popen('whoami')"
    is_safe, reasons = audit_code(code)
    assert not is_safe
    assert any("os.popen" in r for r in reasons)


def test_subprocess_run_call():
    code = "import subprocess\nsubprocess.run(['ls'])"
    is_safe, reasons = audit_code(code)
    assert not is_safe
    assert any("subprocess.run" in r for r in reasons)


def test_subprocess_popen_call():
    code = "import subprocess\nsubprocess.Popen(['ls'])"
    is_safe, reasons = audit_code(code)
    assert not is_safe


def test_eval_call():
    code = "eval('1+1')"
    is_safe, reasons = audit_code(code)
    assert not is_safe
    assert any("eval" in r for r in reasons)


def test_exec_call():
    code = "exec('print(1)')"
    is_safe, reasons = audit_code(code)
    assert not is_safe
    assert any("exec" in r for r in reasons)


def test_compile_call():
    code = "compile('1+1', '<s>', 'eval')"
    is_safe, reasons = audit_code(code)
    assert not is_safe
    assert any("compile" in r for r in reasons)


def test_shutil_rmtree():
    code = "import shutil\nshutil.rmtree('/tmp/x')"
    is_safe, reasons = audit_code(code)
    assert not is_safe
    assert any("shutil.rmtree" in r for r in reasons)


def test_importlib_import_module():
    code = "import importlib\nimportlib.import_module('os')"
    is_safe, reasons = audit_code(code)
    assert not is_safe
    assert any("importlib.import_module" in r for r in reasons)


# ---------- 危险导入应被拦截 ----------

def test_import_ctypes():
    code = "import ctypes"
    is_safe, reasons = audit_code(code)
    assert not is_safe
    assert any("ctypes" in r for r in reasons)


def test_import_threading():
    code = "import threading"
    is_safe, reasons = audit_code(code)
    assert not is_safe
    assert any("threading" in r for r in reasons)


def test_import_socket():
    code = "import socket"
    is_safe, reasons = audit_code(code)
    assert not is_safe
    assert any("socket" in r for r in reasons)


def test_import_multiprocessing():
    code = "import multiprocessing"
    is_safe, reasons = audit_code(code)
    assert not is_safe


def test_from_import_forbidden():
    """from ... import 形式也应检测顶层包。"""
    code = "from threading import Thread"
    is_safe, reasons = audit_code(code)
    assert not is_safe
    assert any("threading" in r for r in reasons)


# ---------- __import__ 与语法错误 ----------

def test_dunder_import_call():
    code = "__import__('os')"
    is_safe, reasons = audit_code(code)
    assert not is_safe


def test_syntax_error():
    code = "def broken(:"
    is_safe, reasons = audit_code(code)
    assert not is_safe
    assert any("语法错误" in r for r in reasons)


def test_empty_code():
    code = ""
    is_safe, reasons = audit_code(code)
    assert is_safe
    assert reasons == []


# ---------- 直接运行入口 ----------

if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            print(f"  PASS  {test.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR {test.__name__}: {type(e).__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed, {len(tests)} total")
    sys.exit(1 if failed else 0)
