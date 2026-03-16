from abc import ABC, abstractmethod
from typing import List, Dict, Optional, AsyncIterator, Any
from dataclasses import dataclass, field
import os
import logging

logger = logging.getLogger(__name__)


@dataclass
class Message:
    role: str
    content: str
    name: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None


@dataclass
class ToolDefinition:
    """OpenAI-compatible tool/function definition."""
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema object

    def to_openai_dict(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


@dataclass
class ModelResponse:
    content: str
    model: str
    usage: Dict[str, int]
    finish_reason: str
    tool_calls: Optional[List[Dict[str, Any]]] = None


class ModelProvider(ABC):
    """Abstract base class for AI model providers."""

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = api_key
        self.model_name = model_name

    @abstractmethod
    async def generate(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        **kwargs,
    ) -> ModelResponse:
        pass

    @abstractmethod
    async def stream_generate(
        self,
        messages: List[Message],
        **kwargs,
    ) -> AsyncIterator[str]:
        pass

    def supports_tools(self) -> bool:
        """Return True if this provider supports function/tool calling."""
        return False


class OpenAIProvider(ModelProvider):
    """OpenAI API provider using the official openai Python SDK."""

    TOOL_CAPABLE_MODELS = {
        "gpt-4-turbo-preview", "gpt-4-turbo", "gpt-4o", "gpt-4o-mini",
        "gpt-4", "gpt-3.5-turbo", "gpt-3.5-turbo-16k",
    }

    def __init__(self, api_key: Optional[str] = None, model_name: str = "gpt-4-turbo-preview"):
        super().__init__(api_key or os.getenv("OPENAI_API_KEY"), model_name)

    def supports_tools(self) -> bool:
        return self.model_name in self.TOOL_CAPABLE_MODELS

    def _get_client(self):
        from openai import AsyncOpenAI
        if not self.api_key:
            raise ValueError("OpenAI API key is required.")
        return AsyncOpenAI(api_key=self.api_key)

    @staticmethod
    def _messages_to_dicts(messages: List[Message]) -> List[Dict[str, Any]]:
        result = []
        for msg in messages:
            entry: Dict[str, Any] = {"role": msg.role, "content": msg.content or ""}
            if msg.name:
                entry["name"] = msg.name
            if msg.tool_calls:
                entry["tool_calls"] = msg.tool_calls
            if msg.tool_call_id:
                entry["tool_call_id"] = msg.tool_call_id
                entry["role"] = "tool"
            result.append(entry)
        return result

    async def generate(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        **kwargs,
    ) -> ModelResponse:
        client = self._get_client()
        params: Dict[str, Any] = {
            "model": self.model_name,
            "messages": self._messages_to_dicts(messages),
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 2048),
            "top_p": kwargs.get("top_p", 1.0),
            "presence_penalty": kwargs.get("presence_penalty", 0.0),
            "frequency_penalty": kwargs.get("frequency_penalty", 0.0),
        }
        if tools and self.supports_tools():
            params["tools"] = [t.to_openai_dict() for t in tools]
            params["tool_choice"] = kwargs.get("tool_choice", "auto")
        if "stop" in kwargs:
            params["stop"] = kwargs["stop"]

        response = await client.chat.completions.create(**params)
        choice = response.choices[0]
        usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        }
        raw_tool_calls = None
        if choice.message.tool_calls:
            raw_tool_calls = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in choice.message.tool_calls
            ]
        return ModelResponse(
            content=choice.message.content or "",
            model=response.model,
            usage=usage,
            finish_reason=choice.finish_reason or "stop",
            tool_calls=raw_tool_calls,
        )

    async def stream_generate(self, messages: List[Message], **kwargs) -> AsyncIterator[str]:
        client = self._get_client()
        params: Dict[str, Any] = {
            "model": self.model_name,
            "messages": self._messages_to_dicts(messages),
            "stream": True,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 2048),
        }
        async with await client.chat.completions.create(**params) as stream:
            async for chunk in stream:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta and delta.content:
                    yield delta.content


class AnthropicProvider(ModelProvider):
    """Anthropic Claude API provider."""

    EXTENDED_CONTEXT_MODELS = {
        "claude-3-opus-20240229", "claude-3-sonnet-20240229",
        "claude-3-haiku-20240307", "claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022",
    }

    def __init__(self, api_key=None, model_name="claude-3-sonnet-20240229"):
        super().__init__(api_key or os.getenv("ANTHROPIC_API_KEY"), model_name)

    def _get_client(self):
        from anthropic import AsyncAnthropic
        if not self.api_key:
            raise ValueError("Anthropic API key is required.")
        return AsyncAnthropic(api_key=self.api_key)

    @staticmethod
    def _extract_system_prompt(messages: List[Message]):
        if messages and messages[0].role == "system":
            return messages[0].content, messages[1:]
        return None, messages

    async def generate(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        **kwargs,
    ) -> ModelResponse:
        client = self._get_client()
        system_prompt, conversation = self._extract_system_prompt(messages)
        create_kwargs: Dict[str, Any] = {
            "model": self.model_name,
            "max_tokens": kwargs.get("max_tokens", 2048),
            "messages": [
                {"role": m.role, "content": m.content}
                for m in conversation
                if m.role in ("user", "assistant")
            ],
            "temperature": kwargs.get("temperature", 1.0),
        }
        if system_prompt:
            create_kwargs["system"] = system_prompt
        response = await client.messages.create(**create_kwargs)
        text_content = "".join(
            block.text for block in response.content if hasattr(block, "text")
        )
        usage = {
            "prompt_tokens": response.usage.input_tokens,
            "completion_tokens": response.usage.output_tokens,
            "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
        }
        return ModelResponse(
            content=text_content, model=response.model, usage=usage,
            finish_reason=response.stop_reason or "stop",
        )

    async def stream_generate(self, messages: List[Message], **kwargs) -> AsyncIterator[str]:
        client = self._get_client()
        system_prompt, conversation = self._extract_system_prompt(messages)
        create_kwargs: Dict[str, Any] = {
            "model": self.model_name,
            "max_tokens": kwargs.get("max_tokens", 2048),
            "messages": [{"role": m.role, "content": m.content} for m in conversation],
            "temperature": kwargs.get("temperature", 1.0),
        }
        if system_prompt:
            create_kwargs["system"] = system_prompt
        async with client.messages.stream(**create_kwargs) as stream:
            async for text in stream.text_stream:
                yield text


