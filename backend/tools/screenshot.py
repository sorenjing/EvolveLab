"""
截图工具：捕获当前屏幕并保存，返回图片路径或 base64（供 LLM 视觉推理使用）。
仅在检测到 LLM 支持视觉输入时启用。无 GUI 环境自动降级返回提示。
"""
import base64
import os
import time
from pathlib import Path

try:
    import pyautogui
    from PIL import Image
    PYAUTOGUI_AVAILABLE = True
except Exception:
    PYAUTOGUI_AVAILABLE = False

from config import SCREENSHOT_DIR
from logger import get_logger

log = get_logger("tools.screenshot")


def _is_headless() -> bool:
    """检测当前是否为无 GUI 环境（无法截屏）。"""
    # Linux: 无 DISPLAY 环境变量
    if os.name == "posix" and not os.environ.get("DISPLAY"):
        return True
    # Windows: 检测桌面会话
    if os.name == "nt":
        try:
            import ctypes
            if ctypes.windll.user32.GetDesktopWindow() == 0:
                return True
        except Exception:
            return True
    return False


def screenshot(save_path: str = "", return_base64: bool = True) -> str:
    """
    截取当前屏幕。
    - save_path: 可选自定义保存路径（相对于 screenshots/）
    - return_base64: True 返回 base64 数据 URL，False 返回本地路径
    """
    if not PYAUTOGUI_AVAILABLE:
        return "[错误] 截图依赖未安装（pyautogui / PIL），请执行: pip install pyautogui pillow"

    if _is_headless():
        log.warning("当前为无 GUI 环境，截图不可用")
        return "[错误] 当前为无 GUI 环境（headless），截图不可用。请在有桌面环境的机器上运行。"

    try:
        img = pyautogui.screenshot()
        if not save_path:
            save_path = f"screenshot_{int(time.time())}.png"
        target = SCREENSHOT_DIR / save_path
        target.parent.mkdir(parents=True, exist_ok=True)
        img.save(target)

        if return_base64:
            with open(target, "rb") as f:
                data = base64.b64encode(f.read()).decode("utf-8")
            return f"data:image/png;base64,{data}"
        return str(target)
    except Exception as e:
        log.error("截图失败: %s", e)
        return f"[错误] 截图失败: {e}"
