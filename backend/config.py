import os
from pathlib import Path

# 项目根目录（限制文件操作范围）
PROJECT_ROOT = Path(__file__).parent.parent.resolve()

# LLM 配置：从环境变量读取，避免敏感信息硬编码进仓库
# 本地开发请在 backend/ 下创建 .env 并填入真实值（.env 已被 .gitignore 忽略）
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")
LLM_MODEL = os.getenv("LLM_MODEL", "glm-4-flash")

# Agent 配置
MAX_STEPS = int(os.getenv("MAX_STEPS", "15"))

# 截图保存目录
SCREENSHOT_DIR = PROJECT_ROOT / "screenshots"
SCREENSHOT_DIR.mkdir(exist_ok=True)
