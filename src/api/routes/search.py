"""
Search endpoints for finding conversations and messages.
"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from ..auth import get_current_user
from ..database import get_db
from ..models import Conversation, Message, User

router = APIRouter(prefix="/search", tags=["search"])


class MessageSearchResult(BaseModel):
    """Search result for a message."""
    message_id: str
    conversation_id: str
    conversation_title: str
    role: str
    content: str
    created_at: datetime
    snippet: str = Field(description="Highlighted snippet of matching content")


class ConversationSearchResult(BaseModel):
    """Search result for a conversation."""
    conversation_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int
    last_message_preview: Optional[str] = None


class SearchResponse(BaseModel):
    """Combined search response."""
    conversations: List[ConversationSearchResult]
    messages: List[MessageSearchResult]
    total_results: int


@router.get("/messages", response_model=List[MessageSearchResult])
async def search_messages(
    query: str = Query(..., min_length=2, description="Search query"),
    conversation_id: Optional[str] = None,
    role: Optional[str] = Query(None, regex="^(user|assistant|system)$"),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Search through messages with various filters.
    
    Supports:
    - Full-text search across message content
    - Filtering by conversation, role, and date range
    - Pagination
    """
    # Build base query
    search_query = db.query(Message).join(Conversation).filter(
        and_(
            Conversation.user_id == current_user.id,
            Message.content.ilike(f"%{query}%"),
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
    results = await db.execute(
        search_query.order_by(Message.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    messages = results.scalars().all()
    
    # Format results with snippets
    search_results = []
    for msg in messages:
        # Create snippet around the match
        content_lower = msg.content.lower()
        query_lower = query.lower()
        match_pos = content_lower.find(query_lower)
        
        if match_pos != -1:
            start = max(0, match_pos - 50)
            end = min(len(msg.content), match_pos + len(query) + 50)
            snippet = msg.content[start:end]
            if start > 0:
                snippet = "..." + snippet
            if end < len(msg.content):
                snippet = snippet + "..."
        else:
            snippet = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
        
        search_results.append(
            MessageSearchResult(
                message_id=msg.id,
                conversation_id=msg.conversation_id,
                conversation_title=msg.conversation.title if hasattr(msg, "conversation") else "Unknown",
                role=msg.role,
                content=msg.content,
                created_at=msg.created_at,
                snippet=snippet,
            )
        )
    
    return search_results


@router.get("/conversations", response_model=List[ConversationSearchResult])
async def search_conversations(
    query: str = Query(..., min_length=2, description="Search query"),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Search conversations by title or content.
    """
    # Search in conversation titles
    search_query = db.query(Conversation).filter(
        and_(
            Conversation.user_id == current_user.id,
            Conversation.title.ilike(f"%{query}%"),
        )
    )
    
    # Apply date filters
    if start_date:
        search_query = search_query.filter(Conversation.created_at >= start_date)
    
    if end_date:
        search_query = search_query.filter(Conversation.created_at <= end_date)
    
    # Execute query
    results = await db.execute(
        search_query.order_by(Conversation.updated_at.desc())
        .limit(limit)
        .offset(offset)
    )
    conversations = results.scalars().all()
    
    # Format results
    search_results = []
    for conv in conversations:
        # Get message count
        msg_count = await db.execute(
            func.count(Message.id).filter(Message.conversation_id == conv.id)
        )
        msg_count = msg_count.scalar() or 0
        
        # Get last message preview
        last_msg = await db.execute(
            db.query(Message)
            .filter(Message.conversation_id == conv.id)
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        last_msg = last_msg.scalar_one_or_none()
        last_preview = last_msg.content[:100] if last_msg else None
        
        search_results.append(
            ConversationSearchResult(
                conversation_id=conv.id,
                title=conv.title,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
                message_count=msg_count,
                last_message_preview=last_preview,
            )
        )
    
    return search_results


@router.get("/all", response_model=SearchResponse)
async def search_all(
    query: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(10, ge=1, le=50, description="Limit per category"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Search across both conversations and messages.
    
    Returns combined results from all categories.
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
    
    return SearchResponse(
        conversations=conversations,
        messages=messages,
        total_results=len(conversations) + len(messages),
    )
