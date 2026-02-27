"""Cache decorators for function and FastAPI route caching."""

import asyncio
import functools
import inspect
import logging
from typing import Any, Callable, Optional, Union

from fastapi import Request, Response
from fastapi.responses import JSONResponse

from .cache_manager import cache_manager

logger = logging.getLogger(__name__)


def cached(
    ttl: int = 300,
    key_prefix: str = "func",
    key_builder: Optional[Callable] = None,
    skip_if: Optional[Callable] = None,
):
    """Decorator to cache function results.

    Args:
        ttl: Time to live in seconds
        key_prefix: Prefix for cache key
        key_builder: Custom function to build cache key
        skip_if: Function to determine if caching should be skipped

    Example:
        @cached(ttl=600, key_prefix="user")
        async def get_user(user_id: str):
            return await fetch_user(user_id)
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Check if caching should be skipped
            if skip_if and skip_if(*args, **kwargs):
                return await func(*args, **kwargs)

            # Build cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                # Default key builder
                func_name = func.__name__
                key_parts = [key_prefix, func_name]

                # Add positional args
                key_parts.extend(str(arg) for arg in args)

                # Add keyword args
                for k, v in sorted(kwargs.items()):
                    key_parts.append(f"{k}={v}")

                cache_key = cache_manager.generate_key(*key_parts)

            # Try to get from cache
            cached_value = await cache_manager.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit for key: {cache_key}")
                return cached_value

            # Execute function
            logger.debug(f"Cache miss for key: {cache_key}")
            result = await func(*args, **kwargs)

            # Store in cache
            await cache_manager.set(cache_key, result, ttl=ttl)

            return result

        # Add cache invalidation method
        async def invalidate(*args, **kwargs):
            """Invalidate cache for this function call."""
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                func_name = func.__name__
                key_parts = [key_prefix, func_name]
                key_parts.extend(str(arg) for arg in args)
                for k, v in sorted(kwargs.items()):
                    key_parts.append(f"{k}={v}")
                cache_key = cache_manager.generate_key(*key_parts)

            await cache_manager.delete(cache_key)

        wrapper.invalidate = invalidate
        wrapper.is_cached = True

        return wrapper

    return decorator


def cache_route(
    ttl: int = 300,
    key_prefix: str = "route",
    vary_on: Optional[list] = None,
):
    """Decorator to cache FastAPI route responses.

    Args:
        ttl: Time to live in seconds
        key_prefix: Prefix for cache key
        vary_on: List of request attributes to vary cache on
                 (e.g., ["user_id", "query_params"])

    Example:
        @router.get("/users/{user_id}")
        @cache_route(ttl=600, vary_on=["user_id"])
        async def get_user(user_id: str):
            return {"id": user_id}
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request if available
            request: Optional[Request] = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            if not request:
                # No request found, execute without caching
                return await func(*args, **kwargs)

            # Build cache key
            key_parts = [key_prefix, request.url.path]

            # Add vary_on attributes
            if vary_on:
                for attr in vary_on:
                    if attr in kwargs:
                        key_parts.append(f"{attr}={kwargs[attr]}")
                    elif attr == "query_params":
                        query = dict(request.query_params)
                        if query:
                            key_parts.append(cache_manager.hash_key(query))
                    elif attr == "user_id":
                        # Get user_id from request state or kwargs
                        user_id = getattr(request.state, "user_id", None) or kwargs.get("user_id")
                        if user_id:
                            key_parts.append(f"user={user_id}")

            cache_key = cache_manager.generate_key(*key_parts)

            # Try to get from cache
            cached_response = await cache_manager.get(cache_key)
            if cached_response is not None:
                logger.debug(f"Route cache hit: {request.url.path}")
                return JSONResponse(
                    content=cached_response,
                    headers={"X-Cache": "HIT"},
                )

            # Execute route handler
            logger.debug(f"Route cache miss: {request.url.path}")
            response = await func(*args, **kwargs)

            # Cache response if it's successful
            if isinstance(response, dict):
                await cache_manager.set(cache_key, response, ttl=ttl)
                return JSONResponse(
                    content=response,
                    headers={"X-Cache": "MISS"},
                )
            elif isinstance(response, Response):
                # For Response objects, try to cache the body
                try:
                    if hasattr(response, "body"):
                        import json
                        body = json.loads(response.body)
                        await cache_manager.set(cache_key, body, ttl=ttl)
                except Exception as e:
                    logger.warning(f"Could not cache response: {e}")

            return response

        return wrapper

    return decorator


class CacheKey:
    """Helper class for building cache keys."""

    @staticmethod
    def for_conversation(conversation_id: str) -> str:
        """Generate cache key for conversation."""
        return cache_manager.generate_key("conversation", conversation_id)

    @staticmethod
    def for_user_session(user_id: str) -> str:
        """Generate cache key for user session."""
        return cache_manager.generate_key("session", user_id)

    @staticmethod
    def for_model_response(model: str, prompt_hash: str) -> str:
        """Generate cache key for model response."""
        return cache_manager.generate_key("model", model, prompt_hash)

    @staticmethod
    def for_tool_result(tool_name: str, params_hash: str) -> str:
        """Generate cache key for tool result."""
        return cache_manager.generate_key("tool", tool_name, params_hash)

    @staticmethod
    def for_rate_limit(user_id: str, endpoint: str) -> str:
        """Generate cache key for rate limit."""
        return cache_manager.generate_key("ratelimit", user_id, endpoint)

    @staticmethod
    def for_user_preferences(user_id: str) -> str:
        """Generate cache key for user preferences."""
        return cache_manager.generate_key("preferences", user_id)
