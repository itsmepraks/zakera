"""
Google Gemini 2.0 Flash Model Provider

Supports gemini-2.0-flash-exp and gemini-2.0-flash-thinking-exp variants.
Provides async streaming, native function calling, and token counting.
"""

from __future__ import annotations

import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx

from ..base import BaseModelProvider, ModelCapability, ModelMetadata, ProviderConfig
from ..exceptions import ModelProviderError, RateLimitError, TokenLimitError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"

MODEL_METADATA: Dict[str, ModelMetadata] = {
    "gemini-2.0-flash-exp": ModelMetadata(
        name="gemini-2.0-flash-exp",
        display_name="Gemini 2.0 Flash (Experimental)",
        context_window=1_048_576,  # 1 M tokens
        max_output_tokens=8192,
        input_price_per_1k=0.000075,   # USD per 1K input tokens
        output_price_per_1k=0.000300,  # USD per 1K output tokens
        capabilities=[
            ModelCapability.CHAT,
            ModelCapability.STREAMING,
            ModelCapability.FUNCTION_CALLING,
            ModelCapability.VISION,
            ModelCapability.JSON_MODE,
        ],
        supports_system_prompt=True,
    ),
    "gemini-2.0-flash-thinking-exp": ModelMetadata(
        name="gemini-2.0-flash-thinking-exp",
        display_name="Gemini 2.0 Flash Thinking (Experimental)",
        context_window=32_768,
        max_output_tokens=8192,
        input_price_per_1k=0.000075,
        output_price_per_1k=0.000300,
        capabilities=[
            ModelCapability.CHAT,
            ModelCapability.STREAMING,
            ModelCapability.FUNCTION_CALLING,
        ],
        supports_system_prompt=True,
    ),
}

DEFAULT_MODEL = "gemini-2.0-flash-exp"

