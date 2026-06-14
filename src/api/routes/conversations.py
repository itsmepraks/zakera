from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, desc
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
import secrets

from ..database import get_db
from ..models import Conversation, Message, User, ConversationShare, ConversationExport
from ..auth import get_current_active_user

router = APIRouter()

# Pydantic schemas
class ConversationCreate(BaseModel):
    title: Optional[str] = "New Conversation"
    system_prompt: Optional[str] = None
    model_name: Optional[str] = "gpt-4-turbo-preview"
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 4000
    tags: Optional[List[str]] = []

class ConversationUpdate(BaseModel):
    title: Optional[str] = None
    system_prompt: Optional[str] = None
    model_name: Optional[str] = None
    is_archived: Optional[bool] = None
    is_pinned: Optional[bool] = None
    tags: Optional[List[str]] = None
    metadata: Optional[dict] = None

class MessageCreate(BaseModel):
    role: str = Field(..., pattern="^(user|assistant|system|tool)$")
    content: str
    metadata: Optional[dict] = None

class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    created_at: datetime
    tokens_used: int
    model_name: Optional[str] = None
    finish_reason: Optional[str] = None
    latency_ms: Optional[int] = None
    metadata: Optional[dict] = {}

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
    total_tokens: int
    total_cost: float
    last_message_at: Optional[datetime] = None
    tags: List[str] = []

    class Config:
        from_attributes = True

class ConversationDetailResponse(ConversationResponse):
    system_prompt: Optional[str] = None
    temperature: float
    max_tokens: int
    messages: List[MessageResponse] = []
    metadata: Optional[dict] = {}

class ConversationStatsResponse(BaseModel):
    total_conversations: int
    active_conversations: int
    archived_conversations: int
    total_messages: int
    total_tokens: int
    total_cost: float
    conversations_this_month: int
    messages_this_month: int

class ShareCreate(BaseModel):
    is_public: bool = False
    shared_with: Optional[str] = None  # User ID
    can_edit: bool = False
    expires_in_days: Optional[int] = 7

class ShareResponse(BaseModel):
    id: str
    share_token: str
    is_public: bool
    can_edit: bool
    expires_at: Optional[datetime]
    created_at: datetime
    share_url: str

    class Config:
        from_attributes = True

# ============================================================================
# CRUD Operations
# ============================================================================

@router.post("/conversations", response_model=ConversationResponse, status_code=201)
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
        temperature=conversation.temperature,
        max_tokens=conversation.max_tokens,
        tags=conversation.tags or []
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
        message_count=0,
        total_tokens=0,
        total_cost=0.0,
        tags=db_conversation.tags or []
    )

@router.get("/conversations", response_model=List[ConversationResponse])
async def list_conversations(
    current_user: User = Depends(get_current_active_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    archived: Optional[bool] = None,
    pinned: Optional[bool] = None,
    search: Optional[str] = None,
    tags: Optional[str] = None,  # Comma-separated tags
    sort_by: str = Query("updated_at", regex="^(created_at|updated_at|title|message_count)$"),
    order: str = Query("desc", regex="^(asc|desc)$"),
    db: Session = Depends(get_db)
):
    """List all conversations for the authenticated user with advanced filtering"""
    query = db.query(Conversation).filter(
        Conversation.user_id == current_user.id,
        Conversation.is_deleted == False
    )
    
    if archived is not None:
        query = query.filter(Conversation.is_archived == archived)
    
    if pinned is not None:
        query = query.filter(Conversation.is_pinned == pinned)
    
    if search:
        query = query.filter(
            or_(
                Conversation.title.contains(search),
                Conversation.system_prompt.contains(search)
            )
        )
    
    if tags:
        tag_list = [t.strip() for t in tags.split(",")]
        # Filter conversations that have any of the specified tags
        for tag in tag_list:
            query = query.filter(Conversation.tags.contains([tag]))
    
    # Sorting
    sort_column = getattr(Conversation, sort_by)
    if order == "desc":
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(sort_column)
    
    # Always prioritize pinned conversations
    query = query.order_by(Conversation.is_pinned.desc())
    
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
            message_count=conv.message_count or 0,
            total_tokens=conv.total_tokens or 0,
            total_cost=conv.total_cost or 0.0,
            last_message_at=conv.last_message_at,
            tags=conv.tags or []
        )
        for conv in conversations
    ]

