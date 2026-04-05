"""DeepInfra provider for Zakera AI Chat Agent.

DeepInfra exposes an OpenAI-compatible Chat Completions API, so this provider
mirrors the request/response shape used by OpenAIProvider while targeting the
DeepInfra endpoint.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, AsyncIterator, Dict, List, Optional, Union

import httpx

from .providers import Message, ModelProvider, ModelResponse, ToolDefinition

logger = logging.getLogger(__name__)

DEEPINFRA_API_BASE = "https://api.deepinfra.com/v1/openai"
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_BASE = 2.0
DEFAULT_TIMEOUT = 120.0


class DeepInfraModel(str, Enum):
    """Common DeepInfra model identifiers."""

    LLAMA_3_70B_CHAT_HF = "meta-llama/Llama-3-70b-chat-hf"
    LLAMA_3_8B_CHAT_HF = "meta-llama/Llama-3-8b-chat-hf"
    LLAMA_3_1_70B_INSTRUCT = "meta-llama/Llama-3.1-70B-Instruct"
    LLAMA_3_1_8B_INSTRUCT = "meta-llama/Llama-3.1-8B-Instruct"
    MIXTRAL_8X7B_INSTRUCT = "mistralai/Mixtral-8x7B-Instruct-v0.1"
    MISTRAL_7B_INSTRUCT = "mistralai/Mistral-7B-Instruct-v0.3"
    MYTHOMAX_L2_13B = "Gryphe/MythoMax-L2-13b"
    GEMMA_2_27B_IT = "google/gemma-2-27b-it"
    QWEN2_5_72B_INSTRUCT = "Qwen/Qwen2.5-72B-Instruct"
    DEEPSEEK_R1_DISTILL_LLAMA_70B = "deepseek-ai/DeepSeek-R1-Distill-Llama-70B"

    @classmethod
    def values(cls) -> List[str]:
        return [model.value for model in cls]


SUPPORTED_DEEPINFRA_MODELS = tuple(DeepInfraModel.values())
DEFAULT_DEEPINFRA_MODEL = DeepInfraModel.LLAMA_3_70B_CHAT_HF.value


@dataclass
class DeepInfraConfig:
    """Configuration for the DeepInfra provider."""

    api_key: str
    model: str = DEFAULT_DEEPINFRA_MODEL
    api_base: str = DEEPINFRA_API_BASE
    max_tokens: int = 4096
    temperature: float = 0.7
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    max_retries: int = DEFAULT_MAX_RETRIES
    timeout: float = DEFAULT_TIMEOUT
    organization: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.api_key:
            raise ValueError("DeepInfra api_key must not be empty.")
        if self.max_retries < 0:
            raise ValueError("max_retries must be >= 0")
        if self.timeout <= 0:
            raise ValueError("timeout must be > 0")
        if self.model not in SUPPORTED_DEEPINFRA_MODELS:
            logger.warning(
                "DeepInfraConfig: model '%s' is not in the curated list %s. Proceeding anyway.",
                self.model,
                SUPPORTED_DEEPINFRA_MODELS,
            )


@dataclass
class TokenUsage:
    """Tracks token usage for a single request."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    model: str = ""
    request_id: Optional[str] = None

    @classmethod
    def from_response(
        cls,
        data: Dict[str, Any],
        model: str,
        request_id: Optional[str] = None,
    ) -> "TokenUsage":
        usage = data.get("usage", {})
        return cls(
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
            model=model,
            request_id=request_id,
        )


