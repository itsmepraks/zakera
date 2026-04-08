from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
import asyncio, json, logging
import os

from ..database import get_db, SessionLocal
from ..models import Conversation, Message, User
from ..auth import get_current_active_user, decode_access_token
from ..config import settings
from ...model.providers import (
    OpenAIProvider, AnthropicProvider, GeminiProvider, GroqProvider, LocalModelProvider, ModelProvider
)
from ...model.providers_deepseek import DeepSeekProvider, DeepSeekConfig
from ...model.providers_mistral import MistralProvider
from ...model.providers_perplexity import PerplexityProvider
from ...model.memory import ConversationMemory
from ...tools.manager import get_tool_manager

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

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
    tools_enabled: bool = Field(
        default=False,
        description=(
            "When True, the model may return tool-call requests that are "
            "automatically executed before producing the final reply."
        ),
    )


class ChatRetryRequest(BaseModel):
    """Request body for POST /chat/retry."""

    conversation_id: str = Field(
        ...,
        description="ID of the conversation whose last assistant message should be regenerated.",
    )
    temperature: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=2.0,
        description="Sampling temperature for this retry (overrides conversation default).",
    )
    max_tokens: Optional[int] = Field(
        default=None,
        gt=0,
        description="Maximum tokens to generate for this retry.",
    )
    model_override: Optional[str] = Field(
        default=None,
        description=(
            "Use a different model for this single retry without permanently "
            "changing the conversation's model."
        ),
    )


class ChatResponse(BaseModel):
    conversation_id: str
    message: ChatMessage
    usage: Optional[Dict[str, int]] = None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_provider(model_name: str) -> ModelProvider:
    """Resolve a ModelProvider instance from a model-name string."""
    model_name_lower = model_name.lower()
    deepseek_aliases = {
        "deepseek-v3": "deepseek-chat",
        "deepseek-r1": "deepseek-reasoner",
        "v3": "deepseek-chat",
        "r1": "deepseek-reasoner",
    }

    if model_name_lower.startswith("gpt"):
        return OpenAIProvider(model_name=model_name)
    elif model_name_lower.startswith("claude"):
        return AnthropicProvider(model_name=model_name)
    elif model_name_lower.startswith("gemini"):
        return GeminiProvider(model_name=model_name)
    elif model_name_lower.startswith("llama3-70b-8192") or model_name_lower.startswith("groq/"):
        actual_model = model_name
        if model_name_lower.startswith("groq/"):
            actual_model = model_name[5:]
        return GroqProvider(model_name=actual_model)
    elif model_name_lower in deepseek_aliases or model_name_lower.startswith("deepseek/"):
        if model_name_lower.startswith("deepseek/"):
            actual_model = model_name.split("/", 1)[1]
            actual_model = deepseek_aliases.get(actual_model.lower(), actual_model)
        else:
            actual_model = deepseek_aliases[model_name_lower]
        return DeepSeekProvider(
            DeepSeekConfig(
                api_key=settings.DEEPSEEK_API_KEY,
                api_base=settings.DEEPSEEK_API_BASE,
                model=actual_model,
            )
        )
    elif model_name_lower.startswith("mistral/"):
        actual_model = model_name.split("/", 1)[1]
        return MistralProvider(model_name=actual_model)
    elif model_name_lower.startswith("perplexity/"):
        actual_model = model_name.split("/", 1)[1]
        return PerplexityProvider(model_name=actual_model)
    elif model_name_lower.startswith("ollama:") or model_name_lower.startswith("local:"):
        _, actual_model = model_name.split(":", 1)
        return LocalModelProvider(model_name=actual_model)
    else:
        logger.warning("Unknown model '%s', falling back to gpt-4-turbo-preview", model_name)
        return OpenAIProvider()


