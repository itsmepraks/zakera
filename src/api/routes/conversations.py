from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import uuid

router = APIRouter()

# In-memory storage for demo (replace with database)
conversations_db = {}

class ConversationCreate(BaseModel):
    title: Optional[str] = "New Conversation"
    system_prompt: Optional[str] = None

class ConversationResponse(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int

@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(conversation: ConversationCreate):
    """Create a new conversation"""
    conv_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat()
    
    conversations_db[conv_id] = {
        "id": conv_id,
        "title": conversation.title,
        "system_prompt": conversation.system_prompt,
        "created_at": timestamp,
        "updated_at": timestamp,
        "messages": [],
        "metadata": {}
    }
    
    return ConversationResponse(
        id=conv_id,
        title=conversation.title,
        created_at=timestamp,
        updated_at=timestamp,
        message_count=0
    )

@router.get("/conversations", response_model=List[ConversationResponse])
async def list_conversations(skip: int = 0, limit: int = 20):
    """List all conversations"""
    convs = list(conversations_db.values())
    convs.sort(key=lambda x: x["updated_at"], reverse=True)
    
    return [
        ConversationResponse(
            id=c["id"],
            title=c["title"],
            created_at=c["created_at"],
            updated_at=c["updated_at"],
            message_count=len(c["messages"])
        )
        for c in convs[skip:skip+limit]
    ]

@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Get a specific conversation with its messages"""
    if conversation_id not in conversations_db:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return conversations_db[conversation_id]

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a conversation"""
    if conversation_id not in conversations_db:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    del conversations_db[conversation_id]
    return {"message": "Conversation deleted successfully"}