class GeminiProvider(ModelProvider):
    """Google Gemini API provider via REST (httpx)."""

    VALID_MODELS = [
        "gemini-pro", "gemini-pro-vision",
        "gemini-1.5-pro", "gemini-1.5-flash",
        "gemini-2.0-flash", "gemini-2.0-pro",
    ]

    def __init__(self, api_key=None, model_name="gemini-1.5-flash"):
        super().__init__(api_key or os.getenv("GOOGLE_API_KEY"), model_name)
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        if model_name not in self.VALID_MODELS:
            logger.warning(
                f"GeminiProvider: model '{model_name}' not in known list {self.VALID_MODELS}. Proceeding anyway."
            )

    def _convert_messages_to_gemini_format(self, messages: List[Message]) -> List[Dict]:
        converted = []
        for m in messages:
            if m.role == "system":
                # Gemini doesn't have a system role; prepend as a user turn
                converted.append({"role": "user", "parts": [{"text": f"[System] {m.content}"}]})
            else:
                converted.append({
                    "role": "model" if m.role == "assistant" else "user",
                    "parts": [{"text": m.content}],
                })
        return converted

    async def generate(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        **kwargs,
    ) -> ModelResponse:
        import httpx, json as _json
        payload: Dict[str, Any] = {
            "contents": self._convert_messages_to_gemini_format(messages),
            "generationConfig": {
                "temperature": kwargs.get("temperature", 0.7),
                "topP": kwargs.get("top_p", 0.95),
                "topK": kwargs.get("top_k", 40),
                "maxOutputTokens": kwargs.get("max_tokens", 2048),
            },
        }
        url = f"{self.base_url}/models/{self.model_name}:generateContent?key={self.api_key}"
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()
            candidate = result["candidates"][0]
            content = candidate["content"]["parts"][0]["text"]
            usage_meta = result.get("usageMetadata", {})
            usage = {
                "prompt_tokens": usage_meta.get("promptTokenCount", 0),
                "completion_tokens": usage_meta.get("candidatesTokenCount", 0),
                "total_tokens": usage_meta.get("totalTokenCount", 0),
            }
            return ModelResponse(
                content=content, model=self.model_name, usage=usage,
                finish_reason=candidate.get("finishReason", "STOP").lower(),
            )

    async def stream_generate(self, messages: List[Message], **kwargs) -> AsyncIterator[str]:
        import httpx, json as _json
        payload: Dict[str, Any] = {
            "contents": self._convert_messages_to_gemini_format(messages),
            "generationConfig": {
                "temperature": kwargs.get("temperature", 0.7),
                "topP": kwargs.get("top_p", 0.95),
                "topK": kwargs.get("top_k", 40),
                "maxOutputTokens": kwargs.get("max_tokens", 2048),
            },
        }
        url = f"{self.base_url}/models/{self.model_name}:streamGenerateContent?key={self.api_key}&alt=sse"
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", url, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        try:
                            data = _json.loads(line[6:])
                            if "candidates" in data:
                                parts = data["candidates"][0].get("content", {}).get("parts", [])
                                if parts and "text" in parts[0]:
                                    yield parts[0]["text"]
                        except _json.JSONDecodeError:
                            continue


class LocalModelProvider(ModelProvider):
    """Local model provider via Ollama REST API (http://localhost:11434)."""

    def __init__(self, base_url: str = "http://localhost:11434", model_name: str = "llama2"):
        super().__init__(None, model_name)
        self.base_url = base_url.rstrip("/")

    async def generate(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        **kwargs,
    ) -> ModelResponse:
        import httpx, json as _json
        # Ollama /api/chat supports the messages format
        payload = {
            "model": self.model_name,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
            "options": {
                "temperature": kwargs.get("temperature", 0.7),
                "num_predict": kwargs.get("max_tokens", 2048),
            },
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(f"{self.base_url}/api/chat", json=payload)
            response.raise_for_status()
            result = response.json()
            content = result.get("message", {}).get("content", "")
            usage = {
                "prompt_tokens": result.get("prompt_eval_count", 0),
                "completion_tokens": result.get("eval_count", 0),
                "total_tokens": result.get("prompt_eval_count", 0) + result.get("eval_count", 0),
            }
            return ModelResponse(
                content=content, model=self.model_name, usage=usage,
                finish_reason=result.get("done_reason", "stop"),
            )

    async def stream_generate(self, messages: List[Message], **kwargs) -> AsyncIterator[str]:
        import httpx, json as _json
        payload = {
            "model": self.model_name,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": True,
            "options": {
                "temperature": kwargs.get("temperature", 0.7),
                "num_predict": kwargs.get("max_tokens", 2048),
            },
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", f"{self.base_url}/api/chat", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        data = _json.loads(line)
                        chunk = data.get("message", {}).get("content", "")
                        if chunk:
                            yield chunk
                        if data.get("done"):
                            break
                    except _json.JSONDecodeError:
                        continue