async def _maybe_run_tools(
    model_response: Any,
    provider: ModelProvider,
    provider_messages: List[Any],
    memory: "ConversationMemory",
    gen_kwargs: Dict[str, Any],
) -> tuple[str, Dict[str, int]]:
    """
    Check whether *model_response* contains tool-call requests.  If it does,
    execute them via the global :class:`~src.tools.manager.ToolManager`,
    append the results to *provider_messages*, and obtain a final response
    from the model.

    When no tool calls are present the original response is returned unchanged.

    Args:
        model_response:   The initial :class:`~src.model.providers.ModelResponse`.
        provider:         The active :class:`~src.model.providers.ModelProvider`.
        provider_messages: Mutable list of messages already sent to the model.
        memory:           The live :class:`~src.model.memory.ConversationMemory`
                          for the current conversation (used to persist tool turns).
        gen_kwargs:       Extra kwargs forwarded to the model on the follow-up call.

    Returns:
        ``(assistant_content, usage)`` — the final assistant text and the usage
        dict from the last model call.
    """
    from ...model.providers import Message as ProviderMessage

    # ---- Detect tool calls ------------------------------------------------
    # Providers express tool calls in metadata["tool_calls"] as a list of
    # {"name": str, "parameters": dict} dicts.  Some providers may embed
    # a JSON blob directly in the content instead; we try both.
    tool_calls: List[Dict[str, Any]] = []

    if model_response.metadata:
        tool_calls = model_response.metadata.get("tool_calls") or []

    # Fallback: try to parse content as JSON if no metadata tool_calls
    if not tool_calls and model_response.content:
        try:
            parsed = json.loads(model_response.content)
            if isinstance(parsed, dict) and "tool_calls" in parsed:
                tool_calls = parsed["tool_calls"]
        except (json.JSONDecodeError, TypeError):
            pass

    if not tool_calls:
        # No tool calls — return the original response as-is.
        return model_response.content, model_response.usage or {}

    # ---- Execute tools (in parallel) --------------------------------------
    tool_manager = get_tool_manager()
    logger.info("Executing %d tool call(s) requested by the model", len(tool_calls))

    call_pairs = [
        (tc["name"], tc.get("parameters") or tc.get("arguments") or {})
        for tc in tool_calls
        if tc.get("name")
    ]

    tool_results = await tool_manager.execute_tools_parallel(call_pairs)

    # ---- Build tool-result messages and persist them ----------------------
    tool_results_summary: List[Dict[str, Any]] = []
    for (tool_name, tool_params), result in zip(call_pairs, tool_results):
        summary = {
            "tool": tool_name,
            "parameters": tool_params,
            "success": result.success,
            "result": result.data if result.success else {"error": result.error},
            "execution_time": result.execution_time,
        }
        tool_results_summary.append(summary)
        logger.debug(
            "Tool '%s' finished | success=%s | time=%.2fs",
            tool_name, result.success, result.execution_time or 0.0,
        )

    # Append a synthetic "tool" turn so the model knows what happened.
    tool_turn_content = json.dumps(tool_results_summary, ensure_ascii=False)
    memory.add_turn("tool", tool_turn_content)
    provider_messages.append(
        ProviderMessage(role="tool", content=tool_turn_content)
    )

    # ---- Get the final response after tool execution ----------------------
    try:
        final_response = await provider.generate(provider_messages, **gen_kwargs)
        return final_response.content, final_response.usage or {}
    except Exception as exc:
        logger.exception("Model provider error on post-tool follow-up call")
        # Fall back gracefully: return the model's original (pre-tool) content
        # rather than raising and losing the tool results entirely.
        fallback = (
            f"{model_response.content}\n\n"
            f"[Tool results: {tool_turn_content}]"
        )
        return fallback, model_response.usage or {}


# ---------------------------------------------------------------------------
# POST /chat  — non-streaming
# ---------------------------------------------------------------------------

