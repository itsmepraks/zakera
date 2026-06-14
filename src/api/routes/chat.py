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
from ...model.providers import (
    GeminiProvider,
    LocalModelProvider,
    ModelProvider,
    OpenAIProvider,
    OpenRouterProvider,
)
from ...model.providers_anthropic import AnthropicProvider
from ...model.providers_deepseek import DeepSeekProvider, DeepSeekConfig
from ...model.providers_groq import GroqProvider
from ...model.providers_mistral import MistralProvider
from ...model.providers_perplexity import PerplexityProvider
from ...model.providers_fireworks import FireworksProvider
from ...model.memory import ConversationMemory
from ...tools.manager import get_tool_manager
from ..services.agent_run_service import AgentRunService

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
    run_id: Optional[str] = None
    run_status: Optional[str] = None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_provider(model_name: str) -> ModelProvider:
    """Resolve a ModelProvider instance from a model-name string."""
    model_name_lower = model_name.lower()
    if model_name_lower.startswith("openrouter/"):
        actual_model = model_name.split("/", 1)[1]
        if actual_model in {"auto", "free"}:
            actual_model = model_name
        return OpenRouterProvider(model_name=actual_model)
    elif model_name_lower.startswith("~"):
        return OpenRouterProvider(model_name=model_name)
    elif model_name_lower.startswith("gpt"):
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
    elif model_name_lower.startswith("deepseek/"):
        actual_model = model_name.split("/", 1)[1]
        return DeepSeekProvider(
            DeepSeekConfig(
                api_key=os.getenv("DEEPSEEK_API_KEY", ""),
                model=actual_model,
            )
        )
    elif model_name_lower.startswith("mistral/"):
        actual_model = model_name.split("/", 1)[1]
        return MistralProvider(model_name=actual_model)
    elif model_name_lower.startswith("perplexity/"):
        actual_model = model_name.split("/", 1)[1]
        return PerplexityProvider(model_name=actual_model)
    elif model_name_lower.startswith("fireworks/"):
        actual_model = model_name.split("/", 1)[1]
        return FireworksProvider(model_name=actual_model)
    elif model_name_lower.startswith("ollama:") or model_name_lower.startswith("local:"):
        _, actual_model = model_name.split(":", 1)
        return LocalModelProvider(model_name=actual_model)
    else:
        logger.warning("Unknown model '%s', falling back to gpt-4-turbo-preview", model_name)
        return OpenAIProvider()


def _extract_tool_calls(model_response: Any) -> List[Dict[str, Any]]:
    """Return tool-call payloads from a model response, if present."""
    tool_calls = getattr(model_response, "tool_calls", None) or []
    if tool_calls:
        return tool_calls

    metadata = getattr(model_response, "metadata", None)
    if isinstance(metadata, dict):
        return metadata.get("tool_calls") or []

    return []


def _message_dict_to_provider_message(message: Dict[str, Any]):
    """Convert a persisted message dictionary into a Provider Message object."""
    from ...model.providers import Message as ProviderMessage

    return ProviderMessage(
        role=message["role"],
        content=message["content"],
        name=message.get("name"),
        tool_calls=message.get("tool_calls"),
        tool_call_id=message.get("tool_call_id"),
    )


def _coerce_tool_arguments(arguments: Any) -> Dict[str, Any]:
    """Best-effort conversion of tool arguments into a dict."""
    if isinstance(arguments, dict):
        return arguments

    if isinstance(arguments, str):
        try:
            parsed = json.loads(arguments)
        except json.JSONDecodeError:
            return {"input": arguments}

        if isinstance(parsed, dict):
            return parsed
        return {"input": parsed}

    return {}


