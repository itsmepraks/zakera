"""Conversation Analytics Service.

Provides comprehensive analytics and insights for conversations,
including user engagement metrics, model performance, and cost analysis.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict
import logging

from sqlalchemy import func, and_, or_, select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from cachetools import TTLCache

from src.api.models import Conversation, Message, User
from src.monitoring.metrics import track_analytics_query


logger = logging.getLogger(__name__)


class ConversationAnalytics:
    """Service for analyzing conversation data and generating insights."""

    def __init__(self, cache_ttl: int = 300):
        """Initialize analytics service with caching.
        
        Args:
            cache_ttl: Cache time-to-live in seconds (default: 5 minutes)
        """
        self.cache = TTLCache(maxsize=100, ttl=cache_ttl)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def get_overview_metrics(
        self,
        db: AsyncSession,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Get high-level overview metrics for the dashboard.
        
        Args:
            db: Database session
            start_date: Start date for filtering (default: 30 days ago)
            end_date: End date for filtering (default: now)
            
        Returns:
            Dictionary containing overview metrics
        """
        cache_key = f"overview_{start_date}_{end_date}"
        if cache_key in self.cache:
            self.logger.debug("Returning cached overview metrics")
            return self.cache[cache_key]

        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()

        self.logger.info(f"Calculating overview metrics from {start_date} to {end_date}")

        try:
            with track_analytics_query("overview_metrics"):
                # Total conversations
                total_conv_query = select(func.count(Conversation.id)).where(
                    and_(
                        Conversation.created_at >= start_date,
                        Conversation.created_at <= end_date,
                    )
                )
                total_conversations = await db.scalar(total_conv_query)

                # Total messages
                total_msg_query = select(func.count(Message.id)).where(
                    and_(
                        Message.created_at >= start_date,
                        Message.created_at <= end_date,
                    )
                )
                total_messages = await db.scalar(total_msg_query)

                # Active users
                active_users_query = select(func.count(func.distinct(Conversation.user_id))).where(
                    and_(
                        Conversation.created_at >= start_date,
                        Conversation.created_at <= end_date,
                    )
                )
                active_users = await db.scalar(active_users_query)

                # Average messages per conversation
                avg_messages = (
                    float(total_messages) / total_conversations if total_conversations > 0 else 0
                )

                # Model usage distribution
                model_usage_query = (
                    select(
                        Message.model,
                        func.count(Message.id).label("count"),
                    )
                    .where(
                        and_(
                            Message.created_at >= start_date,
                            Message.created_at <= end_date,
                            Message.role == "assistant",
                        )
                    )
                    .group_by(Message.model)
                )
                model_usage_result = await db.execute(model_usage_query)
                model_usage = {row.model: row.count for row in model_usage_result}

                # Success rate (conversations with at least 2 turns)
                success_query = select(func.count(Conversation.id)).where(
                    and_(
                        Conversation.created_at >= start_date,
                        Conversation.created_at <= end_date,
                        Conversation.message_count >= 2,
                    )
                )
                successful_conversations = await db.scalar(success_query)
                success_rate = (
                    (successful_conversations / total_conversations * 100)
                    if total_conversations > 0
                    else 0
                )

                metrics = {
                    "total_conversations": total_conversations or 0,
                    "total_messages": total_messages or 0,
                    "active_users": active_users or 0,
                    "avg_messages_per_conversation": round(avg_messages, 2),
                    "success_rate": round(success_rate, 2),
                    "model_usage": model_usage,
                    "period": {
                        "start": start_date.isoformat(),
                        "end": end_date.isoformat(),
                    },
                }

                self.cache[cache_key] = metrics
                return metrics

        except Exception as e:
            self.logger.error(f"Error calculating overview metrics: {str(e)}")
            raise

    async def get_conversation_metrics(
        self,
        db: AsyncSession,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        user_id: Optional[int] = None,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get detailed conversation metrics with filtering.
        
        Args:
            db: Database session
            start_date: Start date for filtering
            end_date: End date for filtering
            user_id: Filter by specific user
            model: Filter by specific model
            
        Returns:
            Dictionary containing detailed conversation metrics
        """
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=7)
        if not end_date:
            end_date = datetime.utcnow()

        self.logger.info(
            f"Calculating conversation metrics (user={user_id}, model={model})"
        )

        try:
            with track_analytics_query("conversation_metrics"):
                # Build base query conditions
                conditions = [
                    Conversation.created_at >= start_date,
                    Conversation.created_at <= end_date,
                ]
                if user_id:
                    conditions.append(Conversation.user_id == user_id)

                # Conversation duration statistics
                duration_query = select(
                    func.avg(Conversation.duration_seconds).label("avg_duration"),
                    func.max(Conversation.duration_seconds).label("max_duration"),
                    func.min(Conversation.duration_seconds).label("min_duration"),
                ).where(and_(*conditions))
                duration_result = await db.execute(duration_query)
                duration_stats = duration_result.first()

                # Message count distribution
                message_dist_query = (
                    select(
                        Conversation.message_count,
                        func.count(Conversation.id).label("count"),
                    )
                    .where(and_(*conditions))
                    .group_by(Conversation.message_count)
                    .order_by(Conversation.message_count)
                )
                message_dist_result = await db.execute(message_dist_query)
                message_distribution = {
                    row.message_count: row.count for row in message_dist_result
                }

                # Daily conversation counts
                daily_query = (
                    select(
                        func.date(Conversation.created_at).label("date"),
                        func.count(Conversation.id).label("count"),
                    )
                    .where(and_(*conditions))
                    .group_by(func.date(Conversation.created_at))
                    .order_by(func.date(Conversation.created_at))
                )
                daily_result = await db.execute(daily_query)
                daily_counts = {
                    str(row.date): row.count for row in daily_result
                }

                # Top conversations by message count
                top_conv_query = (
                    select(Conversation)
                    .where(and_(*conditions))
                    .order_by(desc(Conversation.message_count))
                    .limit(10)
                )
                top_conv_result = await db.execute(top_conv_query)
                top_conversations = [
                    {
                        "id": conv.id,
                        "title": conv.title,
                        "message_count": conv.message_count,
                        "duration_seconds": conv.duration_seconds,
                        "created_at": conv.created_at.isoformat(),
                    }
                    for conv in top_conv_result.scalars()
                ]

                return {
                    "duration_stats": {
                        "avg_seconds": round(duration_stats.avg_duration or 0, 2),
                        "max_seconds": duration_stats.max_duration or 0,
                        "min_seconds": duration_stats.min_duration or 0,
                    },
                    "message_distribution": message_distribution,
                    "daily_counts": daily_counts,
                    "top_conversations": top_conversations,
                    "filters": {
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat(),
                        "user_id": user_id,
                        "model": model,
                    },
                }

        except Exception as e:
            self.logger.error(f"Error calculating conversation metrics: {str(e)}")
            raise

    async def get_model_performance(
        self,
        db: AsyncSession,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Get model performance comparison metrics.
        
        Args:
            db: Database session
            start_date: Start date for filtering
            end_date: End date for filtering
            
        Returns:
            Dictionary containing model performance metrics
        """
        cache_key = f"model_perf_{start_date}_{end_date}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()

        self.logger.info("Calculating model performance metrics")

        try:
            with track_analytics_query("model_performance"):
                # Query for model statistics
                model_stats_query = (
                    select(
                        Message.model,
                        func.count(Message.id).label("total_messages"),
                        func.avg(Message.response_time_ms).label("avg_response_time"),
                        func.sum(Message.prompt_tokens).label("total_prompt_tokens"),
                        func.sum(Message.completion_tokens).label("total_completion_tokens"),
                        func.avg(Message.prompt_tokens).label("avg_prompt_tokens"),
                        func.avg(Message.completion_tokens).label("avg_completion_tokens"),
                    )
                    .where(
                        and_(
                            Message.created_at >= start_date,
                            Message.created_at <= end_date,
                            Message.role == "assistant",
                        )
                    )
                    .group_by(Message.model)
                )
                model_stats_result = await db.execute(model_stats_query)

                model_performance = {}
                for row in model_stats_result:
                    total_tokens = (
                        (row.total_prompt_tokens or 0) + (row.total_completion_tokens or 0)
                    )
                    model_performance[row.model] = {
                        "total_messages": row.total_messages,
                        "avg_response_time_ms": round(row.avg_response_time or 0, 2),
                        "total_tokens": total_tokens,
                        "avg_prompt_tokens": round(row.avg_prompt_tokens or 0, 2),
                        "avg_completion_tokens": round(row.avg_completion_tokens or 0, 2),
                        "tokens_per_message": (
                            round(total_tokens / row.total_messages, 2)
                            if row.total_messages > 0
                            else 0
                        ),
                    }

                result = {
                    "models": model_performance,
                    "period": {
                        "start": start_date.isoformat(),
                        "end": end_date.isoformat(),
                    },
                }

                self.cache[cache_key] = result
                return result

        except Exception as e:
            self.logger.error(f"Error calculating model performance: {str(e)}")
            raise

    async def get_user_engagement(
        self,
        db: AsyncSession,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        top_n: int = 20,
    ) -> Dict[str, Any]:
        """Get user engagement statistics.
        
        Args:
            db: Database session
            start_date: Start date for filtering
            end_date: End date for filtering
            top_n: Number of top users to return
            
        Returns:
            Dictionary containing user engagement metrics
        """
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()

        self.logger.info("Calculating user engagement metrics")

        try:
            with track_analytics_query("user_engagement"):
                # Top users by conversation count
                top_users_query = (
                    select(
                        Conversation.user_id,
                        func.count(Conversation.id).label("conversation_count"),
                        func.sum(Conversation.message_count).label("total_messages"),
                        func.avg(Conversation.message_count).label("avg_messages_per_conv"),
                        func.max(Conversation.created_at).label("last_activity"),
                    )
                    .where(
                        and_(
                            Conversation.created_at >= start_date,
                            Conversation.created_at <= end_date,
                        )
                    )
                    .group_by(Conversation.user_id)
                    .order_by(desc("conversation_count"))
                    .limit(top_n)
                )
                top_users_result = await db.execute(top_users_query)

                top_users = [
                    {
                        "user_id": row.user_id,
                        "conversation_count": row.conversation_count,
                        "total_messages": row.total_messages or 0,
                        "avg_messages_per_conversation": round(
                            row.avg_messages_per_conv or 0, 2
                        ),
                        "last_activity": row.last_activity.isoformat(),
                    }
                    for row in top_users_result
                ]

                # User retention (users active in multiple weeks)
                retention_weeks = 4
                retention_data = await self._calculate_retention(
                    db, start_date, end_date, retention_weeks
                )

                return {
                    "top_users": top_users,
                    "retention": retention_data,
                    "period": {
                        "start": start_date.isoformat(),
                        "end": end_date.isoformat(),
                    },
                }

        except Exception as e:
            self.logger.error(f"Error calculating user engagement: {str(e)}")
            raise

    async def _calculate_retention(
        self,
        db: AsyncSession,
        start_date: datetime,
        end_date: datetime,
        weeks: int,
    ) -> Dict[str, Any]:
        """Calculate user retention over multiple weeks."""
        weekly_data = []
        week_duration = timedelta(days=7)

        for i in range(weeks):
            week_start = start_date + (i * week_duration)
            week_end = min(week_start + week_duration, end_date)

            active_query = select(func.count(func.distinct(Conversation.user_id))).where(
                and_(
                    Conversation.created_at >= week_start,
                    Conversation.created_at < week_end,
                )
            )
            active_users = await db.scalar(active_query)

            weekly_data.append(
                {
                    "week": i + 1,
                    "start_date": week_start.isoformat(),
                    "end_date": week_end.isoformat(),
                    "active_users": active_users or 0,
                }
            )

        # Calculate retention rate
        if weekly_data and weekly_data[0]["active_users"] > 0:
            baseline = weekly_data[0]["active_users"]
            for week in weekly_data[1:]:
                week["retention_rate"] = round(
                    (week["active_users"] / baseline) * 100, 2
                )
            weekly_data[0]["retention_rate"] = 100.0

        return {"weekly_data": weekly_data, "total_weeks": weeks}

    async def get_cost_analysis(
        self,
        db: AsyncSession,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Get cost analysis and breakdown by model.
        
        Args:
            db: Database session
            start_date: Start date for filtering
            end_date: End date for filtering
            
        Returns:
            Dictionary containing cost analysis
        """
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()

        self.logger.info("Calculating cost analysis")

        # Model pricing (per 1K tokens) - approximate values
        model_pricing = {
            "gpt-4-turbo": {"prompt": 0.01, "completion": 0.03},
            "gpt-4": {"prompt": 0.03, "completion": 0.06},
            "gpt-3.5-turbo": {"prompt": 0.0005, "completion": 0.0015},
            "claude-3-opus": {"prompt": 0.015, "completion": 0.075},
            "claude-3-sonnet": {"prompt": 0.003, "completion": 0.015},
            "claude-3-haiku": {"prompt": 0.00025, "completion": 0.00125},
            "gemini-1.5-pro": {"prompt": 0.0035, "completion": 0.0105},
            "gemini-1.5-flash": {"prompt": 0.00035, "completion": 0.00105},
        }

        try:
            with track_analytics_query("cost_analysis"):
                # Get token usage by model
                token_query = (
                    select(
                        Message.model,
                        func.sum(Message.prompt_tokens).label("prompt_tokens"),
                        func.sum(Message.completion_tokens).label("completion_tokens"),
                        func.count(Message.id).label("message_count"),
                    )
                    .where(
                        and_(
                            Message.created_at >= start_date,
                            Message.created_at <= end_date,
                            Message.role == "assistant",
                        )
                    )
                    .group_by(Message.model)
                )
                token_result = await db.execute(token_query)

                cost_breakdown = []
                total_cost = 0.0

                for row in token_result:
                    model = row.model
                    prompt_tokens = row.prompt_tokens or 0
                    completion_tokens = row.completion_tokens or 0

                    # Calculate cost if pricing is available
                    if model in model_pricing:
                        pricing = model_pricing[model]
                        prompt_cost = (prompt_tokens / 1000) * pricing["prompt"]
                        completion_cost = (completion_tokens / 1000) * pricing["completion"]
                        model_cost = prompt_cost + completion_cost
                    else:
                        # Unknown model - estimate or mark as free (Ollama)
                        model_cost = 0.0

                    total_cost += model_cost

                    cost_breakdown.append(
                        {
                            "model": model,
                            "message_count": row.message_count,
                            "prompt_tokens": prompt_tokens,
                            "completion_tokens": completion_tokens,
                            "total_tokens": prompt_tokens + completion_tokens,
                            "estimated_cost_usd": round(model_cost, 4),
                            "cost_per_message": (
                                round(model_cost / row.message_count, 6)
                                if row.message_count > 0
                                else 0
                            ),
                        }
                    )

                # Sort by cost descending
                cost_breakdown.sort(key=lambda x: x["estimated_cost_usd"], reverse=True)

                # Calculate daily costs for trending
                days_in_period = (end_date - start_date).days or 1
                daily_avg_cost = total_cost / days_in_period

                return {
                    "total_cost_usd": round(total_cost, 2),
                    "daily_avg_cost_usd": round(daily_avg_cost, 2),
                    "monthly_projected_cost_usd": round(daily_avg_cost * 30, 2),
                    "cost_breakdown": cost_breakdown,
                    "period": {
                        "start": start_date.isoformat(),
                        "end": end_date.isoformat(),
                        "days": days_in_period,
                    },
                }

        except Exception as e:
            self.logger.error(f"Error calculating cost analysis: {str(e)}")
            raise


# Global analytics service instance
analytics_service = ConversationAnalytics()