@router.post("/chat", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Send a message and get a response (requires authentication).

    When ``tools_enabled=True`` the model may request tool executions;
    these are performed automatically before the final reply is returned.
    """
    conversation = db.query(Conversation).filter(
        Conversation.id == request.conversation_id,
        Conversation.user_id == current_user.id,
    ).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Build memory from persistent history and add the new user turn.
    memory = ConversationMemory(
        max_tokens=request.max_tokens or 4000,
        conversation_id=conversation.id,
        model=conversation.model_name or "gpt-4-turbo-preview",
        system_prompt=conversation.system_prompt,
        db=db,
    )
    memory.add_turn("user", request.message)

    provider = _get_provider(conversation.model_name or "gpt-4-turbo-preview")

    try:
        from ...model.providers import Message as ProviderMessage

        provider_messages = [
            ProviderMessage(role=m["role"], content=m["content"])
            for m in memory.get_messages()
        ]
        gen_kwargs: Dict[str, Any] = {}
        if request.temperature is not None:
            gen_kwargs["temperature"] = request.temperature
        if request.max_tokens is not None:
            gen_kwargs["max_tokens"] = request.max_tokens
        if request.tools_enabled:
            gen_kwargs["tools_enabled"] = True

        model_response = await provider.generate(provider_messages, **gen_kwargs)

        if request.tools_enabled:
            assistant_content, usage = await _maybe_run_tools(
                model_response, provider, provider_messages, memory, gen_kwargs
            )
        else:
            assistant_content = model_response.content
            usage = model_response.usage or {}

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Model provider error during POST /chat")
        raise HTTPException(status_code=502, detail=f"Model provider error: {exc}")

    # Persist the assistant turn and update stats.
    memory.add_turn("assistant", assistant_content)
    memory.update_conversation_stats(total_tokens=usage.get("total_tokens", 0))

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
            timestamp=(
                assistant_message.created_at.isoformat()
                if assistant_message
                else datetime.utcnow().isoformat()
            ),
            metadata={"tools_used": request.tools_enabled},
        ),
        usage=usage,
    )


# ---------------------------------------------------------------------------
# POST /chat/retry
# ---------------------------------------------------------------------------

@router.post("/chat/retry", response_model=ChatResponse)
async def retry_last_message(
    request: ChatRetryRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Regenerate the last assistant reply in a conversation.

    Deletes the most-recent assistant :class:`~src.api.models.Message` from
    the database, then re-runs the model over the remaining history.  Callers
    can optionally supply a different ``temperature``, ``max_tokens``, or
    ``model_override`` for this single call without permanently altering the
    conversation record.

    Raises:
        404: Conversation not found or does not belong to the current user.
        400: The conversation has no assistant messages to retry.
        502: The upstream model provider returned an error.
    """
    # ---- Fetch & authorise the conversation --------------------------------
    conversation = db.query(Conversation).filter(
        Conversation.id == request.conversation_id,
        Conversation.user_id == current_user.id,
    ).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # ---- Find and delete the last assistant message -----------------------
    last_assistant_msg = (
        db.query(Message)
        .filter(
            Message.conversation_id == conversation.id,
            Message.role == "assistant",
        )
        .order_by(Message.created_at.desc())
        .first()
    )

    if last_assistant_msg is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "No assistant messages found in this conversation. "
                "Send at least one message before retrying."
            ),
        )

    # Also remove any "tool" turns that were produced as part of the same
    # assistant turn (i.e. turns created after the last *user* message and
    # before / at the same time as the assistant message we just found).
    last_user_msg = (
        db.query(Message)
        .filter(
            Message.conversation_id == conversation.id,
            Message.role == "user",
        )
        .order_by(Message.created_at.desc())
        .first()
    )

    if last_user_msg is None:
        # Conversation contains only assistant messages — should not normally
        # happen, but guard against it gracefully.
        raise HTTPException(
            status_code=400,
            detail="Conversation history is malformed (no user messages found).",
        )

    # Delete tool turns that sit between the last user message and now.
    db.query(Message).filter(
        Message.conversation_id == conversation.id,
        Message.role == "tool",
        Message.created_at > last_user_msg.created_at,
    ).delete(synchronize_session=False)

    # Delete the last assistant message.
    db.delete(last_assistant_msg)
    db.flush()  # apply deletes before rebuilding memory

    # ---- Rebuild memory from the trimmed history --------------------------
    effective_model = request.model_override or conversation.model_name or "gpt-4-turbo-preview"

    memory = ConversationMemory(
        max_tokens=request.max_tokens or 4000,
        conversation_id=conversation.id,
        model=effective_model,
        system_prompt=conversation.system_prompt,
        db=db,
    )

    history = memory.get_messages()
    if not history:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="No messages remain after removing the last assistant turn.",
        )

    # ---- Call the model ---------------------------------------------------
    provider = _get_provider(effective_model)

    try:
        from ...model.providers import Message as ProviderMessage

        provider_messages = [
            ProviderMessage(role=m["role"], content=m["content"])
            for m in history
        ]
        gen_kwargs: Dict[str, Any] = {}
        if request.temperature is not None:
            gen_kwargs["temperature"] = request.temperature
        if request.max_tokens is not None:
            gen_kwargs["max_tokens"] = request.max_tokens

        model_response = await provider.generate(provider_messages, **gen_kwargs)
        assistant_content = model_response.content
        usage = model_response.usage or {}

    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        logger.exception("Model provider error during POST /chat/retry")
        raise HTTPException(status_code=502, detail=f"Model provider error: {exc}")

    # ---- Persist the new assistant turn -----------------------------------
    memory.add_turn("assistant", assistant_content)
    memory.update_conversation_stats(total_tokens=usage.get("total_tokens", 0))

    new_assistant_message = (
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

    logger.info(
        "Retry successful for conversation %s | model=%s",
        conversation.id, effective_model,
    )

    return ChatResponse(
        conversation_id=conversation.id,
        message=ChatMessage(
            role="assistant",
            content=assistant_content,
            timestamp=(
                new_assistant_message.created_at.isoformat()
                if new_assistant_message
                else datetime.utcnow().isoformat()
            ),
            metadata={
                "retried": True,
                "model_used": effective_model,
                "model_overridden": request.model_override is not None,
            },
        ),
        usage=usage,
    )


# ---------------------------------------------------------------------------
# POST /chat/stream  — SSE
# ---------------------------------------------------------------------------

@router.post("/chat/stream")
async def send_message_stream(
    request: ChatRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Send a message and receive a Server-Sent Events stream of response chunks.

    Note: ``tools_enabled`` is honoured for the initial model call.  If the
    model requests tool executions those are performed synchronously before
    the streamed reply begins, so the client receives a single continuous
    stream of the final answer.
    """
    conversation = db.query(Conversation).filter(
        Conversation.id == request.conversation_id,
        Conversation.user_id == current_user.id,
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
        full_response: List[str] = []
        try:
            provider_messages = [
                ProviderMessage(role=m["role"], content=m["content"])
                for m in memory.get_messages()
            ]
            gen_kwargs: Dict[str, Any] = {}
            if request.temperature is not None:
                gen_kwargs["temperature"] = request.temperature
            if request.max_tokens is not None:
                gen_kwargs["max_tokens"] = request.max_tokens
            if request.tools_enabled:
                gen_kwargs["tools_enabled"] = True

            # ----- Tool-use pre-flight (non-streaming) ---------------------
            # If tools are enabled we first do a non-streaming generate to
            # check for tool calls, execute them, then stream the final reply.
            if request.tools_enabled:
                init_response = await provider.generate(provider_messages, **gen_kwargs)
                tool_calls = (init_response.metadata or {}).get("tool_calls") or []

                if tool_calls:
                    yield f"data: {json.dumps({'type': 'status', 'message': 'executing_tools'})}\n\n"
                    assistant_content, usage = await _maybe_run_tools(
                        init_response, provider, provider_messages, memory, gen_kwargs
                    )
                    # Emit the final answer as a single chunk then done.
                    yield f"data: {json.dumps({'type': 'chunk', 'content': assistant_content})}\n\n"
                    memory.add_turn("assistant", assistant_content)
                    conversation.updated_at = datetime.utcnow()
                    db.commit()
                    yield f"data: {json.dumps({'type': 'done', 'content': assistant_content})}\n\n"
                    return
                else:
                    # No tool calls — stream the initial response content.
                    full_response.append(init_response.content)
                    yield f"data: {json.dumps({'type': 'chunk', 'content': init_response.content})}\n\n"
                    assistant_content = init_response.content
                    memory.add_turn("assistant", assistant_content)
                    conversation.updated_at = datetime.utcnow()
                    db.commit()
                    yield f"data: {json.dumps({'type': 'done', 'content': assistant_content})}\n\n"
                    return

            # ----- Normal streaming path (tools_enabled=False) -------------
            async for chunk in provider.stream_generate(provider_messages, **gen_kwargs):
                full_response.append(chunk)
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"

            assistant_content = "".join(full_response)
            memory.add_turn("assistant", assistant_content)
            conversation.updated_at = datetime.utcnow()
            db.commit()

            yield f"data: {json.dumps({'type': 'done', 'content': assistant_content})}\n\n"

        except Exception as exc:
            logger.exception("Streaming error in POST /chat/stream")
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ---------------------------------------------------------------------------
# WebSocket /ws/chat/{conversation_id}
# ---------------------------------------------------------------------------

@router.websocket("/ws/chat/{conversation_id}")
async def websocket_chat(websocket: WebSocket, conversation_id: str):
    """WebSocket streaming chat with token-based auth and real AI model integration."""
    await websocket.accept()
    db = SessionLocal()
    try:
        # First message must be the auth token.
        auth_data    = await websocket.receive_text()
        auth_message = json.loads(auth_data)
        token        = auth_message.get("token")
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
            Conversation.user_id == user.id,
        ).first()
        if not conversation:
            await websocket.send_json({"type": "error", "message": "Conversation not found"})
            await websocket.close()
            return

        await websocket.send_json({"type": "authenticated", "user": user.username})

        provider = _get_provider(conversation.model_name or "gpt-4-turbo-preview")

        # Main message loop.
        while True:
            data         = await websocket.receive_text()
            message_data = json.loads(data)
            user_input   = message_data.get("message", "")

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

            full_response: List[str] = []
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
                    "role":      "assistant",
                    "content":   assistant_content,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            })

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        try:
            await websocket.send_json({"type": "error", "message": str(exc)})
        except Exception:
            pass
    finally:
        db.close()