class DeepInfraProvider(ModelProvider):
    """Async DeepInfra provider using the OpenAI-compatible API surface."""

    PROVIDER_NAME = "deepinfra"

    def __init__(self, config: DeepInfraConfig) -> None:
        super().__init__(api_key=config.api_key, model_name=config.model)
        self.config = config
        self._client: Optional[httpx.AsyncClient] = None
        self._total_usage: TokenUsage = TokenUsage(model=config.model)

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            headers: Dict[str, str] = {
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            }
            if self.config.organization:
                headers["DeepInfra-Organization"] = self.config.organization
            self._client = httpx.AsyncClient(
                base_url=self.config.api_base.rstrip("/"),
                headers=headers,
                timeout=httpx.Timeout(self.config.timeout),
            )
        return self._client

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "DeepInfraProvider":
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()

    def supports_tools(self) -> bool:
        """DeepInfra is OpenAI-compatible, so tool calling is supported."""
        return True

    @staticmethod
    def _messages_to_dicts(messages: List[Message]) -> List[Dict[str, Any]]:
        result: List[Dict[str, Any]] = []
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

    def _build_payload(
        self,
        messages: List[Message],
        *,
        stream: bool = False,
        tools: Optional[List[ToolDefinition]] = None,
        tool_choice: Optional[Union[str, Dict[str, Any]]] = None,
        response_format: Optional[Dict[str, Any]] = None,
        seed: Optional[int] = None,
        stop: Optional[Union[str, List[str]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        presence_penalty: Optional[float] = None,
        frequency_penalty: Optional[float] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "model": self.model_name,
            "messages": self._messages_to_dicts(messages),
            "stream": stream,
            "temperature": self.config.temperature if temperature is None else temperature,
            "max_tokens": self.config.max_tokens if max_tokens is None else max_tokens,
            "top_p": self.config.top_p if top_p is None else top_p,
            "presence_penalty": self.config.presence_penalty if presence_penalty is None else presence_penalty,
            "frequency_penalty": self.config.frequency_penalty if frequency_penalty is None else frequency_penalty,
        }

        if tools:
            payload["tools"] = [tool.to_openai_dict() for tool in tools]
            if tool_choice is not None:
                payload["tool_choice"] = tool_choice
        if response_format:
            payload["response_format"] = response_format
        if seed is not None:
            payload["seed"] = seed
        if stop is not None:
            payload["stop"] = stop
        if stream:
            payload["stream_options"] = {"include_usage": True}

        return payload

    @staticmethod
    def _is_retryable(status_code: int) -> bool:
        return status_code in {429, 500, 502, 503, 504}

    async def _post_with_retry(self, endpoint: str, payload: Dict[str, Any]) -> httpx.Response:
        client = await self._get_client()
        last_exc: Optional[Exception] = None

        for attempt in range(self.config.max_retries + 1):
            try:
                response = await client.post(endpoint, json=payload)
                if response.status_code == 200 or not self._is_retryable(response.status_code):
                    return response

                wait = DEFAULT_BACKOFF_BASE ** attempt
                logger.warning(
                    "DeepInfra request failed (status=%s), retrying in %.1fs (attempt %d/%d)",
                    response.status_code,
                    wait,
                    attempt + 1,
                    self.config.max_retries,
                )
                last_exc = RuntimeError(f"HTTP {response.status_code}: {response.text[:200]}")
                await asyncio.sleep(wait)
            except httpx.RequestError as exc:
                wait = DEFAULT_BACKOFF_BASE ** attempt
                logger.warning("DeepInfra network error: %s, retrying in %.1fs", exc, wait)
                last_exc = exc
                await asyncio.sleep(wait)

        raise RuntimeError(f"DeepInfra request failed after {self.config.max_retries} retries") from last_exc

    async def generate(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        **kwargs,
    ) -> ModelResponse:
        payload = self._build_payload(
            messages,
            stream=False,
            tools=tools,
            tool_choice=kwargs.get("tool_choice", "auto"),
            response_format=kwargs.get("response_format"),
            seed=kwargs.get("seed"),
            stop=kwargs.get("stop"),
            temperature=kwargs.get("temperature", self.config.temperature),
            max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
            top_p=kwargs.get("top_p", self.config.top_p),
            presence_penalty=kwargs.get("presence_penalty", self.config.presence_penalty),
            frequency_penalty=kwargs.get("frequency_penalty", self.config.frequency_penalty),
        )
        response = await self._post_with_retry("/chat/completions", payload)
        if response.status_code != 200:
            raise RuntimeError(f"DeepInfra API error {response.status_code}: {response.text[:500]}")

        data = response.json()
        choice = data["choices"][0]
        message = choice["message"]
        request_id = response.headers.get("x-request-id")
        usage = TokenUsage.from_response(data, model=data.get("model", self.model_name), request_id=request_id)
        self._accumulate_usage(usage)

        return ModelResponse(
            content=message.get("content") or "",
            model=data.get("model", self.model_name),
            usage={
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "total_tokens": usage.total_tokens,
            },
            finish_reason=choice.get("finish_reason") or "stop",
            tool_calls=message.get("tool_calls"),
        )

    async def stream_generate(self, messages: List[Message], **kwargs) -> AsyncIterator[str]:
        payload = self._build_payload(
            messages,
            stream=True,
            tools=kwargs.get("tools"),
            tool_choice=kwargs.get("tool_choice"),
            response_format=kwargs.get("response_format"),
            seed=kwargs.get("seed"),
            stop=kwargs.get("stop"),
            temperature=kwargs.get("temperature", self.config.temperature),
            max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
            top_p=kwargs.get("top_p", self.config.top_p),
            presence_penalty=kwargs.get("presence_penalty", self.config.presence_penalty),
            frequency_penalty=kwargs.get("frequency_penalty", self.config.frequency_penalty),
        )
        client = await self._get_client()

        async with client.stream("POST", "/chat/completions", json=payload) as response:
            if response.status_code != 200:
                body = await response.aread()
                raise RuntimeError(f"DeepInfra stream error {response.status_code}: {body.decode()[:500]}")

            async for line in response.aiter_lines():
                if not line or not line.startswith("data: "):
                    continue

                raw = line[len("data: "):].strip()
                if raw == "[DONE]":
                    break

                try:
                    event = json.loads(raw)
                except json.JSONDecodeError:
                    logger.debug("Failed to parse DeepInfra SSE line: %s", raw)
                    continue

                if event.get("usage"):
                    usage = TokenUsage.from_response(event, model=self.model_name)
                    self._accumulate_usage(usage)
                    continue

                choices = event.get("choices", [])
                if not choices:
                    continue

                delta = choices[0].get("delta", {})
                text = delta.get("content")
                if text:
                    yield text

    def _accumulate_usage(self, usage: TokenUsage) -> None:
        self._total_usage.prompt_tokens += usage.prompt_tokens
        self._total_usage.completion_tokens += usage.completion_tokens
        self._total_usage.total_tokens += usage.total_tokens

    def get_total_usage(self) -> TokenUsage:
        """Return cumulative token usage across all requests."""
        return self._total_usage

    def reset_usage(self) -> None:
        """Reset session-level token counters."""
        self._total_usage = TokenUsage(model=self.model_name)

    @classmethod
    def list_models(cls) -> List[str]:
        """Return the curated list of supported DeepInfra model IDs."""
        return list(SUPPORTED_DEEPINFRA_MODELS)

    def __repr__(self) -> str:
        return f"DeepInfraProvider(model={self.model_name!r})"


def create_deepinfra_provider(settings: Dict[str, Any]) -> DeepInfraProvider:
    """Convenience factory that builds a DeepInfra provider from settings."""
    config = DeepInfraConfig(
        api_key=settings["deepinfra_api_key"],
        model=settings.get("deepinfra_model", DEFAULT_DEEPINFRA_MODEL),
        api_base=settings.get("deepinfra_api_base", DEEPINFRA_API_BASE),
        max_tokens=int(settings.get("deepinfra_max_tokens", 4096)),
        temperature=float(settings.get("deepinfra_temperature", 0.7)),
        top_p=float(settings.get("deepinfra_top_p", 1.0)),
        frequency_penalty=float(settings.get("deepinfra_frequency_penalty", 0.0)),
        presence_penalty=float(settings.get("deepinfra_presence_penalty", 0.0)),
        max_retries=int(settings.get("deepinfra_max_retries", DEFAULT_MAX_RETRIES)),
        timeout=float(settings.get("deepinfra_timeout", DEFAULT_TIMEOUT)),
        organization=settings.get("deepinfra_organization"),
    )
    return DeepInfraProvider(config)
