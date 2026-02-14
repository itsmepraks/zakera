"""
Enhanced search endpoints for finding conversations and messages.
"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import or_, and_, func, desc
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from ..auth import get_current_active_user
from ..database import get_db
from ..models import Conversation, Message, User

router = APIRouter()


class MessageSearchResult(BaseModel):
    """Search result for a message."""
    message_id: str
    conversation_id: str
    conversation_title: str
    role: str
    content: str
    created_at: datetime
    snippet: str = Field(description="Highlighted snippet of matching content")
    tokens_used: int = 0
    
    class Config:
        from_attributes = True


class ConversationSearchResult(BaseModel):
    """Search result for a conversation."""
    conversation_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int
    total_tokens: int
    last_message_preview: Optional[str] = None
    is_archived: bool = False
    is_pinned: bool = False
    tags: List[str] = []
    
    class Config:
        from_attributes = True


class SearchResponse(BaseModel):
    """Combined search response."""
    conversations: List[ConversationSearchResult]
    messages: List[MessageSearchResult]
    total_conversations: int
    total_messages: int
    total_results: int


@router.get("/search/messages", response_model=List[MessageSearchResult])
async def search_messages(
    query: str = Query(..., min_length=2, description="Search query"),
    conversation_id: Optional[str] = None,
    role: Optional[str] = Query(None, regex="^(user|assistant|system|tool)$"),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Search through messages with various filters.
    
    Supports:
    - Full-text search across message content
    - Filtering by conversation, role, and date range
    - Pagination with offset/limit
    - Snippet generation showing match context
    """
    # Build base query - join with conversations to ensure user owns them
    search_query = db.query(Message).join(Conversation).filter(
        and_(
            Conversation.user_id == current_user.id,
            Conversation.is_deleted == False,
            Message.content.contains(query)  # Case-insensitive search
        )
    )
    
    # Apply filters
    if conversation_id:
        search_query = search_query.filter(Message.conversation_id == conversation_id)
    
    if role:
        search_query = search_query.filter(Message.role == role)
    
    if start_date:
        search_query = search_query.filter(Message.created_at >= start_date)
    
    if end_date:
        search_query = search_query.filter(Message.created_at <= end_date)
    
    # Execute query with pagination
    messages = search_query.order_by(desc(Message.created_at)).limit(limit).offset(offset).all()
    
    # Format results with snippets
    search_results = []
    for msg in messages:
        # Create snippet around the match
        content_lower = msg.content.lower()
        query_lower = query.lower()
        match_pos = content_lower.find(query_lower)
        
        if match_pos != -1:
            # Show context around the match
            snippet_start = max(0, match_pos - 50)
            snippet_end = min(len(msg.content), match_pos + len(query) + 50)
            snippet = msg.content[snippet_start:snippet_end]
            
            # Add ellipsis if truncated
            if snippet_start > 0:
                snippet = "..." + snippet
            if snippet_end < len(msg.content):
                snippet = snippet + "..."
        else:
            # Fallback to first 100 chars if no match found (shouldn't happen)
            snippet = msg.content[:100] + ("..." if len(msg.content) > 100 else "")
        
        search_results.append(
            MessageSearchResult(
                message_id=msg.id,
                conversation_id=msg.conversation_id,
                conversation_title=msg.conversation.title,
                role=msg.role,
                content=msg.content,
                created_at=msg.created_at,
                snippet=snippet,
                tokens_used=msg.tokens_used or 0
            )
        )
    
    return search_results


