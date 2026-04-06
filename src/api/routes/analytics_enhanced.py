from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any
from datetime import datetime
from ..database import get_db
from ..models import Conversation, Message, User
from ..auth import get_current_active_user

router = APIRouter(prefix="/analytics/enhanced", tags=["analytics"])

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
        "avg_response_time_seconds": sum(delays) / len(delays),
        "message_pairs": len(delays),
        "min_delay": min(delays),
        "max_delay": max(delays)
    }
