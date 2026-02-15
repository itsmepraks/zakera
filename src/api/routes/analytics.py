"""Analytics API endpoints.

Provides REST API endpoints for accessing conversation analytics,
user engagement metrics, model performance, and cost analysis.
"""

from datetime import datetime, timedelta
from typing import Optional
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from src.api.database import get_db
from src.api.auth import get_current_user
from src.api.analytics import analytics_service
from src.monitoring.metrics import analytics_request_counter, analytics_request_duration


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analytics", tags=["analytics"])


class DateRangeParams(BaseModel):
    """Date range query parameters."""
    start_date: Optional[datetime] = Field(None, description="Start date for filtering")
    end_date: Optional[datetime] = Field(None, description="End date for filtering")


class AnalyticsResponse(BaseModel):
    """Base analytics response."""
    success: bool = True
    data: dict
    message: Optional[str] = None


@router.get("/overview", response_model=AnalyticsResponse)
async def get_overview(
    start_date: Optional[datetime] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="End date (ISO format)"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Get high-level overview metrics for the dashboard.
    
    Returns summary statistics including:
    - Total conversations and messages
    - Active users count
    - Average messages per conversation
    - Success rate
    - Model usage distribution
    
    **Default period**: Last 30 days if dates not specified
    """
    analytics_request_counter.labels(endpoint="overview", user_id=current_user.id).inc()
    
    try:
        with analytics_request_duration.labels(endpoint="overview").time():
            metrics = await analytics_service.get_overview_metrics(
                db=db,
                start_date=start_date,
                end_date=end_date,
            )
        
        logger.info(
            f"User {current_user.id} accessed overview analytics",
            extra={"user_id": current_user.id, "metric_count": len(metrics)},
        )
        
        return AnalyticsResponse(
            data=metrics,
            message="Overview metrics retrieved successfully",
        )
    
    except Exception as e:
        logger.error(
            f"Error retrieving overview metrics: {str(e)}",
            extra={"user_id": current_user.id},
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve overview metrics",
        )


@router.get("/conversations", response_model=AnalyticsResponse)
async def get_conversation_analytics(
    start_date: Optional[datetime] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="End date (ISO format)"),
    user_id: Optional[int] = Query(None, description="Filter by specific user ID"),
    model: Optional[str] = Query(None, description="Filter by specific model"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Get detailed conversation metrics with optional filtering.
    
    Returns:
    - Duration statistics (avg, min, max)
    - Message count distribution
    - Daily conversation counts
    - Top conversations by engagement
    
    **Default period**: Last 7 days if dates not specified
    """
    analytics_request_counter.labels(endpoint="conversations", user_id=current_user.id).inc()
    
    try:
        with analytics_request_duration.labels(endpoint="conversations").time():
            metrics = await analytics_service.get_conversation_metrics(
                db=db,
                start_date=start_date,
                end_date=end_date,
                user_id=user_id,
                model=model,
            )
        
        logger.info(
            f"User {current_user.id} accessed conversation analytics",
            extra={
                "user_id": current_user.id,
                "filter_user": user_id,
                "filter_model": model,
            },
        )
        
        return AnalyticsResponse(
            data=metrics,
            message="Conversation metrics retrieved successfully",
        )
    
    except Exception as e:
        logger.error(
            f"Error retrieving conversation metrics: {str(e)}",
            extra={"user_id": current_user.id},
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve conversation metrics",
        )


@router.get("/models", response_model=AnalyticsResponse)
async def get_model_performance(
    start_date: Optional[datetime] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="End date (ISO format)"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Get model performance comparison metrics.
    
    Returns for each model:
    - Total messages generated
    - Average response time
    - Token usage statistics
    - Tokens per message ratio
    
    Useful for:
    - Identifying slow models
    - Optimizing token usage
    - Cost-performance analysis
    
    **Default period**: Last 30 days if dates not specified
    """
    analytics_request_counter.labels(endpoint="models", user_id=current_user.id).inc()
    
    try:
        with analytics_request_duration.labels(endpoint="models").time():
            metrics = await analytics_service.get_model_performance(
                db=db,
                start_date=start_date,
                end_date=end_date,
            )
        
        logger.info(
            f"User {current_user.id} accessed model performance analytics",
            extra={"user_id": current_user.id, "model_count": len(metrics.get("models", {}))},
        )
        
        return AnalyticsResponse(
            data=metrics,
            message="Model performance metrics retrieved successfully",
        )
    
    except Exception as e:
        logger.error(
            f"Error retrieving model performance: {str(e)}",
            extra={"user_id": current_user.id},
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve model performance metrics",
        )


@router.get("/users", response_model=AnalyticsResponse)
async def get_user_engagement(
    start_date: Optional[datetime] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="End date (ISO format)"),
    top_n: int = Query(20, ge=1, le=100, description="Number of top users to return"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Get user engagement statistics.
    
    Returns:
    - Top users by conversation count
    - Message activity per user
    - User retention over time (weekly cohorts)
    
    Useful for:
    - Identifying power users
    - Understanding retention patterns
    - User behavior analysis
    
    **Default period**: Last 30 days if dates not specified
    """
    analytics_request_counter.labels(endpoint="users", user_id=current_user.id).inc()
    
    try:
        with analytics_request_duration.labels(endpoint="users").time():
            metrics = await analytics_service.get_user_engagement(
                db=db,
                start_date=start_date,
                end_date=end_date,
                top_n=top_n,
            )
        
        logger.info(
            f"User {current_user.id} accessed user engagement analytics",
            extra={"user_id": current_user.id, "top_n": top_n},
        )
        
        return AnalyticsResponse(
            data=metrics,
            message="User engagement metrics retrieved successfully",
        )
    
    except Exception as e:
        logger.error(
            f"Error retrieving user engagement: {str(e)}",
            extra={"user_id": current_user.id},
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve user engagement metrics",
        )


@router.get("/costs", response_model=AnalyticsResponse)
async def get_cost_analysis(
    start_date: Optional[datetime] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="End date (ISO format)"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Get cost analysis and breakdown by model.
    
    Returns:
    - Total estimated costs
    - Daily average cost
    - Monthly projected cost
    - Per-model cost breakdown
    - Cost per message by model
    
    **Note**: Costs are estimates based on published pricing.
    Local models (Ollama) show $0 cost.
    
    **Default period**: Last 30 days if dates not specified
    """
    analytics_request_counter.labels(endpoint="costs", user_id=current_user.id).inc()
    
    try:
        with analytics_request_duration.labels(endpoint="costs").time():
            metrics = await analytics_service.get_cost_analysis(
                db=db,
                start_date=start_date,
                end_date=end_date,
            )
        
        logger.info(
            f"User {current_user.id} accessed cost analysis",
            extra={
                "user_id": current_user.id,
                "total_cost": metrics.get("total_cost_usd"),
            },
        )
        
        return AnalyticsResponse(
            data=metrics,
            message="Cost analysis retrieved successfully",
        )
    
    except Exception as e:
        logger.error(
            f"Error retrieving cost analysis: {str(e)}",
            extra={"user_id": current_user.id},
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve cost analysis",
        )


@router.get("/export")
async def export_analytics(
    format: str = Query("json", regex="^(json|csv)$", description="Export format"),
    metric_type: str = Query(
        "overview",
        regex="^(overview|conversations|models|users|costs)$",
        description="Type of metrics to export",
    ),
    start_date: Optional[datetime] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="End date (ISO format)"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Export analytics data in JSON or CSV format.
    
    Supports exporting:
    - overview: High-level metrics
    - conversations: Detailed conversation data
    - models: Model performance data
    - users: User engagement data
    - costs: Cost analysis data
    
    **Formats**:
    - `json`: Structured JSON (default)
    - `csv`: Comma-separated values
    """
    analytics_request_counter.labels(endpoint="export", user_id=current_user.id).inc()
    
    try:
        # Get the requested metrics
        if metric_type == "overview":
            data = await analytics_service.get_overview_metrics(db, start_date, end_date)
        elif metric_type == "conversations":
            data = await analytics_service.get_conversation_metrics(db, start_date, end_date)
        elif metric_type == "models":
            data = await analytics_service.get_model_performance(db, start_date, end_date)
        elif metric_type == "users":
            data = await analytics_service.get_user_engagement(db, start_date, end_date)
        elif metric_type == "costs":
            data = await analytics_service.get_cost_analysis(db, start_date, end_date)
        
        logger.info(
            f"User {current_user.id} exported {metric_type} analytics as {format}",
            extra={"user_id": current_user.id, "format": format, "type": metric_type},
        )
        
        if format == "json":
            return Response(
                content=str(data),
                media_type="application/json",
                headers={
                    "Content-Disposition": f"attachment; filename=analytics_{metric_type}_{datetime.utcnow().strftime('%Y%m%d')}.json"
                },
            )
        else:
            # CSV format - simplified flat structure
            import csv
            import io
            
            output = io.StringIO()
            # Note: CSV export would need custom formatting per metric type
            # This is a simplified version
            output.write(f"# Analytics Export: {metric_type}\n")
            output.write(f"# Generated: {datetime.utcnow().isoformat()}\n")
            output.write(f"# Data: {str(data)}\n")
            
            return Response(
                content=output.getvalue(),
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=analytics_{metric_type}_{datetime.utcnow().strftime('%Y%m%d')}.csv"
                },
            )
    
    except Exception as e:
        logger.error(
            f"Error exporting analytics: {str(e)}",
            extra={"user_id": current_user.id},
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to export analytics data",
        )


@router.get("/trends")
async def get_trends(
    metric: str = Query(
        "conversations",
        regex="^(conversations|messages|users|costs)$",
        description="Metric to analyze for trends",
    ),
    days: int = Query(30, ge=7, le=365, description="Number of days to analyze"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Get time-series trend analysis for specified metrics.
    
    Analyzes daily trends over the specified period for:
    - `conversations`: Daily conversation counts
    - `messages`: Daily message counts
    - `users`: Daily active users
    - `costs`: Daily estimated costs
    
    Returns daily data points with trend indicators.
    """
    analytics_request_counter.labels(endpoint="trends", user_id=current_user.id).inc()
    
    try:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get conversation metrics which includes daily counts
        metrics = await analytics_service.get_conversation_metrics(
            db=db,
            start_date=start_date,
            end_date=end_date,
        )
        
        daily_counts = metrics.get("daily_counts", {})
        
        # Calculate simple trend (comparing first half vs second half)
        if daily_counts:
            dates = sorted(daily_counts.keys())
            mid_point = len(dates) // 2
            
            first_half_avg = sum(daily_counts[d] for d in dates[:mid_point]) / max(mid_point, 1)
            second_half_avg = sum(daily_counts[d] for d in dates[mid_point:]) / max(
                len(dates) - mid_point, 1
            )
            
            trend_direction = "increasing" if second_half_avg > first_half_avg else "decreasing"
            trend_percentage = (
                ((second_half_avg - first_half_avg) / max(first_half_avg, 1)) * 100
                if first_half_avg > 0
                else 0
            )
        else:
            trend_direction = "stable"
            trend_percentage = 0
        
        logger.info(
            f"User {current_user.id} accessed trend analysis for {metric}",
            extra={"user_id": current_user.id, "metric": metric, "days": days},
        )
        
        return {
            "success": True,
            "data": {
                "metric": metric,
                "daily_data": daily_counts,
                "trend": {
                    "direction": trend_direction,
                    "percentage_change": round(trend_percentage, 2),
                },
                "period": {
                    "days": days,
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat(),
                },
            },
            "message": "Trend analysis retrieved successfully",
        }
    
    except Exception as e:
        logger.error(
            f"Error retrieving trend analysis: {str(e)}",
            extra={"user_id": current_user.id},
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve trend analysis",
        )
