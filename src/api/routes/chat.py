from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import asyncio
import json

router = APIRouter()

# Import from conversations to access shared storage
from .conversations import conversations_db

class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
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
async def send_message(request: ChatRequest):
    """Send a message and get a response"""
    if request.conversation_id not in conversations_db:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    conversation = conversations_db[request.conversation_id]
    timestamp = datetime.utcnow().isoformat()
    
    # Add user message to conversation
    user_message = {
        "role": "user",
        "content": request.message,
        "timestamp": timestamp
    }
    conversation["messages"].append(user_message)
    
    # TODO: Replace with actual AI model call
    # For now, return a simple echo response
    assistant_response = f"Echo: {request.message}\n\n[This is a placeholder. Integrate with your AI model provider.]"
    
    assistant_message = {
        "role": "assistant",
        "content": assistant_response,
        "timestamp": datetime.utcnow().isoformat()
    }
    conversation["messages"].append(assistant_message)
    conversation["updated_at"] = datetime.utcnow().isoformat()
    
    return ChatResponse(
        conversation_id=request.conversation_id,
        message=ChatMessage(**assistant_message),
        usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    )

@router.websocket("/ws/chat/{conversation_id}")
async def websocket_chat(websocket: WebSocket, conversation_id: str):
    """WebSocket endpoint for streaming chat responses"""
    await websocket.accept()
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Validate conversation exists
            if conversation_id not in conversations_db:
                await websocket.send_json({
                    "type": "error",
                    "message": "Conversation not found"
                })
                break
            
            conversation = conversations_db[conversation_id]
            
            # Add user message
            user_message = {
                "role": "user",
                "content": message_data.get("message", ""),
                "timestamp": datetime.utcnow().isoformat()
            }
            conversation["messages"].append(user_message)
            
            # TODO: Stream response from AI model
            # For now, simulate streaming
            response_text = f"Streaming response to: {message_data.get('message', '')}"
            
            # Send streaming chunks
            for chunk in response_text.split():
                await websocket.send_json({
                    "type": "chunk",
                    "content": chunk + " "
                })
                await asyncio.sleep(0.1)  # Simulate delay
            
            # Send completion signal
            assistant_message = {
                "role": "assistant",
                "content": response_text,
                "timestamp": datetime.utcnow().isoformat()
            }
            conversation["messages"].append(assistant_message)
            
            await websocket.send_json({
                "type": "complete",
                "message": assistant_message
            })
            
    except WebSocketDisconnect:
        print(f"Client disconnected from conversation {conversation_id}")
    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })
