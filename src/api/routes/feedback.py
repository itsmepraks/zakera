from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

from ..database import get_db
from ..models import Message, MessageFeedback, User
from ..auth import get_current_active_user

router = APIRouter()

class FeedbackRequest(BaseModel):
    message_id: str
    is_positive: bool
    comment: Optional[str] = Field(default=None, max_length=1000)

class FeedbackResponse(BaseModel):
    id: str
    message_id: str
    is_positive: bool
    comment: Optional[str]
    created_at: datetime

@router.post("/", response_model=FeedbackResponse)
async def create_feedback(
    request: FeedbackRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Submit feedback for a specific AI message.
    """
    # Check if message exists
    message = db.query(Message).filter(Message.id == request.message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    # Create new feedback record
    feedback = MessageFeedback(
        message_id=request.message_id,
        user_id=current_user.id,
        is_positive=request.is_positive,
        comment=request.comment
    )
    
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    
    return feedback
