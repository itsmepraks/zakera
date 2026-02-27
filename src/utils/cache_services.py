"""Specialized cache services for different data types."""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .cache_manager import cache_manager
from .cache_decorators import CacheKey

logger = logging.getLogger(__name__)


class ConversationCache:
    """Cache service for conversation data."""

    DEFAULT_TTL = 3600  # 1 hour

    @staticmethod
    async def get(conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get conversation from cache.

        Args:
            conversation_id: Conversation ID

        Returns:
            Conversation data or None
        """
        key = CacheKey.for_conversation(conversation_id)
        return await cache_manager.get(key)

    @staticmethod
    async def set(
        conversation_id: str,
        conversation_data: Dict[str, Any],
        ttl: Optional[int] = None,
    ) -> bool:
        """Set conversation in cache.

        Args:
            conversation_id: Conversation ID
            conversation_data: Conversation data
            ttl: Time to live in seconds

        Returns:
            True if successful
        """
        key = CacheKey.for_conversation(conversation_id)
        return await cache_manager.set(
            key,
            conversation_data,
            ttl=ttl or ConversationCache.DEFAULT_TTL,
        )

    @staticmethod
    async def delete(conversation_id: str) -> int:
        """Delete conversation from cache.

        Args:
            conversation_id: Conversation ID

        Returns:
            Number of keys deleted
        """
        key = CacheKey.for_conversation(conversation_id)
        return await cache_manager.delete(key)

    @staticmethod
    async def get_many(conversation_ids: List[str]) -> List[Optional[Dict[str, Any]]]:
        """Get multiple conversations from cache.

        Args:
            conversation_ids: List of conversation IDs

        Returns:
            List of conversation data
        """
        keys = [CacheKey.for_conversation(cid) for cid in conversation_ids]
        return await cache_manager.get_many(*keys)


class ModelResponseCache:
    """Cache service for model responses."""

    DEFAULT_TTL = 7200  # 2 hours

    @staticmethod
    def _build_prompt_hash(prompt: str, **kwargs) -> str:
        """Build hash for prompt and parameters.

        Args:
            prompt: The prompt text
            **kwargs: Additional parameters (temperature, max_tokens, etc.)

        Returns:
            Hash string
        """
        data = {"prompt": prompt, **kwargs}
        return cache_manager.hash_key(data)

    @staticmethod
    async def get(
        model: str,
        prompt: str,
        **kwargs,
    ) -> Optional[Dict[str, Any]]:
        """Get model response from cache.

        Args:
            model: Model name
            prompt: Prompt text
            **kwargs: Additional parameters

        Returns:
            Model response or None
        """
        prompt_hash = ModelResponseCache._build_prompt_hash(prompt, **kwargs)
        key = CacheKey.for_model_response(model, prompt_hash)
        return await cache_manager.get(key)

    @staticmethod
    async def set(
        model: str,
        prompt: str,
        response: Dict[str, Any],
        ttl: Optional[int] = None,
        **kwargs,
    ) -> bool:
        """Set model response in cache.

        Args:
            model: Model name
            prompt: Prompt text
            response: Model response
            ttl: Time to live in seconds
            **kwargs: Additional parameters

        Returns:
            True if successful
        """
        prompt_hash = ModelResponseCache._build_prompt_hash(prompt, **kwargs)
        key = CacheKey.for_model_response(model, prompt_hash)
        return await cache_manager.set(
            key,
            response,
            ttl=ttl or ModelResponseCache.DEFAULT_TTL,
        )


class ToolResultCache:
    """Cache service for tool execution results."""

    DEFAULT_TTL = 1800  # 30 minutes

    @staticmethod
    async def get(
        tool_name: str,
        parameters: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Get tool result from cache.

        Args:
            tool_name: Tool name
            parameters: Tool parameters

        Returns:
            Tool result or None
        """
        params_hash = cache_manager.hash_key(parameters)
        key = CacheKey.for_tool_result(tool_name, params_hash)
        return await cache_manager.get(key)

    @staticmethod
    async def set(
        tool_name: str,
        parameters: Dict[str, Any],
        result: Dict[str, Any],
        ttl: Optional[int] = None,
    ) -> bool:
        """Set tool result in cache.

        Args:
            tool_name: Tool name
            parameters: Tool parameters
            result: Tool result
            ttl: Time to live in seconds

        Returns:
            True if successful
        """
        params_hash = cache_manager.hash_key(parameters)
        key = CacheKey.for_tool_result(tool_name, params_hash)
        return await cache_manager.set(
            key,
            result,
            ttl=ttl or ToolResultCache.DEFAULT_TTL,
        )

    @staticmethod
    async def clear_for_tool(tool_name: str) -> int:
        """Clear all cached results for a tool.

        Args:
            tool_name: Tool name

        Returns:
            Number of keys deleted
        """
        pattern = cache_manager.generate_key("tool", tool_name, "*")
        return await cache_manager.clear_pattern(pattern)


class RateLimitCache:
    """Cache service for rate limiting."""

    @staticmethod
    async def get_count(
        user_id: str,
        endpoint: str,
    ) -> int:
        """Get current request count.

        Args:
            user_id: User ID
            endpoint: API endpoint

        Returns:
            Current request count
        """
        key = CacheKey.for_rate_limit(user_id, endpoint)
        count = await cache_manager.get(key, default=0)
        return int(count) if count else 0

    @staticmethod
    async def increment(
        user_id: str,
        endpoint: str,
        window_seconds: int = 60,
    ) -> int:
        """Increment request count.

        Args:
            user_id: User ID
            endpoint: API endpoint
            window_seconds: Rate limit window in seconds

        Returns:
            New count
        """
        key = CacheKey.for_rate_limit(user_id, endpoint)
        
        # Get current count
        count = await cache_manager.increment(key)
        
        # Set expiration on first request
        if count == 1:
            await cache_manager.expire(key, window_seconds)
        
        return count or 0

    @staticmethod
    async def reset(
        user_id: str,
        endpoint: str,
    ) -> int:
        """Reset rate limit counter.

        Args:
            user_id: User ID
            endpoint: API endpoint

        Returns:
            Number of keys deleted
        """
        key = CacheKey.for_rate_limit(user_id, endpoint)
        return await cache_manager.delete(key)


class UserSessionCache:
    """Cache service for user sessions."""

    DEFAULT_TTL = 7200  # 2 hours

    @staticmethod
    async def get(user_id: str) -> Optional[Dict[str, Any]]:
        """Get user session from cache.

        Args:
            user_id: User ID

        Returns:
            Session data or None
        """
        key = CacheKey.for_user_session(user_id)
        return await cache_manager.get(key)

    @staticmethod
    async def set(
        user_id: str,
        session_data: Dict[str, Any],
        ttl: Optional[int] = None,
    ) -> bool:
        """Set user session in cache.

        Args:
            user_id: User ID
            session_data: Session data
            ttl: Time to live in seconds

        Returns:
            True if successful
        """
        key = CacheKey.for_user_session(user_id)
        
        # Add timestamp
        session_data["last_updated"] = datetime.utcnow().isoformat()
        
        return await cache_manager.set(
            key,
            session_data,
            ttl=ttl or UserSessionCache.DEFAULT_TTL,
        )

    @staticmethod
    async def delete(user_id: str) -> int:
        """Delete user session from cache.

        Args:
            user_id: User ID

        Returns:
            Number of keys deleted
        """
        key = CacheKey.for_user_session(user_id)
        return await cache_manager.delete(key)

    @staticmethod
    async def refresh(user_id: str, ttl: Optional[int] = None) -> bool:
        """Refresh session expiration.

        Args:
            user_id: User ID
            ttl: Time to live in seconds

        Returns:
            True if successful
        """
        key = CacheKey.for_user_session(user_id)
        return await cache_manager.expire(
            key,
            ttl or UserSessionCache.DEFAULT_TTL,
        )