@router.get("/conversations/stats", response_model=ConversationStatsResponse)
async def get_conversation_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get conversation statistics for the authenticated user"""
    # Total conversations
    total = db.query(func.count(Conversation.id)).filter(
        Conversation.user_id == current_user.id,
        Conversation.is_deleted == False
    ).scalar()
    
    # Active conversations
    active = db.query(func.count(Conversation.id)).filter(
        Conversation.user_id == current_user.id,
        Conversation.is_archived == False,
        Conversation.is_deleted == False
    ).scalar()
    
    # Archived conversations
    archived = db.query(func.count(Conversation.id)).filter(
        Conversation.user_id == current_user.id,
        Conversation.is_archived == True,
        Conversation.is_deleted == False
    ).scalar()
    
    # Total messages
    total_messages = db.query(func.sum(Conversation.message_count)).filter(
        Conversation.user_id == current_user.id,
        Conversation.is_deleted == False
    ).scalar() or 0
    
    # Total tokens
    total_tokens = db.query(func.sum(Conversation.total_tokens)).filter(
        Conversation.user_id == current_user.id,
        Conversation.is_deleted == False
    ).scalar() or 0
    
    # Total cost
    total_cost = db.query(func.sum(Conversation.total_cost)).filter(
        Conversation.user_id == current_user.id,
        Conversation.is_deleted == False
    ).scalar() or 0.0
    
    # This month stats
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    conversations_this_month = db.query(func.count(Conversation.id)).filter(
        Conversation.user_id == current_user.id,
        Conversation.created_at >= month_start,
        Conversation.is_deleted == False
    ).scalar()
    
    messages_this_month = db.query(func.count(Message.id)).join(
        Conversation
    ).filter(
        Conversation.user_id == current_user.id,
        Message.created_at >= month_start
    ).scalar()
    
    return ConversationStatsResponse(
        total_conversations=total,
        active_conversations=active,
        archived_conversations=archived,
        total_messages=total_messages,
        total_tokens=total_tokens,
        total_cost=total_cost,
        conversations_this_month=conversations_this_month,
        messages_this_month=messages_this_month
    )

@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_active_user),
    include_messages: bool = Query(True),
    message_limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """Get a specific conversation with its messages"""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id,
        Conversation.is_deleted == False
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    messages = []
    if include_messages:
        message_query = db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at).limit(message_limit)
        
        messages = [
            MessageResponse(
                id=msg.id,
                role=msg.role,
                content=msg.content,
                created_at=msg.created_at,
                tokens_used=msg.tokens_used or 0,
                model_name=msg.model_name,
                finish_reason=msg.finish_reason,
                latency_ms=msg.latency_ms,
                metadata=msg.extra_metadata or {}
            )
            for msg in message_query.all()
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
        message_count=conversation.message_count or 0,
        total_tokens=conversation.total_tokens or 0,
        total_cost=conversation.total_cost or 0.0,
        last_message_at=conversation.last_message_at,
        system_prompt=conversation.system_prompt,
        temperature=conversation.temperature,
        max_tokens=conversation.max_tokens,
        messages=messages,
        tags=conversation.tags or [],
        metadata=conversation.extra_metadata or {}
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
        Conversation.user_id == current_user.id,
        Conversation.is_deleted == False
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Update fields if provided
    if update.title is not None:
        conversation.title = update.title
    if update.system_prompt is not None:
        conversation.system_prompt = update.system_prompt
    if update.model_name is not None:
        conversation.model_name = update.model_name
    if update.is_archived is not None:
        conversation.is_archived = update.is_archived
    if update.is_pinned is not None:
        conversation.is_pinned = update.is_pinned
    if update.tags is not None:
        conversation.tags = update.tags
    if update.metadata is not None:
        conversation.extra_metadata = update.metadata
    
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
        message_count=conversation.message_count or 0,
        total_tokens=conversation.total_tokens or 0,
        total_cost=conversation.total_cost or 0.0,
        last_message_at=conversation.last_message_at,
        tags=conversation.tags or []
    )

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    hard_delete: bool = Query(False),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a conversation (soft delete by default, hard delete if specified)"""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    if hard_delete:
        # Permanently delete
        db.delete(conversation)
    else:
        # Soft delete
        conversation.is_deleted = True
        conversation.deleted_at = func.now()
    
    db.commit()
    
    return {
        "message": "Conversation deleted successfully",
        "hard_delete": hard_delete
    }

# ============================================================================
# Message Operations
# ============================================================================

