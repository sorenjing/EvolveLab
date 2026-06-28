"""
LLM 配置测试服务。
"""
import httpx
from logger import get_logger

log = get_logger("config_service")


async def test_config(api_key: str, base_url: str, model: str) -> dict[str, str]:
    """测试 LLM 配置是否可用，发送最小请求检查连通性。"""
    if not api_key:
        return {"ok": False, "message": "API Key 不能为空"}

    base = base_url.rstrip("/")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "hi"}],
        "max_tokens": 5,
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{base}/chat/completions",
                headers=headers,
                json=payload,
            )
        if resp.status_code == 200:
            return {"ok": True, "message": f"连接成功，模型 {model} 可用"}
        # 常见错误：401 鉴权失败、404 模型名错误、429 限流
        return {"ok": False, "message": f"HTTP {resp.status_code}: {resp.text[:200]}"}
    except httpx.ConnectError:
        return {"ok": False, "message": f"无法连接到 {base}，请检查地址"}
    except httpx.TimeoutException:
        return {"ok": False, "message": "请求超时，请检查网络或 Base URL"}
    except Exception as e:
        return {"ok": False, "message": f"测试失败: {e}"}