@router.get("/search/conversations", response_model=List[ConversationSearchResult])
async def search_conversations(
    query: str = Query(..., min_length=2, description="Search query"),
    include_archived: bool = Query(False),
    tags: Optional[str] = Query(None, description="Comma-separated tags to filter"),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Search conversations by title, system prompt, or message content.
    
    Supports:
    - Search in title and system prompts
    - Tag filtering
    - Date range filtering
    - Archive filtering
    - Pagination
    """
    # Build base query
    search_query = db.query(Conversation).filter(
        and_(
            Conversation.user_id == current_user.id,
            Conversation.is_deleted == False,
            or_(
                Conversation.title.contains(query),
                Conversation.system_prompt.contains(query)
            )
        )
    )
    
    # Filter archived
    if not include_archived:
        search_query = search_query.filter(Conversation.is_archived == False)
    
    # Filter by tags
    if tags:
        tag_list = [t.strip() for t in tags.split(",")]
        for tag in tag_list:
            search_query = search_query.filter(Conversation.tags.contains([tag]))
    
    # Apply date filters
    if start_date:
        search_query = search_query.filter(Conversation.created_at >= start_date)
    
    if end_date:
        search_query = search_query.filter(Conversation.created_at <= end_date)
    
    # Execute query with ordering
    conversations = search_query.order_by(
        desc(Conversation.is_pinned),
        desc(Conversation.updated_at)
    ).limit(limit).offset(offset).all()
    
    # Format results
    search_results = []
    for conv in conversations:
        # Get last message for preview
        last_msg = db.query(Message).filter(
            Message.conversation_id == conv.id
        ).order_by(desc(Message.created_at)).first()
        
        last_preview = None
        if last_msg:
            preview_length = 100
            last_preview = last_msg.content[:preview_length]
            if len(last_msg.content) > preview_length:
                last_preview += "..."
        
        search_results.append(
            ConversationSearchResult(
                conversation_id=conv.id,
                title=conv.title,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
                message_count=conv.message_count or 0,
                total_tokens=conv.total_tokens or 0,
                last_message_preview=last_preview,
                is_archived=conv.is_archived,
                is_pinned=conv.is_pinned,
                tags=conv.tags or []
            )
        )
    
    return search_results


@router.get("/search/all", response_model=SearchResponse)
async def search_all(
    query: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(10, ge=1, le=50, description="Limit per category"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Search across both conversations and messages.
    
    Returns combined results from all categories with total counts.
    This is useful for a unified search experience.
    """
    # Search conversations
    conversations = await search_conversations(
        query=query,
        limit=limit,
        offset=0,
        current_user=current_user,
        db=db,
    )
    
    # Search messages
    messages = await search_messages(
        query=query,
        limit=limit,
        offset=0,
        current_user=current_user,
        db=db,
    )
    
    # Get total counts (without limits)
    total_conversations = db.query(func.count(Conversation.id)).filter(
        and_(
            Conversation.user_id == current_user.id,
            Conversation.is_deleted == False,
            or_(
                Conversation.title.contains(query),
                Conversation.system_prompt.contains(query)
            )
        )
    ).scalar()
    
    total_messages = db.query(func.count(Message.id)).join(Conversation).filter(
        and_(
            Conversation.user_id == current_user.id,
            Conversation.is_deleted == False,
            Message.content.contains(query)
        )
    ).scalar()
    
    return SearchResponse(
        conversations=conversations,
        messages=messages,
        total_conversations=total_conversations,
        total_messages=total_messages,
        total_results=total_conversations + total_messages,
    )


@router.get("/search/recent", response_model=List[ConversationSearchResult])
async def get_recent_conversations(
    limit: int = Query(10, ge=1, le=50),
    include_archived: bool = Query(False),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get recently updated conversations.
    
    Useful for quick access to recent work.
    """
    query = db.query(Conversation).filter(
        Conversation.user_id == current_user.id,
        Conversation.is_deleted == False
    )
    
    if not include_archived:
        query = query.filter(Conversation.is_archived == False)
    
    conversations = query.order_by(
        desc(Conversation.is_pinned),
        desc(Conversation.updated_at)
    ).limit(limit).all()
    
    results = []
    for conv in conversations:
        # Get last message for preview
        last_msg = db.query(Message).filter(
            Message.conversation_id == conv.id
        ).order_by(desc(Message.created_at)).first()
        
        last_preview = None
        if last_msg:
            last_preview = last_msg.content[:100]
            if len(last_msg.content) > 100:
                last_preview += "..."
        
        results.append(
            ConversationSearchResult(
                conversation_id=conv.id,
                title=conv.title,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
                message_count=conv.message_count or 0,
                total_tokens=conv.total_tokens or 0,
                last_message_preview=last_preview,
                is_archived=conv.is_archived,
                is_pinned=conv.is_pinned,
                tags=conv.tags or []
            )
        )
    
    return results


@router.get("/search/tags", response_model=List[str])
async def get_all_tags(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get all unique tags used by the user's conversations.
    
    Useful for tag autocomplete and filtering.
    """
    # Get all conversations with tags
    conversations = db.query(Conversation.tags).filter(
        Conversation.user_id == current_user.id,
        Conversation.is_deleted == False,
        Conversation.tags.isnot(None)
    ).all()
    
    # Collect all unique tags
    all_tags = set()
    for (tags,) in conversations:
        if tags:
            all_tags.update(tags)
    
    return sorted(list(all_tags))
