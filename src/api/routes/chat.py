from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
import asyncio
import json

from ..database import get_db
from ..models import Conversation, Message

router = APIRouter()

class ChatMessage(BaseModel):
    role: str
    content: str
    timestamp: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class ChatRequest(BaseModel):
    conversation_id: str
    message: str
    stream: bool = False
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None

class ChatResponse(BaseModel):
    conversation_id: str
    message: ChatMessage
    usage: Optional[Dict[str, int]] = None

@router.post("/chat", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    user_id: str = "default-user",  # TODO: Get from auth
    db: Session = Depends(get_db)
):
    """Send a message and get a response"""
    # Verify conversation exists and belongs to user
    conversation = db.query(Conversation).filter(
        Conversation.id == request.conversation_id,
        Conversation.user_id == user_id
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Add user message to database
    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        content=request.message,
        model_name=conversation.model_name
    )
    db.add(user_message)
    
    # TODO: Replace with actual AI model call
    # For now, return a simple echo response
    assistant_content = f"Echo: {request.message}\n\n[Database integrated! User message saved. TODO: Connect to AI model provider.]"
    
    # Add assistant message to database
    assistant_message = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=assistant_content,
        model_name=conversation.model_name,
        tokens_used=0  # TODO: Calculate actual tokens
    )
    db.add(assistant_message)
    
    # Update conversation timestamp
    conversation.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(assistant_message)
    
    return ChatResponse(
        conversation_id=conversation.id,
        message=ChatMessage(
            role=assistant_message.role,
            content=assistant_message.content,
            timestamp=assistant_message.created_at.isoformat()
        ),
        usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    )

@router.websocket("/ws/chat/{conversation_id}")
async def websocket_chat(
    websocket: WebSocket,
    conversation_id: str,
    user_id: str = "default-user"  # TODO: Get from auth token in WebSocket
):
    """WebSocket endpoint for streaming chat responses"""
    await websocket.accept()
    
    # Get database session
    from ..database import SessionLocal
    db = SessionLocal()
    
    try:
        # Verify conversation exists
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id
        ).first()
        
        if not conversation:
            await websocket.send_json({
                "type": "error",
                "message": "Conversation not found"
            })
            await websocket.close()
            return
        
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Add user message to database
            user_message = Message(
                conversation_id=conversation.id,
                role="user",
                content=message_data.get("message", ""),
                model_name=conversation.model_name
            )
            db.add(user_message)
            db.commit()
            
            # TODO: Stream response from AI model
            # For now, simulate streaming
            response_text = f"Streaming response to: {message_data.get('message', '')}"
            
            # Send streaming chunks
            for chunk in response_text.split():
                await websocket.send_json({
                    "type": "chunk",
                    "content": chunk + " "
                })
                await asyncio.sleep(0.1)
            
            # Save assistant message
            assistant_message = Message(
                conversation_id=conversation.id,
                role="assistant",
                content=response_text,
                model_name=conversation.model_name
            )
            db.add(assistant_message)
            conversation.updated_at = datetime.utcnow()
            db.commit()
            
            # Send completion signal
            await websocket.send_json({
                "type": "complete",
                "message": {
                    "role": "assistant",
                    "content": response_text,
                    "timestamp": assistant_message.created_at.isoformat()
                }
            })
            
    except WebSocketDisconnect:
        print(f"Client disconnected from conversation {conversation_id}")
    except Exception as e:
        print(f"WebSocket error: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except:
            pass
    finally:
        db.close()
