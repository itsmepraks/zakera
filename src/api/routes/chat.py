from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
import asyncio, json, logging

from ..database import get_db, SessionLocal
from ..models import Conversation, Message, User
from ..auth import get_current_active_user, decode_access_token
from ...model.providers import (
    OpenAIProvider, AnthropicProvider, GeminiProvider, LocalModelProvider, ModelProvider
)
from ...model.memory import ConversationMemory

logger = logging.getLogger(__name__)

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


def _get_provider(model_name: str) -> ModelProvider:
    """Resolve a provider instance from a model name string."""
    model_name_lower = model_name.lower()
    if model_name_lower.startswith("gpt"):
        return OpenAIProvider(model_name=model_name)
    elif model_name_lower.startswith("claude"):
        return AnthropicProvider(model_name=model_name)
    elif model_name_lower.startswith("gemini"):
        return GeminiProvider(model_name=model_name)
    elif model_name_lower.startswith("ollama:") or model_name_lower.startswith("local:"):
        _, actual_model = model_name.split(":", 1)
        return LocalModelProvider(model_name=actual_model)
    else:
        # Default to GPT-4 if model is unrecognised
        logger.warning(f"Unknown model '{model_name}', falling back to gpt-4-turbo-preview")
        return OpenAIProvider()


@router.post("/chat", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Send a message and get a response (requires authentication)."""
    conversation = db.query(Conversation).filter(
        Conversation.id == request.conversation_id,
        Conversation.user_id == current_user.id
    ).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Build memory from persistent history
    memory = ConversationMemory(
        max_tokens=request.max_tokens or 4000,
        conversation_id=conversation.id,
        model=conversation.model_name or "gpt-4-turbo-preview",
        system_prompt=conversation.system_prompt,
        db=db,
    )

    # Add the new user turn to memory (and persist it)
    memory.add_turn("user", request.message)

    # Resolve provider and call the model
    provider = _get_provider(conversation.model_name or "gpt-4-turbo-preview")
    try:
        from ...model.providers import Message as ProviderMessage
        provider_messages = [
            ProviderMessage(role=m["role"], content=m["content"])
            for m in memory.get_messages()
        ]
        kwargs: Dict[str, Any] = {}
        if request.temperature is not None:
            kwargs["temperature"] = request.temperature
        if request.max_tokens is not None:
            kwargs["max_tokens"] = request.max_tokens

        model_response = await provider.generate(provider_messages, **kwargs)
        assistant_content = model_response.content
        usage = model_response.usage
    except Exception as exc:
        logger.exception("Model provider error during /chat")
        raise HTTPException(status_code=502, detail=f"Model provider error: {exc}")

    # Persist the assistant turn via memory
    memory.add_turn("assistant", assistant_content)
    memory.update_conversation_stats(
        total_tokens=usage.get("total_tokens", 0)
    )

    # Retrieve the persisted assistant message for the timestamp
    assistant_message = (
        db.query(Message)
        .filter(
            Message.conversation_id == conversation.id,
            Message.role == "assistant",
        )
        .order_by(Message.created_at.desc())
        .first()
    )
    conversation.updated_at = datetime.utcnow()
    db.commit()

    return ChatResponse(
        conversation_id=conversation.id,
        message=ChatMessage(
            role="assistant",
            content=assistant_content,
            timestamp=assistant_message.created_at.isoformat() if assistant_message else datetime.utcnow().isoformat(),
        ),
        usage=usage,
    )


@router.post("/chat/stream")
async def send_message_stream(
    request: ChatRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Send a message and receive a Server-Sent Events stream of response chunks."""
    conversation = db.query(Conversation).filter(
        Conversation.id == request.conversation_id,
        Conversation.user_id == current_user.id
    ).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    memory = ConversationMemory(
        max_tokens=request.max_tokens or 4000,
        conversation_id=conversation.id,
        model=conversation.model_name or "gpt-4-turbo-preview",
        system_prompt=conversation.system_prompt,
        db=db,
    )
    memory.add_turn("user", request.message)

    provider = _get_provider(conversation.model_name or "gpt-4-turbo-preview")

    from ...model.providers import Message as ProviderMessage

    async def event_generator():
        full_response = []
        try:
            provider_messages = [
                ProviderMessage(role=m["role"], content=m["content"])
                for m in memory.get_messages()
            ]
            kwargs: Dict[str, Any] = {}
            if request.temperature is not None:
                kwargs["temperature"] = request.temperature
            if request.max_tokens is not None:
                kwargs["max_tokens"] = request.max_tokens

            async for chunk in provider.stream_generate(provider_messages, **kwargs):
                full_response.append(chunk)
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"

            assistant_content = "".join(full_response)
            memory.add_turn("assistant", assistant_content)
            conversation.updated_at = datetime.utcnow()
            db.commit()

            yield f"data: {json.dumps({'type': 'done', 'content': assistant_content})}\n\n"
        except Exception as exc:
            logger.exception("Streaming error in /chat/stream")
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.websocket("/ws/chat/{conversation_id}")
async def websocket_chat(websocket: WebSocket, conversation_id: str):
    """WebSocket streaming chat with token-based auth and real AI model integration."""
    await websocket.accept()
    db = SessionLocal()
    try:
        auth_data = await websocket.receive_text()
        auth_message = json.loads(auth_data)
        token = auth_message.get("token")
        if not token:
            await websocket.send_json({"type": "error", "message": "Authentication required."})
            await websocket.close()
            return

        token_data = decode_access_token(token)
        if not token_data or not token_data.user_id:
            await websocket.send_json({"type": "error", "message": "Invalid token"})
            await websocket.close()
            return

        user = db.query(User).filter(User.id == token_data.user_id).first()
        if not user or not user.is_active:
            await websocket.send_json({"type": "error", "message": "User not found or inactive"})
            await websocket.close()
            return

        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user.id
        ).first()
        if not conversation:
            await websocket.send_json({"type": "error", "message": "Conversation not found"})
            await websocket.close()
            return

        await websocket.send_json({"type": "authenticated", "user": user.username})

        provider = _get_provider(conversation.model_name or "gpt-4-turbo-preview")

        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            user_input = message_data.get("message", "")

            memory = ConversationMemory(
                max_tokens=4000,
                conversation_id=conversation.id,
                model=conversation.model_name or "gpt-4-turbo-preview",
                system_prompt=conversation.system_prompt,
                db=db,
            )
            memory.add_turn("user", user_input)

            from ...model.providers import Message as ProviderMessage
            provider_messages = [
                ProviderMessage(role=m["role"], content=m["content"])
                for m in memory.get_messages()
            ]

            full_response = []
            try:
                async for chunk in provider.stream_generate(provider_messages):
                    full_response.append(chunk)
                    await websocket.send_json({"type": "chunk", "content": chunk})
            except Exception as exc:
                logger.exception("WebSocket model provider error")
                await websocket.send_json({"type": "error", "message": str(exc)})
                continue

            assistant_content = "".join(full_response)
            memory.add_turn("assistant", assistant_content)
            conversation.updated_at = datetime.utcnow()
            db.commit()

            await websocket.send_json({
                "type": "complete",
                "message": {
                    "role": "assistant",
                    "content": assistant_content,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
    finally:
        db.close()
