from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
import asyncio
import json

from ..database import get_db, SessionLocal
from ..models import Conversation, Message, User
from ..auth import get_current_active_user, decode_access_token

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
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Send a message and get a response (requires authentication)"""
    # Verify conversation exists and belongs to user
    conversation = db.query(Conversation).filter(
        Conversation.id == request.conversation_id,
        Conversation.user_id == current_user.id
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
    # For now, return a response acknowledging the authenticated user
    assistant_content = f"Hello {current_user.username}! You said: {request.message}\n\n[Authentication working! Database integrated! TODO: Connect to AI model provider.]"
    
    # Add assistant message to database
    assistant_message = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=assistant_content,
        model_name=conversation.model_name,
        tokens_used=0
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
    conversation_id: str
):
    """WebSocket endpoint for streaming chat responses (with authentication)"""
    await websocket.accept()
    
    db = SessionLocal()
    
    try:
        # Authenticate via WebSocket (token should be sent in first message)
        auth_data = await websocket.receive_text()
        auth_message = json.loads(auth_data)
        
        token = auth_message.get("token")
        if not token:
            await websocket.send_json({
                "type": "error",
                "message": "Authentication required. Send token in first message."
            })
            await websocket.close()
            return
        
        # Verify token
        token_data = decode_access_token(token)
        if not token_data or not token_data.user_id:
            await websocket.send_json({
                "type": "error",
                "message": "Invalid authentication token"
            })
            await websocket.close()
            return
        
        # Get user
        user = db.query(User).filter(User.id == token_data.user_id).first()
        if not user or not user.is_active:
            await websocket.send_json({
                "type": "error",
                "message": "User not found or inactive"
            })
            await websocket.close()
            return
        
        # Verify conversation exists and belongs to user
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user.id
        ).first()
        
        if not conversation:
            await websocket.send_json({
                "type": "error",
                "message": "Conversation not found"
            })
            await websocket.close()
            return
        
        # Send authentication success
        await websocket.send_json({
            "type": "authenticated",
            "user": user.username
        })
        
        # Handle messages
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Add user message
            user_message = Message(
                conversation_id=conversation.id,
                role="user",
                content=message_data.get("message", ""),
                model_name=conversation.model_name
            )
            db.add(user_message)
            db.commit()
            
            # TODO: Stream response from AI model
            response_text = f"Hello {user.username}! Streaming response to: {message_data.get('message', '')}"
            
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
            
            # Send completion
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
