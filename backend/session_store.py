"""
会话存储：Redis 持久化（优先）+ 内存 dict 降级（本地开发）。
通过 REDIS_URL 环境变量切换。未配置或连接失败时自动降级为内存存储。
"""
import json
import time
import threading
from typing import Any

from config import REDIS_URL
from logger import get_logger

log = get_logger("session_store")

SESSION_TTL = 3600      # 会话保留时长（秒），默认 1 小时
SESSION_MAX = 100       # 内存存储最多保留的会话数量


class SessionStore:
    """会话存储抽象基类。"""

    def save(self, session_id: str, data: dict[str, Any]) -> None:
        raise NotImplementedError

    def get(self, session_id: str) -> dict[str, Any] | None:
        raise NotImplementedError


class MemorySessionStore(SessionStore):
    """内存存储：进程内 dict，重启即丢。适合本地开发。"""

    def __init__(self):
        self._cache: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def save(self, session_id: str, data: dict[str, Any]) -> None:
        with self._lock:
            data["_ts"] = time.time()
            self._cache[session_id] = data
            self._prune()

    def get(self, session_id: str) -> dict[str, Any] | None:
        with self._lock:
            return self._cache.get(session_id)

    def _prune(self) -> None:
        """清理过期或超量的会话。"""
        now = time.time()
        expired = [
            sid for sid, d in self._cache.items()
            if now - d.get("_ts", 0) > SESSION_TTL
        ]
        for sid in expired:
            del self._cache[sid]
        if len(self._cache) > SESSION_MAX:
            sorted_items = sorted(self._cache.items(), key=lambda x: x[1].get("_ts", 0))
            for sid, _ in sorted_items[:len(self._cache) - SESSION_MAX]:
                del self._cache[sid]


class RedisSessionStore(SessionStore):
    """Redis 存储：持久化，重启不丢，支持多实例。TTL 自动过期。"""

    def __init__(self, url: str):
        import redis
        self._client = redis.Redis.from_url(url, decode_responses=True)
        self._prefix = "evolvelab:session:"
        log.info("会话存储使用 Redis: %s", url)

    def save(self, session_id: str, data: dict[str, Any]) -> None:
        data["_ts"] = time.time()
        self._client.setex(
            f"{self._prefix}{session_id}",
            SESSION_TTL,
            json.dumps(data, ensure_ascii=False),
        )

    def get(self, session_id: str) -> dict[str, Any] | None:
        raw = self._client.get(f"{self._prefix}{session_id}")
        if raw is None:
            return None
        return json.loads(raw)


# 全局单例：根据 REDIS_URL 自动选择实现，连接失败降级内存
_store: SessionStore | None = None
_store_lock = threading.Lock()


def get_session_store() -> SessionStore:
    global _store
    if _store is None:
        with _store_lock:
            if _store is None:
                if REDIS_URL:
                    try:
                        _store = RedisSessionStore(REDIS_URL)
                    except Exception as e:
                        log.warning("Redis 连接失败，降级为内存存储: %s", e)
                        _store = MemorySessionStore()
                else:
                    _store = MemorySessionStore()
    return _store
