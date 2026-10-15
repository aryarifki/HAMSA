"""
Unified Two-Tier Cache Layer (L1 In-Memory LRU + L2 Optional Redis) with TTL for Hamsa.
Maintains 100% zero-dependency compatibility by defaulting to thread-safe L1 memory cache,
while automatically leveraging Redis if available in the environment.
"""

from __future__ import annotations

import functools
import hashlib
import json
import os
import time
from collections import OrderedDict
from threading import Lock
from typing import Any, Callable, Optional


def _get_optional_redis() -> Optional[Any]:
    """Attempts to connect to Redis if redis-py is installed and REDIS_HOST is accessible."""
    redis_host = os.environ.get("REDIS_HOST", "127.0.0.1")
    redis_port = int(os.environ.get("REDIS_PORT", "6379"))
    redis_db = int(os.environ.get("REDIS_DB", "0"))

    try:
        import redis  # type: ignore

        client = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            decode_responses=True,
            socket_timeout=1.5,
            socket_connect_timeout=1.5,
        )
        client.ping()
        return client
    except Exception:
        return None


class TTLCache:
    """
    Thread-safe Two-Tier Cache (L1 Memory LRU + L2 Redis Fallback) with TTL.
    Provides sub-millisecond retrieval (0ms) from local memory while persisting
    cross-process / cross-restart state when Redis is active.
    """

    def __init__(
        self,
        maxsize: int = 256,
        ttl_seconds: float = 300.0,
        redis_prefix: str = "hamsa_cache",
        enable_redis: bool = True,
    ) -> None:
        self.maxsize = maxsize
        self.ttl_seconds = ttl_seconds
        self.redis_prefix = redis_prefix
        self._cache: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self._lock = Lock()
        self._redis = _get_optional_redis() if enable_redis else None

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            # 1. Check L1 Memory Cache (0ms)
            if key in self._cache:
                timestamp, val = self._cache[key]
                if (time.time() - timestamp) <= self.ttl_seconds:
                    self._cache.move_to_end(key)
                    return val
                else:
                    del self._cache[key]

            # 2. Check L2 Redis if L1 missed
            if self._redis:
                try:
                    rk = f"{self.redis_prefix}:{key}"
                    raw = self._redis.get(rk)
                    if raw is not None:
                        val = json.loads(raw)
                        # Backfill into L1 memory for subsequent requests
                        self._cache[key] = (time.time(), val)
                        return val
                except Exception:
                    pass

            return None

    def set(self, key: str, val: Any) -> None:
        with self._lock:
            now = time.time()
            if key in self._cache:
                del self._cache[key]
            elif len(self._cache) >= self.maxsize:
                self._cache.popitem(last=False)  # Evict oldest LRU item
            self._cache[key] = (now, val)

            # Persist to L2 Redis
            if self._redis:
                try:
                    rk = f"{self.redis_prefix}:{key}"
                    payload = json.dumps(val, default=str)
                    self._redis.set(rk, payload, ex=int(self.ttl_seconds))
                except Exception:
                    pass

    def delete(self, key: str) -> bool:
        with self._lock:
            deleted = False
            if key in self._cache:
                del self._cache[key]
                deleted = True
            if self._redis:
                try:
                    rk = f"{self.redis_prefix}:{key}"
                    self._redis.delete(rk)
                    deleted = True
                except Exception:
                    pass
            return deleted

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
            if self._redis:
                try:
                    keys = self._redis.keys(f"{self.redis_prefix}:*")
                    if keys:
                        self._redis.delete(*keys)
                except Exception:
                    pass

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "l1_memory_size": len(self._cache),
                "l1_maxsize": self.maxsize,
                "ttl_seconds": self.ttl_seconds,
                "l2_redis_connected": self._redis is not None,
            }


# Global instance for OSINT scan and graph query caching
GLOBAL_CACHE = TTLCache(maxsize=512, ttl_seconds=600.0, redis_prefix="hamsa")


def cached(ttl_seconds: float = 300.0, prefix: str = "fn"):
    """Decorator to cache function or coroutine results in TTLCache."""

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(fn)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            raw_key = f"{prefix}:{fn.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
            cache_key = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
            cached_val = GLOBAL_CACHE.get(cache_key)
            if cached_val is not None:
                return cached_val
            result = await fn(*args, **kwargs)
            GLOBAL_CACHE.set(cache_key, result)
            return result

        @functools.wraps(fn)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            raw_key = f"{prefix}:{fn.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
            cache_key = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
            cached_val = GLOBAL_CACHE.get(cache_key)
            if cached_val is not None:
                return cached_val
            result = fn(*args, **kwargs)
            GLOBAL_CACHE.set(cache_key, result)
            return result

        import asyncio

        if asyncio.iscoroutinefunction(fn):
            return async_wrapper
        return sync_wrapper

    return decorator
