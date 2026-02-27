"""Redis Cache Manager for Zakera AI Chat Agent.

Provides comprehensive caching functionality with:
- Connection pooling
- Automatic retry logic
- Cache warming
- Metrics collection
- Circuit breaker pattern
"""

import asyncio
import json
import logging
from datetime import timedelta
from typing import Any, Optional, Dict, List, Callable
from functools import wraps
import hashlib

import redis.asyncio as redis
from redis.asyncio import Redis, ConnectionPool
from redis.exceptions import RedisError, ConnectionError, TimeoutError

from ..config import settings


logger = logging.getLogger(__name__)


class CacheManager:
    """Manages Redis caching with connection pooling and error handling."""

    def __init__(
        self,
        redis_url: str = None,
        max_connections: int = 50,
        socket_timeout: int = 5,
        socket_connect_timeout: int = 5,
        retry_on_timeout: bool = True,
        max_retries: int = 3,
    ):
        """Initialize cache manager.

        Args:
            redis_url: Redis connection URL
            max_connections: Maximum connection pool size
            socket_timeout: Socket timeout in seconds
            socket_connect_timeout: Connection timeout in seconds
            retry_on_timeout: Whether to retry on timeout
            max_retries: Maximum number of retries
        """
        self.redis_url = redis_url or settings.REDIS_URL
        self.max_retries = max_retries

        # Create connection pool
        self.pool = ConnectionPool.from_url(
            self.redis_url,
            max_connections=max_connections,
            socket_timeout=socket_timeout,
            socket_connect_timeout=socket_connect_timeout,
            retry_on_timeout=retry_on_timeout,
            decode_responses=True,
        )

        self.redis: Optional[Redis] = None
        self._is_connected = False

        # Cache statistics
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "errors": 0,
        }

        # Circuit breaker
        self.circuit_breaker = {
            "failures": 0,
            "threshold": 5,
            "timeout": 60,
            "last_failure": None,
            "is_open": False,
        }

    async def connect(self) -> bool:
        """Establish Redis connection.

        Returns:
            True if connected successfully
        """
        try:
            self.redis = Redis(connection_pool=self.pool)
            await self.redis.ping()
            self._is_connected = True
            logger.info("Redis connection established")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self._is_connected = False
            return False

    async def disconnect(self):
        """Close Redis connection."""
        if self.redis:
            await self.redis.close()
            await self.pool.disconnect()
            self._is_connected = False
            logger.info("Redis connection closed")

    async def is_healthy(self) -> bool:
        """Check if Redis connection is healthy.

        Returns:
            True if healthy
        """
        if not self._is_connected or not self.redis:
            return False

        try:
            await self.redis.ping()
            return True
        except Exception:
            return False

    def _check_circuit_breaker(self) -> bool:
        """Check if circuit breaker is open.

        Returns:
            True if circuit is open (requests should be blocked)
        """
        if not self.circuit_breaker["is_open"]:
            return False

        # Check if timeout has passed
        import time
        if time.time() - self.circuit_breaker["last_failure"] > self.circuit_breaker["timeout"]:
            self.circuit_breaker["is_open"] = False
            self.circuit_breaker["failures"] = 0
            logger.info("Circuit breaker reset")
            return False

        return True

    def _record_failure(self):
        """Record a cache operation failure."""
        import time
        self.circuit_breaker["failures"] += 1
        self.circuit_breaker["last_failure"] = time.time()

        if self.circuit_breaker["failures"] >= self.circuit_breaker["threshold"]:
            self.circuit_breaker["is_open"] = True
            logger.warning("Circuit breaker opened due to repeated failures")

    def _record_success(self):
        """Record a successful cache operation."""
        if self.circuit_breaker["failures"] > 0:
            self.circuit_breaker["failures"] = max(0, self.circuit_breaker["failures"] - 1)

    async def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache.

        Args:
            key: Cache key
            default: Default value if key not found

        Returns:
            Cached value or default
        """
        if self._check_circuit_breaker():
            logger.debug("Circuit breaker open, skipping cache get")
            return default

        try:
            if not await self.is_healthy():
                await self.connect()

            value = await self.redis.get(key)

            if value is None:
                self.stats["misses"] += 1
                return default

            self.stats["hits"] += 1
            self._record_success()

            # Try to deserialize JSON
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value

        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            self.stats["errors"] += 1
            self._record_failure()
            return default

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        nx: bool = False,
        xx: bool = False,
    ) -> bool:
        """Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            nx: Only set if key doesn't exist
            xx: Only set if key exists

        Returns:
            True if successful
        """
        if self._check_circuit_breaker():
            logger.debug("Circuit breaker open, skipping cache set")
            return False

        try:
            if not await self.is_healthy():
                await self.connect()

            # Serialize value if needed
            if not isinstance(value, str):
                value = json.dumps(value)

            result = await self.redis.set(
                key,
                value,
                ex=ttl,
                nx=nx,
                xx=xx,
            )

            if result:
                self.stats["sets"] += 1
                self._record_success()

            return bool(result)

        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            self.stats["errors"] += 1
            self._record_failure()
            return False

    async def delete(self, *keys: str) -> int:
        """Delete keys from cache.

        Args:
            keys: Keys to delete

        Returns:
            Number of keys deleted
        """
        if self._check_circuit_breaker():
            return 0

        try:
            if not await self.is_healthy():
                await self.connect()

            result = await self.redis.delete(*keys)
            self.stats["deletes"] += result
            self._record_success()
            return result

        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            self.stats["errors"] += 1
            self._record_failure()
            return 0

    async def exists(self, *keys: str) -> int:
        """Check if keys exist.

        Args:
            keys: Keys to check

        Returns:
            Number of existing keys
        """
        try:
            if not await self.is_healthy():
                return 0

            return await self.redis.exists(*keys)

        except Exception as e:
            logger.error(f"Cache exists error: {e}")
            return 0

    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration time for key.

        Args:
            key: Cache key
            ttl: Time to live in seconds

        Returns:
            True if successful
        """
        try:
            if not await self.is_healthy():
                return False

            return await self.redis.expire(key, ttl)

        except Exception as e:
            logger.error(f"Cache expire error: {e}")
            return False

    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment value.

        Args:
            key: Cache key
            amount: Amount to increment

        Returns:
            New value or None
        """
        try:
            if not await self.is_healthy():
                return None

            return await self.redis.incrby(key, amount)

        except Exception as e:
            logger.error(f"Cache increment error: {e}")
            return None

    async def get_many(self, *keys: str) -> List[Any]:
        """Get multiple values.

        Args:
            keys: Cache keys

        Returns:
            List of values
        """
        try:
            if not await self.is_healthy():
                return [None] * len(keys)

            values = await self.redis.mget(*keys)

            result = []
            for value in values:
                if value is None:
                    result.append(None)
                    self.stats["misses"] += 1
                else:
                    self.stats["hits"] += 1
                    try:
                        result.append(json.loads(value))
                    except (json.JSONDecodeError, TypeError):
                        result.append(value)

            return result

        except Exception as e:
            logger.error(f"Cache get_many error: {e}")
            return [None] * len(keys)

    async def set_many(self, mapping: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Set multiple values.

        Args:
            mapping: Dictionary of key-value pairs
            ttl: Time to live in seconds

        Returns:
            True if successful
        """
        try:
            if not await self.is_healthy():
                return False

            # Serialize values
            serialized = {
                k: json.dumps(v) if not isinstance(v, str) else v
                for k, v in mapping.items()
            }

            # Use pipeline for efficiency
            async with self.redis.pipeline() as pipe:
                await pipe.mset(serialized)

                if ttl:
                    for key in serialized.keys():
                        await pipe.expire(key, ttl)

                await pipe.execute()

            self.stats["sets"] += len(mapping)
            return True

        except Exception as e:
            logger.error(f"Cache set_many error: {e}")
            return False

    async def clear_pattern(self, pattern: str) -> int:
        """Clear keys matching pattern.

        Args:
            pattern: Key pattern (e.g., "user:*")

        Returns:
            Number of keys deleted
        """
        try:
            if not await self.is_healthy():
                return 0

            keys = []
            async for key in self.redis.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                return await self.delete(*keys)

            return 0

        except Exception as e:
            logger.error(f"Cache clear_pattern error: {e}")
            return 0

    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Statistics dictionary
        """
        stats = self.stats.copy()

        # Calculate hit rate
        total_reads = stats["hits"] + stats["misses"]
        stats["hit_rate"] = stats["hits"] / total_reads if total_reads > 0 else 0

        # Get Redis info
        try:
            if await self.is_healthy():
                info = await self.redis.info("stats")
                stats["redis_stats"] = {
                    "total_commands_processed": info.get("total_commands_processed", 0),
                    "keyspace_hits": info.get("keyspace_hits", 0),
                    "keyspace_misses": info.get("keyspace_misses", 0),
                }
        except Exception as e:
            logger.error(f"Error getting Redis stats: {e}")

        return stats

    def generate_key(self, *parts: str, prefix: str = "zakera") -> str:
        """Generate cache key from parts.

        Args:
            parts: Key components
            prefix: Key prefix

        Returns:
            Generated cache key
        """
        key_parts = [prefix] + list(parts)
        return ":".join(str(p) for p in key_parts)

    def hash_key(self, data: Any) -> str:
        """Generate hash for cache key.

        Args:
            data: Data to hash

        Returns:
            Hash string
        """
        if isinstance(data, str):
            content = data
        else:
            content = json.dumps(data, sort_keys=True)

        return hashlib.sha256(content.encode()).hexdigest()[:16]


# Global cache manager instance
cache_manager = CacheManager()
