from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from ..database import get_db
from ..models import Conversation, Message, User
from ..auth import get_current_active_user

router = APIRouter()

# Pydantic schemas
class ConversationCreate(BaseModel):
    title: Optional[str] = "New Conversation"
    system_prompt: Optional[str] = None
    model_name: Optional[str] = "gpt-4-turbo-preview"
    temperature: Optional[int] = 7

class ConversationUpdate(BaseModel):
    title: Optional[str] = None
    system_prompt: Optional[str] = None
    is_archived: Optional[bool] = None
    is_pinned: Optional[bool] = None

class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    created_at: datetime
    tokens_used: int

    class Config:
        from_attributes = True

class ConversationResponse(BaseModel):
    id: str
    user_id: str
    title: str
    model_name: str
    is_archived: bool
    is_pinned: bool
    created_at: datetime
    updated_at: datetime
    message_count: int

    class Config:
        from_attributes = True

class ConversationDetailResponse(ConversationResponse):
    system_prompt: Optional[str] = None
    messages: List[MessageResponse] = []

@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(
    conversation: ConversationCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new conversation for the authenticated user"""
    db_conversation = Conversation(
        user_id=current_user.id,
        title=conversation.title,
        system_prompt=conversation.system_prompt,
        model_name=conversation.model_name,
        temperature=conversation.temperature
    )
    db.add(db_conversation)
    db.commit()
    db.refresh(db_conversation)
    
    return ConversationResponse(
        id=db_conversation.id,
        user_id=db_conversation.user_id,
        title=db_conversation.title,
        model_name=db_conversation.model_name,
        is_archived=db_conversation.is_archived,
        is_pinned=db_conversation.is_pinned,
        created_at=db_conversation.created_at,
        updated_at=db_conversation.updated_at,
        message_count=0
    )

@router.get("/conversations", response_model=List[ConversationResponse])
async def list_conversations(
    current_user: User = Depends(get_current_active_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    archived: Optional[bool] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all conversations for the authenticated user"""
    query = db.query(Conversation).filter(Conversation.user_id == current_user.id)
    
    if archived is not None:
        query = query.filter(Conversation.is_archived == archived)
    
    if search:
        query = query.filter(Conversation.title.contains(search))
    
    query = query.order_by(Conversation.is_pinned.desc(), Conversation.updated_at.desc())
    conversations = query.offset(skip).limit(limit).all()
    
    return [
        ConversationResponse(
            id=conv.id,
            user_id=conv.user_id,
            title=conv.title,
            model_name=conv.model_name,
            is_archived=conv.is_archived,
            is_pinned=conv.is_pinned,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            message_count=len(conv.messages)
        )
        for conv in conversations
    ]

@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get a specific conversation with its messages"""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    messages = [
        MessageResponse(
            id=msg.id,
            role=msg.role,
            content=msg.content,
            created_at=msg.created_at,
            tokens_used=msg.tokens_used
        )
        for msg in conversation.messages
    ]
    
    return ConversationDetailResponse(
        id=conversation.id,
        user_id=conversation.user_id,
        title=conversation.title,
        model_name=conversation.model_name,
        is_archived=conversation.is_archived,
        is_pinned=conversation.is_pinned,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        message_count=len(messages),
        system_prompt=conversation.system_prompt,
        messages=messages
    )

@router.patch("/conversations/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: str,
    update: ConversationUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update a conversation"""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Update fields if provided
    if update.title is not None:
        conversation.title = update.title
    if update.system_prompt is not None:
        conversation.system_prompt = update.system_prompt
    if update.is_archived is not None:
        conversation.is_archived = update.is_archived
    if update.is_pinned is not None:
        conversation.is_pinned = update.is_pinned
    
    db.commit()
    db.refresh(conversation)
    
    return ConversationResponse(
        id=conversation.id,
        user_id=conversation.user_id,
        title=conversation.title,
        model_name=conversation.model_name,
        is_archived=conversation.is_archived,
        is_pinned=conversation.is_pinned,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        message_count=len(conversation.messages)
    )

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a conversation"""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    db.delete(conversation)
    db.commit()
    
    return {"message": "Conversation deleted successfully"}
