"""
utils/cache.py - Redis caching layer for Pasugo API

Provides a graceful-degradation cache: if Redis is unavailable the app
continues to work normally (every call falls through to the database).

Usage in routes:
    from utils.cache import cache

    # Simple get / set
    data = cache.get("key")
    cache.set("key", data, ttl=30)

    # Delete (invalidation)
    cache.delete("key")
    cache.delete_pattern("notifications:user:42:*")
"""

import json
import logging
import time
from typing import Optional, Any

import redis
from config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Redis connection (singleton with retry cooldown)
# ---------------------------------------------------------------------------

_redis_client: Optional[redis.Redis] = None
_redis_last_fail: float = 0.0       # epoch of last connection failure
_REDIS_RETRY_INTERVAL = 60.0        # seconds before retrying after a failure
_redis_warned: bool = False          # only warn once per cooldown period


def _get_redis() -> Optional[redis.Redis]:
    """Return a Redis client, or None if Redis is disabled / unreachable."""
    global _redis_client, _redis_last_fail, _redis_warned

    if not settings.REDIS_ENABLED:
        return None

    if _redis_client is not None:
        return _redis_client

    # Don't retry too fast after a failure
    now = time.time()
    if now - _redis_last_fail < _REDIS_RETRY_INTERVAL:
        return None

    try:
        _redis_client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,   # always return str, not bytes
            socket_connect_timeout=3,
            socket_timeout=2,
            retry_on_timeout=True,
        )
        # Quick ping to verify connectivity
        _redis_client.ping()
        logger.info("✅ Redis connected successfully")
        _redis_warned = False
        return _redis_client
    except Exception as e:
        _redis_last_fail = now
        _redis_client = None
        if not _redis_warned:
            logger.warning(f"⚠️ Redis unavailable – running without cache: {e}")
            _redis_warned = True
        return None


# ---------------------------------------------------------------------------
# Public cache API
# ---------------------------------------------------------------------------

class Cache:
    """Thin wrapper with graceful fallback when Redis is down."""

    # -- core -----------------------------------------------------------------

    def get(self, key: str) -> Optional[Any]:
        """Fetch a cached value. Returns None on miss or error."""
        r = _get_redis()
        if r is None:
            return None
        try:
            raw = r.get(key)
            if raw is None:
                return None
            return json.loads(raw)
        except Exception as e:
            logger.debug(f"Cache GET error for {key}: {e}")
            return None

    def set(self, key: str, value: Any, ttl: int = 30) -> bool:
        """Store a value with a TTL (seconds). Returns True on success."""
        r = _get_redis()
        if r is None:
            return False
        try:
            r.setex(key, ttl, json.dumps(value, default=str))
            return True
        except Exception as e:
            logger.debug(f"Cache SET error for {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Remove a single key."""
        r = _get_redis()
        if r is None:
            return False
        try:
            r.delete(key)
            return True
        except Exception as e:
            logger.debug(f"Cache DELETE error for {key}: {e}")
            return False

    def delete_pattern(self, pattern: str) -> int:
        """Remove all keys matching a glob pattern (e.g. 'user:42:*').

        Uses SCAN so it's safe for production (no KEYS command).
        Returns the number of deleted keys.
        """
        r = _get_redis()
        if r is None:
            return 0
        try:
            deleted = 0
            cursor = 0
            while True:
                cursor, keys = r.scan(cursor=cursor, match=pattern, count=100)
                if keys:
                    r.delete(*keys)
                    deleted += len(keys)
                if cursor == 0:
                    break
            return deleted
        except Exception as e:
            logger.debug(f"Cache DELETE_PATTERN error for {pattern}: {e}")
            return 0

    # -- helpers --------------------------------------------------------------

    def get_or_set(self, key: str, factory, ttl: int = 30) -> Any:
        """Return cached value or call *factory()* to compute & cache it."""
        cached = self.get(key)
        if cached is not None:
            return cached
        value = factory()
        self.set(key, value, ttl=ttl)
        return value

    # -- health ---------------------------------------------------------------

    def ping(self) -> bool:
        r = _get_redis()
        if r is None:
            return False
        try:
            return r.ping()
        except Exception:
            return False

    @property
    def enabled(self) -> bool:
        return settings.REDIS_ENABLED and _get_redis() is not None


# Module-level singleton – import this everywhere
cache = Cache()