DEFAULT_SAFETY_SETTINGS = [
    {"category": "HARM_CATEGORY_HARASSMENT",       "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH",       "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _convert_messages_to_gemini(
    messages: List[Dict[str, Any]],
    system_prompt: Optional[str] = None,
) -> tuple[Optional[Dict], List[Dict]]:
    """
    Convert OpenAI-style messages to the Gemini `contents` format.

    Returns (system_instruction, contents).
    """
    system_instruction = None
    if system_prompt:
        system_instruction = {"parts": [{"text": system_prompt}]}

    contents: List[Dict] = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")

        if role == "system":
            # Merge extra system messages into the system_instruction
            if system_instruction is None:
                system_instruction = {"parts": [{"text": content}]}
            else:
                system_instruction["parts"][0]["text"] += f"\n\n{content}"
            continue

        gemini_role = "model" if role == "assistant" else "user"

        if isinstance(content, str):
            parts = [{"text": content}]
        elif isinstance(content, list):
            # Multi-modal content: [{"type": "text", "text": ...}, {"type": "image_url", ...}]
            parts = []
            for item in content:
                if item.get("type") == "text":
                    parts.append({"text": item["text"]})
                elif item.get("type") == "image_url":
                    url = item["image_url"]["url"]
                    if url.startswith("data:"):
                        mime, b64data = url[5:].split(",", 1)
                        mime_type = mime.split(";")[0]
                        parts.append(
                            {"inline_data": {"mime_type": mime_type, "data": b64data}}
                        )
                    else:
                        parts.append({"file_data": {"file_uri": url}})
        else:
            parts = [{"text": str(content)}]

        contents.append({"role": gemini_role, "parts": parts})

    return system_instruction, contents


def _convert_tools_to_gemini(tools: List[Dict]) -> List[Dict]:
    """
    Convert OpenAI function-calling tool definitions to Gemini's
    `function_declarations` format.
    """
    declarations = []
    for tool in tools:
        fn = tool.get("function", {})
        declarations.append(
            {
                "name": fn.get("name"),
                "description": fn.get("description", ""),
                "parameters": fn.get("parameters", {}),
            }
        )
    return [{"function_declarations": declarations}]


# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------


class GeminiFlashProvider(BaseModelProvider):
    """
    Model provider for Google Gemini 2.0 Flash variants.

    Usage::

        provider = GeminiFlashProvider(
            config=ProviderConfig(api_key="...", model="gemini-2.0-flash-exp")
        )
        response = await provider.generate(messages=[{"role": "user", "content": "Hello!"}])
        print(response.content)
    """

    PROVIDER_ID = "gemini_flash"
    SUPPORTED_MODELS = list(MODEL_METADATA.keys())

    def __init__(self, config: ProviderConfig) -> None:
        super().__init__(config)
        self._api_key = config.api_key
        self._model = config.model or DEFAULT_MODEL
        self._timeout = config.timeout or 60.0
        self._safety_settings = config.extra.get("safety_settings", DEFAULT_SAFETY_SETTINGS)

        if self._model not in MODEL_METADATA:
            raise ModelProviderError(
                f"Unsupported model '{self._model}'. "
                f"Choose from: {self.SUPPORTED_MODELS}"
            )

        self._metadata = MODEL_METADATA[self._model]
        self._http = httpx.AsyncClient(timeout=self._timeout)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def provider_id(self) -> str:
        return self.PROVIDER_ID

    @property
    def model_metadata(self) -> ModelMetadata:
        return self._metadata

    async def generate(
        self,
        messages: List[Dict[str, Any]],
        *,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict]] = None,
        tool_choice: Optional[str] = None,
        response_format: Optional[Dict] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Generate a single (non-streaming) response.

        Returns a dict compatible with the Zakera standard response schema::

            {
                "content": str,
                "role": "assistant",
                "tool_calls": [...] | None,
                "usage": {"prompt_tokens": int, "completion_tokens": int, "total_tokens": int},
                "model": str,
                "finish_reason": str,
            }
        """
        payload = self._build_payload(
            messages,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=tools,
            tool_choice=tool_choice,
            response_format=response_format,
        )

        url = (
            f"{GEMINI_API_BASE}/models/{self._model}:generateContent"
            f"?key={self._api_key}"
        )

        logger.debug("GeminiFlash generate request model=%s", self._model)

        try:
            resp = await self._http.post(url, json=payload)
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            self._handle_http_error(exc)

        data = resp.json()
        return self._parse_response(data)

    async def generate_stream(
        self,
        messages: List[Dict[str, Any]],
        *,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict]] = None,
        **kwargs: Any,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream tokens from the Gemini API using server-sent events.

        Yields dicts::

            {"type": "delta", "content": str}          # text chunk
            {"type": "done",  "usage": {...}}           # final usage stats
        """
        payload = self._build_payload(
            messages,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=tools,
        )

        url = (
            f"{GEMINI_API_BASE}/models/{self._model}:streamGenerateContent"
            f"?key={self._api_key}&alt=sse"
        )

        logger.debug("GeminiFlash stream request model=%s", self._model)

        prompt_tokens = 0
        completion_tokens = 0

        async with self._http.stream("POST", url, json=payload) as response:
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                self._handle_http_error(exc)

            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                raw = line[6:].strip()
                if raw in ("", "[DONE]"):
                    continue

                try:
                    chunk = json.loads(raw)
                except json.JSONDecodeError:
                    logger.warning("GeminiFlash: failed to decode SSE chunk: %s", raw)
                    continue

                # Accumulate usage metadata if present
                meta = chunk.get("usageMetadata", {})
                if meta:
                    prompt_tokens = meta.get("promptTokenCount", prompt_tokens)
                    completion_tokens = meta.get("candidatesTokenCount", completion_tokens)

                candidates = chunk.get("candidates", [])
                for candidate in candidates:
                    for part in candidate.get("content", {}).get("parts", []):
                        text = part.get("text")
                        if text:
                            yield {"type": "delta", "content": text}

        yield {
            "type": "done",
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            },
        }

    async def count_tokens(self, messages: List[Dict[str, Any]]) -> int:
        """
        Count the number of tokens in the given messages using the
        Gemini countTokens endpoint (exact, not an estimate).
        """
        _, contents = _convert_messages_to_gemini(messages)
        payload = {"contents": contents}
        url = (
            f"{GEMINI_API_BASE}/models/{self._model}:countTokens"
            f"?key={self._api_key}"
        )
        try:
            resp = await self._http.post(url, json=payload)
            resp.raise_for_status()
            return resp.json().get("totalTokens", 0)
        except httpx.HTTPStatusError as exc:
            logger.warning("GeminiFlash: countTokens failed: %s", exc)
            return 0

    async def close(self) -> None:
        await self._http.aclose()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_payload(  # noqa: PLR0913
        self,
        messages: List[Dict[str, Any]],
        *,
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: Optional[int],
        tools: Optional[List[Dict]],
        tool_choice: Optional[str] = None,
        response_format: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        system_instruction, contents = _convert_messages_to_gemini(messages, system_prompt)

        generation_config: Dict[str, Any] = {"temperature": temperature}
        if max_tokens:
            generation_config["maxOutputTokens"] = max_tokens
        if response_format and response_format.get("type") == "json_object":
            generation_config["responseMimeType"] = "application/json"

        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": generation_config,
            "safetySettings": self._safety_settings,
        }
        if system_instruction:
            payload["systemInstruction"] = system_instruction
        if tools:
            payload["tools"] = _convert_tools_to_gemini(tools)
            if tool_choice == "required":
                payload["toolConfig"] = {"functionCallingConfig": {"mode": "ANY"}}
            elif tool_choice == "none":
                payload["toolConfig"] = {"functionCallingConfig": {"mode": "NONE"}}
            else:
                payload["toolConfig"] = {"functionCallingConfig": {"mode": "AUTO"}}

        return payload

    @staticmethod
    def _parse_response(data: Dict[str, Any]) -> Dict[str, Any]:
        candidates = data.get("candidates", [])
        if not candidates:
            raise ModelProviderError("Gemini returned no candidates")

        candidate = candidates[0]
        parts = candidate.get("content", {}).get("parts", [])
        finish_reason = candidate.get("finishReason", "STOP")

        content_text = ""
        tool_calls = []

        for part in parts:
            if "text" in part:
                content_text += part["text"]
            elif "functionCall" in part:
                fc = part["functionCall"]
                tool_calls.append(
                    {
                        "id": f"call_{fc['name']}",
                        "type": "function",
                        "function": {
                            "name": fc["name"],
                            "arguments": json.dumps(fc.get("args", {})),
                        },
                    }
                )

        usage_meta = data.get("usageMetadata", {})
        usage = {
            "prompt_tokens": usage_meta.get("promptTokenCount", 0),
            "completion_tokens": usage_meta.get("candidatesTokenCount", 0),
            "total_tokens": usage_meta.get("totalTokenCount", 0),
        }

        return {
            "content": content_text,
            "role": "assistant",
            "tool_calls": tool_calls or None,
            "usage": usage,
            "model": data.get("modelVersion", DEFAULT_MODEL),
            "finish_reason": finish_reason,
        }

    @staticmethod
    def _handle_http_error(exc: httpx.HTTPStatusError) -> None:
        status = exc.response.status_code
        try:
            detail = exc.response.json().get("error", {}).get("message", str(exc))
        except Exception:
            detail = str(exc)

        if status == 429:
            raise RateLimitError(f"Gemini rate limit exceeded: {detail}") from exc
        if status == 400:
            if "token" in detail.lower() or "length" in detail.lower():
                raise TokenLimitError(f"Gemini token limit: {detail}") from exc
        raise ModelProviderError(f"Gemini API error {status}: {detail}") from exc