@router.post("/conversations/{conversation_id}/messages", response_model=MessageResponse, status_code=201)
async def add_message(
    conversation_id: str,
    message: MessageCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Add a message to a conversation"""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id,
        Conversation.is_deleted == False
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Create message
    db_message = Message(
        conversation_id=conversation_id,
        role=message.role,
        content=message.content,
        metadata=message.extra_metadata or {}
    )
    
    db.add(db_message)
    
    # Update conversation stats
    conversation.message_count = (conversation.message_count or 0) + 1
    conversation.last_message_at = func.now()
    conversation.updated_at = func.now()
    
    db.commit()
    db.refresh(db_message)
    
    return MessageResponse(
        id=db_message.id,
        role=db_message.role,
        content=db_message.content,
        created_at=db_message.created_at,
        tokens_used=db_message.tokens_used or 0,
        model_name=db_message.model_name,
        finish_reason=db_message.finish_reason,
        latency_ms=db_message.latency_ms,
        metadata=db_message.extra_metadata or {}
    )

@router.get("/conversations/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_messages(
    conversation_id: str,
    current_user: User = Depends(get_current_active_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    role: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get messages from a conversation with filtering"""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id,
        Conversation.is_deleted == False
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    query = db.query(Message).filter(Message.conversation_id == conversation_id)
    
    if role:
        query = query.filter(Message.role == role)
    
    messages = query.order_by(Message.created_at).offset(skip).limit(limit).all()
    
    return [
        MessageResponse(
            id=msg.id,
            role=msg.role,
            content=msg.content,
            created_at=msg.created_at,
            tokens_used=msg.tokens_used or 0,
            model_name=msg.model_name,
            finish_reason=msg.finish_reason,
            latency_ms=msg.latency_ms,
            metadata=msg.extra_metadata or {}
        )
        for msg in messages
    ]

# ============================================================================
# Sharing Operations
# ============================================================================

@router.post("/conversations/{conversation_id}/share", response_model=ShareResponse, status_code=201)
async def share_conversation(
    conversation_id: str,
    share: ShareCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Share a conversation with another user or publicly"""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id,
        Conversation.is_deleted == False
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Generate secure share token
    share_token = secrets.token_urlsafe(32)
    
    # Calculate expiration
    expires_at = None
    if share.expires_in_days:
        expires_at = datetime.utcnow() + timedelta(days=share.expires_in_days)
    
    db_share = ConversationShare(
        conversation_id=conversation_id,
        share_token=share_token,
        shared_by=current_user.id,
        shared_with=share.shared_with,
        is_public=share.is_public,
        can_edit=share.can_edit,
        expires_at=expires_at
    )
    
    db.add(db_share)
    db.commit()
    db.refresh(db_share)
    
    return ShareResponse(
        id=db_share.id,
        share_token=db_share.share_token,
        is_public=db_share.is_public,
        can_edit=db_share.can_edit,
        expires_at=db_share.expires_at,
        created_at=db_share.created_at,
        share_url=f"/shared/{db_share.share_token}"
    )

@router.get("/conversations/{conversation_id}/shares", response_model=List[ShareResponse])
async def list_shares(
    conversation_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List all shares for a conversation"""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id,
        Conversation.is_deleted == False
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    shares = db.query(ConversationShare).filter(
        ConversationShare.conversation_id == conversation_id
    ).all()
    
    return [
        ShareResponse(
            id=share.id,
            share_token=share.share_token,
            is_public=share.is_public,
            can_edit=share.can_edit,
            expires_at=share.expires_at,
            created_at=share.created_at,
            share_url=f"/shared/{share.share_token}"
        )
        for share in shares
    ]

# ============================================================================
# Bulk Operations
# ============================================================================

@router.post("/conversations/bulk/archive")
async def bulk_archive_conversations(
    conversation_ids: List[str],
    archive: bool = True,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Archive or unarchive multiple conversations"""
    conversations = db.query(Conversation).filter(
        Conversation.id.in_(conversation_ids),
        Conversation.user_id == current_user.id,
        Conversation.is_deleted == False
    ).all()
    
    for conv in conversations:
        conv.is_archived = archive
    
    db.commit()
    
    return {
        "message": f"{'Archived' if archive else 'Unarchived'} {len(conversations)} conversations",
        "count": len(conversations)
    }

@router.post("/conversations/bulk/delete")
async def bulk_delete_conversations(
    conversation_ids: List[str],
    hard_delete: bool = False,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete multiple conversations"""
    conversations = db.query(Conversation).filter(
        Conversation.id.in_(conversation_ids),
        Conversation.user_id == current_user.id
    ).all()
    
    if hard_delete:
        for conv in conversations:
            db.delete(conv)
    else:
        for conv in conversations:
            conv.is_deleted = True
            conv.deleted_at = func.now()
    
    db.commit()
    
    return {
        "message": f"Deleted {len(conversations)} conversations",
        "count": len(conversations),
        "hard_delete": hard_delete
    }
