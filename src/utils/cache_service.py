"""Redis cache service for conversation memory optimization.

This module provides a Redis-based caching layer for conversation data
to improve performance and reduce database load.
"""

import asyncio
import json
import logging
import zlib
from typing import Optional, Dict, List, Any, Union
from datetime import timedelta
from functools import wraps

import redis.asyncio as redis
from opentelemetry import trace, metrics

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)
meter = metrics.get_meter(__name__)

# Metrics
cache_hits = meter.create_counter(
    "cache_hits_total",
    description="Total number of cache hits",
    unit="1",
)

cache_misses = meter.create_counter(
    "cache_misses_total",
    description="Total number of cache misses",
    unit="1",
)

cache_errors = meter.create_counter(
    "cache_errors_total",
    description="Total number of cache errors",
    unit="1",
)


class CacheConfig:
    """Redis cache configuration."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        max_connections: int = 50,
        socket_timeout: int = 5,
        socket_connect_timeout: int = 5,
        decode_responses: bool = False,
        enable_compression: bool = True,
        compression_threshold: int = 1024,  # bytes
    ):
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.max_connections = max_connections
        self.socket_timeout = socket_timeout
        self.socket_connect_timeout = socket_connect_timeout
        self.decode_responses = decode_responses
        self.enable_compression = enable_compression
        self.compression_threshold = compression_threshold


class RedisCache:
    """Redis cache service for conversation data."""

    # Cache key prefixes
    CONVERSATION_PREFIX = "conv:"
    MEMORY_PREFIX = "mem:"
    USER_PREFIX = "user:"
    SESSION_PREFIX = "session:"

    # Default TTLs
    DEFAULT_TTL = timedelta(hours=24)
    CONVERSATION_TTL = timedelta(days=7)
    MEMORY_TTL = timedelta(hours=6)
    SESSION_TTL = timedelta(hours=1)

    def __init__(self, config: Optional[CacheConfig] = None):
        """Initialize Redis cache service.

        Args:
            config: Cache configuration
        """
        self.config = config or CacheConfig()
        self._pool: Optional[redis.ConnectionPool] = None
        self._client: Optional[redis.Redis] = None
        self._connected = False

    async def connect(self) -> None:
        """Establish Redis connection."""
        try:
            self._pool = redis.ConnectionPool(
                host=self.config.host,
                port=self.config.port,
                db=self.config.db,
                password=self.config.password,
                max_connections=self.config.max_connections,
                socket_timeout=self.config.socket_timeout,
                socket_connect_timeout=self.config.socket_connect_timeout,
                decode_responses=self.config.decode_responses,
            )

            self._client = redis.Redis(connection_pool=self._pool)

            # Test connection
            await self._client.ping()
            self._connected = True
            logger.info(f"Connected to Redis at {self.config.host}:{self.config.port}")

        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self._connected = False
            raise

    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.close()
        if self._pool:
            await self._pool.disconnect()
        self._connected = False
        logger.info("Disconnected from Redis")

    def _compress(self, data: str) -> bytes:
        """Compress data if above threshold.

        Args:
            data: String data to compress

        Returns:
            Compressed bytes or original string encoded
        """
        encoded = data.encode('utf-8')
        if self.config.enable_compression and len(encoded) > self.config.compression_threshold:
            compressed = zlib.compress(encoded)
            logger.debug(f"Compressed {len(encoded)} bytes to {len(compressed)} bytes")
            return b'COMPRESSED:' + compressed
        return encoded

    def _decompress(self, data: bytes) -> str:
        """Decompress data if compressed.

        Args:
            data: Bytes to decompress

        Returns:
            Decompressed string
        """
        if data.startswith(b'COMPRESSED:'):
            compressed_data = data[11:]  # Remove prefix
            decompressed = zlib.decompress(compressed_data)
            return decompressed.decode('utf-8')
        return data.decode('utf-8')

    @tracer.start_as_current_span("cache_get")
    async def get(
        self,
        key: str,
        prefix: str = "",
        deserialize: bool = True,
    ) -> Optional[Union[str, Dict, List]]:
        """Get value from cache.

        Args:
            key: Cache key
            prefix: Key prefix
            deserialize: Whether to deserialize JSON

        Returns:
            Cached value or None if not found
        """
        if not self._connected:
            logger.warning("Cache not connected")
            cache_misses.add(1, {"reason": "not_connected"})
            return None

        full_key = f"{prefix}{key}"

        try:
            data = await self._client.get(full_key)
            if data is None:
                cache_misses.add(1, {"prefix": prefix})
                return None

            cache_hits.add(1, {"prefix": prefix})

            # Decompress if needed
            if isinstance(data, bytes):
                data = self._decompress(data)

            if deserialize:
                return json.loads(data)
            return data

        except Exception as e:
            logger.error(f"Cache get error for key {full_key}: {e}")
            cache_errors.add(1, {"operation": "get"})
            return None

    @tracer.start_as_current_span("cache_set")
    async def set(
        self,
        key: str,
        value: Any,
        prefix: str = "",
        ttl: Optional[timedelta] = None,
        serialize: bool = True,
    ) -> bool:
        """Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            prefix: Key prefix
            ttl: Time to live
            serialize: Whether to serialize as JSON

        Returns:
            True if successful
        """
        if not self._connected:
            logger.warning("Cache not connected")
            return False

        full_key = f"{prefix}{key}"
        ttl = ttl or self.DEFAULT_TTL

        try:
            # Serialize if needed
            data = json.dumps(value) if serialize else value

            # Compress if enabled
            if isinstance(data, str):
                data = self._compress(data)

            await self._client.set(full_key, data, ex=int(ttl.total_seconds()))
            logger.debug(f"Cached key {full_key} with TTL {ttl}")
            return True

        except Exception as e:
            logger.error(f"Cache set error for key {full_key}: {e}")
            cache_errors.add(1, {"operation": "set"})
            return False

    @tracer.start_as_current_span("cache_delete")
    async def delete(self, key: str, prefix: str = "") -> bool:
        """Delete value from cache.

        Args:
            key: Cache key
            prefix: Key prefix

        Returns:
            True if successful
        """
        if not self._connected:
            return False

        full_key = f"{prefix}{key}"

        try:
            await self._client.delete(full_key)
            logger.debug(f"Deleted cache key {full_key}")
            return True

        except Exception as e:
            logger.error(f"Cache delete error for key {full_key}: {e}")
            cache_errors.add(1, {"operation": "delete"})
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern.

        Args:
            pattern: Key pattern (supports wildcards)

        Returns:
            Number of keys deleted
        """
        if not self._connected:
            return 0

        try:
            cursor = 0
            deleted = 0

            while True:
                cursor, keys = await self._client.scan(
                    cursor=cursor,
                    match=pattern,
                    count=100,
                )

                if keys:
                    deleted += await self._client.delete(*keys)

                if cursor == 0:
                    break

            logger.info(f"Deleted {deleted} keys matching pattern {pattern}")
            return deleted

        except Exception as e:
            logger.error(f"Cache delete pattern error: {e}")
            cache_errors.add(1, {"operation": "delete_pattern"})
            return 0

    async def get_conversation(self, conversation_id: str) -> Optional[Dict]:
        """Get conversation from cache.

        Args:
            conversation_id: Conversation ID

        Returns:
            Conversation data or None
        """
        return await self.get(
            conversation_id,
            prefix=self.CONVERSATION_PREFIX,
            deserialize=True,
        )

    async def set_conversation(
        self,
        conversation_id: str,
        conversation_data: Dict,
        ttl: Optional[timedelta] = None,
    ) -> bool:
        """Set conversation in cache.

        Args:
            conversation_id: Conversation ID
            conversation_data: Conversation data
            ttl: Time to live

        Returns:
            True if successful
        """
        return await self.set(
            conversation_id,
            conversation_data,
            prefix=self.CONVERSATION_PREFIX,
            ttl=ttl or self.CONVERSATION_TTL,
            serialize=True,
        )

    async def invalidate_conversation(self, conversation_id: str) -> bool:
        """Invalidate conversation cache.

        Args:
            conversation_id: Conversation ID

        Returns:
            True if successful
        """
        # Delete conversation and related memory
        await self.delete(conversation_id, prefix=self.CONVERSATION_PREFIX)
        await self.delete(conversation_id, prefix=self.MEMORY_PREFIX)
        return True

    async def warm_cache(self, conversation_ids: List[str]) -> None:
        """Pre-warm cache with frequently accessed conversations.

        Args:
            conversation_ids: List of conversation IDs to cache
        """
        logger.info(f"Warming cache for {len(conversation_ids)} conversations")
        # Implementation would fetch from DB and cache
        # This is a placeholder for the actual implementation
        pass

    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Cache statistics
        """
        if not self._connected:
            return {"connected": False}

        try:
            info = await self._client.info()
            return {
                "connected": True,
                "used_memory": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "total_keys": await self._client.dbsize(),
                "hit_rate": info.get("keyspace_hits", 0) / max(
                    info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0), 1
                ),
            }
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {"connected": False, "error": str(e)}


def cached(
    prefix: str = "",
    ttl: Optional[timedelta] = None,
    key_func: Optional[callable] = None,
):
    """Decorator for caching function results.

    Args:
        prefix: Cache key prefix
        ttl: Time to live
        key_func: Function to generate cache key from arguments

    Returns:
        Decorated function
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Default: use first argument as key
                cache_key = str(args[0]) if args else ""

            # Try to get from cache
            if hasattr(self, 'cache') and isinstance(self.cache, RedisCache):
                cached_value = await self.cache.get(cache_key, prefix=prefix)
                if cached_value is not None:
                    return cached_value

            # Execute function
            result = await func(self, *args, **kwargs)

            # Cache result
            if hasattr(self, 'cache') and isinstance(self.cache, RedisCache):
                await self.cache.set(cache_key, result, prefix=prefix, ttl=ttl)

            return result

        return wrapper
    return decorator
