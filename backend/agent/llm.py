"""
LLM 调用封装：支持文本与图片输入（若模型支持视觉）。
网络错误 / 5xx 自动重试（指数退避，最多 2 次）。
"""
import asyncio
import json
import httpx
from typing import Any

from config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
from auth.capability import get_llm_capability
from logger import get_logger

log = get_logger("agent.llm")


class LLMClient:
    def __init__(self, model: str = LLM_MODEL, api_key: str = LLM_API_KEY, base_url: str = LLM_BASE_URL):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.capability = get_llm_capability(model)
        self.client = httpx.AsyncClient(timeout=120.0)

    async def chat(self, system_prompt: str, user_prompt: str, image_url: str | None = None) -> dict[str, Any]:
        """
        调用 LLM，返回解析后的 JSON dict。
        若 image_url 提供且模型支持视觉，则加入图片输入。
        网络错误 / 5xx 自动重试（指数退避，最多 2 次）。
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        content: list[dict[str, Any]] | str = user_prompt
        if image_url and self.capability.supports_vision:
            content = [
                {"type": "text", "text": user_prompt},
                {"type": "image_url", "image_url": {"url": image_url}},
            ]

        messages.append({"role": "user", "content": content})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 2048,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        url = f"{self.base_url}/chat/completions"
        max_retries = 2
        last_exc: Exception | None = None

        for attempt in range(max_retries + 1):
            try:
                resp = await self.client.post(url, headers=headers, json=payload)
                # 5xx 服务端错误，可重试
                if resp.status_code >= 500:
                    last_exc = httpx.HTTPStatusError(
                        f"HTTP {resp.status_code}", request=resp.request, response=resp
                    )
                    if attempt < max_retries:
                        wait = 2 ** attempt
                        log.warning("LLM 返回 %d，%ds 后重试 (attempt %d/%d)",
                                    resp.status_code, wait, attempt + 1, max_retries)
                        await asyncio.sleep(wait)
                        continue
                    raise last_exc
                # 4xx 客户端错误（鉴权/参数），不重试
                resp.raise_for_status()
                data = resp.json()
                raw = data["choices"][0]["message"]["content"]
                return self._extract_json(raw)
            except (httpx.ConnectError, httpx.TimeoutException, httpx.TransportError) as e:
                last_exc = e
                if attempt < max_retries:
                    wait = 2 ** attempt
                    log.warning("LLM 网络异常 %s，%ds 后重试 (attempt %d/%d)",
                                type(e).__name__, wait, attempt + 1, max_retries)
                    await asyncio.sleep(wait)
                    continue
                raise

        # 理论上不会到达
        raise last_exc or RuntimeError("LLM 调用失败")

    def _extract_json(self, text: str) -> dict[str, Any]:
        """从模型输出中提取 JSON（支持嵌套对象）。"""
        text = text.strip()
        # 去除 markdown 代码块
        if text.startswith("```"):
            lines = text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 用栈匹配最外层 { ... }，正确处理嵌套与字符串内的花括号
        start = text.find("{")
        if start == -1:
            return self._fallback(text)

        depth = 0
        in_string = False
        escape = False
        end = -1
        for i in range(start, len(text)):
            ch = text[i]
            if escape:
                escape = False
                continue
            if ch == "\\":
                escape = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i
                    break

        if end != -1:
            candidate = text[start:end + 1]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                pass
        return self._fallback(text)

    @staticmethod
    def _fallback(text: str) -> dict[str, Any]:
        return {
            "thought": "解析失败",
            "action": "final_answer",
            "actionInput": {"result": f"模型输出无法解析为 JSON: {text[:200]}"},
        }

    async def close(self):
        await self.client.aclose()
