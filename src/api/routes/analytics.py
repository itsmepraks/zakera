"""
Analytics endpoints for conversation insights and statistics.
"""
import csv
import io
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, and_, desc
from sqlalchemy.orm import Session

from ..auth import get_current_active_user
from ..database import get_db
from ..models import Conversation, Message, User
from pydantic import BaseModel, Field

router = APIRouter(prefix="/analytics", tags=["analytics"])


class ConversationStats(BaseModel):
    """Statistics for a conversation."""
    conversation_id: str
    message_count: int
    avg_message_length: float
    total_tokens: int
    first_message_at: datetime
    last_message_at: datetime
    duration_minutes: float


class OverallAnalytics(BaseModel):
    """Overall analytics across all conversations."""
    total_conversations: int
    total_messages: int
    avg_messages_per_conversation: float
    total_tokens_used: int
    active_conversations_today: int
    active_conversations_week: int
    top_conversation_topics: List[str] = Field(default_factory=list)
    conversation_stats: List[ConversationStats] = Field(default_factory=list)


class MessageSentiment(BaseModel):
    """Sentiment analysis for messages."""
    positive_count: int
    neutral_count: int
    negative_count: int
    avg_sentiment_score: float


@router.get("/overview", response_model=OverallAnalytics)
async def get_analytics_overview(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get overall analytics for user's conversations.
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Get total conversations
    total_conversations = db.query(func.count(Conversation.id)).filter(
        and_(
            Conversation.user_id == current_user.id,
            Conversation.created_at >= cutoff_date,
        )
    ).scalar() or 0
    
    # Get total messages
    total_messages = db.query(func.count(Message.id)).filter(
        Message.conversation_id.in_(
            db.query(Conversation.id).filter(Conversation.user_id == current_user.id)
        )
    ).scalar() or 0
    
    # Calculate averages
    avg_messages = total_messages / total_conversations if total_conversations > 0 else 0
    
    # Get activity for today and this week
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = today - timedelta(days=7)
    
    active_today = db.query(func.count(func.distinct(Conversation.id))).filter(
        and_(
            Conversation.user_id == current_user.id,
            Conversation.updated_at >= today,
        )
    ).scalar() or 0
    
    active_week = db.query(func.count(func.distinct(Conversation.id))).filter(
        and_(
            Conversation.user_id == current_user.id,
            Conversation.updated_at >= week_ago,
        )
    ).scalar() or 0
    
    return OverallAnalytics(
        total_conversations=total_conversations,
        total_messages=total_messages,
        avg_messages_per_conversation=round(avg_messages, 2),
        total_tokens_used=0,
        active_conversations_today=active_today,
        active_conversations_week=active_week,
        top_conversation_topics=[],
        conversation_stats=[],
    )


@router.get("/conversations/{conversation_id}/stats", response_model=ConversationStats)
async def get_conversation_stats(
    conversation_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get detailed statistics for a specific conversation.
    """
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    messages = db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).order_by(Message.created_at).all()
    
    if not messages:
        raise HTTPException(status_code=404, detail="No messages in conversation")
    
    message_count = len(messages)
    total_length = sum(len(msg.content) for msg in messages)
    avg_length = total_length / message_count
    
    first_msg = messages[0]
    last_msg = messages[-1]
    duration = (last_msg.created_at - first_msg.created_at).total_seconds() / 60
    
    return ConversationStats(
        conversation_id=conversation_id,
        message_count=message_count,
        avg_message_length=round(avg_length, 2),
        total_tokens=sum(msg.tokens_used or 0 for msg in messages),
        first_message_at=first_msg.created_at,
        last_message_at=last_msg.created_at,
        duration_minutes=round(duration, 2),
    )


@router.get("/velocity/{conversation_id}")
async def get_response_velocity(
    conversation_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Calculate the average response time for a conversation."""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    messages = db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).order_by(Message.created_at).all()
    
    if len(messages) < 2:
        return {"avg_response_time_seconds": 0, "message_pairs": 0}
    
    delays = []
    for i in range(1, len(messages)):
        if messages[i].role == "assistant" and messages[i-1].role == "user":
            delay = (messages[i].created_at - messages[i-1].created_at).total_seconds()
            delays.append(delay)
    
    if not delays:
        return {"avg_response_time_seconds": 0, "message_pairs": 0}
    
    return {
        "conversation_id": conversation_id,
        "avg_response_time_seconds": round(sum(delays) / len(delays), 2),
        "message_pairs_analyzed": len(delays),
        "min_delay_seconds": round(min(delays), 2),
        "max_delay_seconds": round(max(delays), 2),
        "analyzed_at": datetime.utcnow().isoformat()
    }


@router.get("/export/conversations")
async def export_conversations(
    format: str = Query("json", regex="^(json|csv)$"),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Export user's conversations in JSON or CSV format.
    """
    query = db.query(Conversation).filter(Conversation.user_id == current_user.id)
    
    if start_date:
        query = query.filter(Conversation.created_at >= start_date)
    if end_date:
        query = query.filter(Conversation.created_at <= end_date)
    
    conversations = query.order_by(desc(Conversation.created_at)).all()
    
    if format == "json":
        data = [
            {
                "id": conv.id,
                "title": conv.title,
                "created_at": conv.created_at.isoformat(),
                "updated_at": conv.updated_at.isoformat(),
                "message_count": conv.message_count or 0,
            }
            for conv in conversations
        ]
        return Response(
            content=json.dumps(data, indent=2),
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename=conversations_{datetime.utcnow().strftime('%Y%m%d')}.json"
            },
        )
    
    elif format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "Title", "Created At", "Updated At", "Message Count"])
        
        for conv in conversations:
            writer.writerow([
                conv.id,
                conv.title,
                conv.created_at.isoformat(),
                conv.updated_at.isoformat(),
                conv.message_count or 0,
            ])
        
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=conversations_{datetime.utcnow().strftime('%Y%m%d')}.csv"
            },
        )


@router.get("/sentiment", response_model=MessageSentiment)
async def get_message_sentiment(
    conversation_id: Optional[str] = None,
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get sentiment analysis for messages (Placeholder).
    """
    return MessageSentiment(
        positive_count=45,
        neutral_count=30,
        negative_count=5,
        avg_sentiment_score=0.7,
    )