def _serialize_tool_content(payload: Any) -> str:
    """Serialize tool results for storage and prompt replay."""
    if isinstance(payload, str):
        return payload

    try:
        return json.dumps(payload, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(payload)


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
    tool_calls = _extract_tool_calls(model_response)

    if not tool_calls:
        return model_response.content, model_response.usage or {}

    # ---- Execute tools (in parallel) --------------------------------------
    tool_manager = get_tool_manager()
    logger.info("Executing %d tool call(s) requested by the model", len(tool_calls))

    call_specs: List[Dict[str, Any]] = []
    for tool_call in tool_calls:
        if not isinstance(tool_call, dict):
            continue

        function = tool_call.get("function")
        if not isinstance(function, dict):
            function = {}

        name = function.get("name") or tool_call.get("name")
        if not name:
            continue

        raw_arguments = function.get(
            "arguments",
            tool_call.get("arguments", tool_call.get("parameters", {})),
        )

        call_specs.append(
            {
                "id": tool_call.get("id") or tool_call.get("tool_call_id"),
                "name": name,
                "parameters": _coerce_tool_arguments(raw_arguments),
            }
        )

    if not call_specs:
        return model_response.content, model_response.usage or {}

    tool_results = await tool_manager.execute_tools_parallel(
        [(spec["name"], spec["parameters"]) for spec in call_specs]
    )

    # ---- Build tool-result messages and persist them ----------------------
    tool_results_summary: List[Dict[str, Any]] = []
    for spec, result in zip(call_specs, tool_results):
        tool_payload = result.data if result.success else {"error": result.error}
        tool_content = _serialize_tool_content(tool_payload)

        tool_metadata = {
            "tool_call_id": spec.get("id"),
            "tool_name": spec["name"],
            "success": result.success,
            "execution_time": result.execution_time,
        }
        memory.add_turn("tool", tool_content, metadata=tool_metadata)
        provider_messages.append(
            ProviderMessage(
                role="tool",
                content=tool_content,
                name=spec["name"],
                tool_call_id=spec.get("id"),
            )
        )

        tool_results_summary.append(
            {
                "id": spec.get("id"),
                "tool": spec["name"],
                "parameters": spec["parameters"],
                "success": result.success,
                "result": tool_payload,
                "execution_time": result.execution_time,
            }
        )
        logger.debug(
            "Tool '%s' finished | success=%s | time=%.2fs",
            spec["name"],
            result.success,
            result.execution_time or 0.0,
        )

    tool_turn_content = json.dumps(tool_results_summary, ensure_ascii=False)

    # ---- Get the final response after tool execution ----------------------
    try:
        final_response = await provider.generate(provider_messages, **gen_kwargs)
        return final_response.content, final_response.usage or {}
    except Exception as exc:
        logger.exception("Model provider error on post-tool follow-up call")
        fallback = f"{model_response.content}\n\n" f"[Tool results: {tool_turn_content}]"
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
    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.id == request.conversation_id,
            Conversation.user_id == current_user.id,
        )
        .first()
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    try:
        service = AgentRunService(db=db, provider_factory=_get_provider)
        result = await service.run_chat(
            conversation=conversation,
            user=current_user,
            message=request.message,
            tools_enabled=request.tools_enabled,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
        assistant_content = result.content
        usage = result.usage

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Model provider error during POST /chat")
        raise HTTPException(status_code=502, detail=f"Model provider error: {exc}")

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
        run_id=result.run.id,
        run_status=result.run.status,
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
    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.id == request.conversation_id,
            Conversation.user_id == current_user.id,
        )
        .first()
    )
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
        provider_messages = [_message_dict_to_provider_message(m) for m in history]
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
        conversation.id,
        effective_model,
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
    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.id == request.conversation_id,
            Conversation.user_id == current_user.id,
        )
        .first()
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    async def event_generator():
        service = AgentRunService(db=db, provider_factory=_get_provider)
        try:
            async for event in service.stream_chat(
                conversation=conversation,
                user=current_user,
                message=request.message,
                tools_enabled=request.tools_enabled,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            ):
                yield f"data: {json.dumps(event)}\n\n"
                if event.get("type") == "agent.response.chunk":
                    yield f"data: {json.dumps({'type': 'chunk', 'content': event.get('chunk', '')})}\n\n"
                elif event.get("type") == "agent.done":
                    yield f"data: {json.dumps({'type': 'done', 'run_id': event.get('run_id'), 'status': event.get('status')})}\n\n"

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

        conversation = (
            db.query(Conversation)
            .filter(
                Conversation.id == conversation_id,
                Conversation.user_id == user.id,
            )
            .first()
        )
        if not conversation:
            await websocket.send_json({"type": "error", "message": "Conversation not found"})
            await websocket.close()
            return

        await websocket.send_json({"type": "authenticated", "user": user.username})

        provider = _get_provider(conversation.model_name or "gpt-4-turbo-preview")

        # Main message loop.
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

            provider_messages = [
                _message_dict_to_provider_message(m) for m in memory.get_messages()
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

            await websocket.send_json(
                {
                    "type": "complete",
                    "message": {
                        "role": "assistant",
                        "content": assistant_content,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                }
            )

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        try:
            await websocket.send_json({"type": "error", "message": str(exc)})
        except Exception:
            pass
    finally:
        db.close()
