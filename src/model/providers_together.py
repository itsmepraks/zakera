"""
Together AI model provider for Zakera.

Together AI provides a hosted inference API for 50+ open-source models
(Llama 3, Mistral, Qwen, DBRX, DeepSeek, Gemma, …) via an OpenAI-compatible
chat-completions endpoint.  This provider follows the same pattern as the
existing providers in src/model/providers.py so it integrates seamlessly with
the ModelManager and fallback strategies.

Documentation: https://docs.together.ai/reference/chat-completions
"""

from __future__ import annotations

import json
import os
from typing import AsyncIterator, Dict, List, Optional

from .providers import Message, ModelProvider, ModelResponse

# ---------------------------------------------------------------------------
# Model catalogue (subset – add more as Together updates its offering)
# ---------------------------------------------------------------------------
TOGETHER_MODELS: Dict[str, Dict] = {
    # Meta Llama 3.x
    "meta-llama/Llama-3.3-70B-Instruct-Turbo": {
        "context_length": 131_072,
        "capabilities": ["chat", "code"],
    },
    "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo": {
        "context_length": 131_072,
        "capabilities": ["chat"],
    },
    "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo": {
        "context_length": 131_072,
        "capabilities": ["chat", "code"],
    },
    "meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo": {
        "context_length": 131_072,
        "capabilities": ["chat", "code"],
    },
    # Mistral
    "mistralai/Mistral-7B-Instruct-v0.3": {
        "context_length": 32_768,
        "capabilities": ["chat"],
    },
    "mistralai/Mixtral-8x7B-Instruct-v0.1": {
        "context_length": 32_768,
        "capabilities": ["chat", "code"],
    },
    "mistralai/Mixtral-8x22B-Instruct-v0.1": {
        "context_length": 65_536,
        "capabilities": ["chat", "code"],
    },
    # Qwen
    "Qwen/Qwen2.5-72B-Instruct-Turbo": {
        "context_length": 32_768,
        "capabilities": ["chat", "code"],
    },
    "Qwen/Qwen2.5-7B-Instruct-Turbo": {
        "context_length": 32_768,
        "capabilities": ["chat"],
    },
    # DeepSeek
    "deepseek-ai/DeepSeek-V3": {
        "context_length": 131_072,
        "capabilities": ["chat", "code"],
    },
    "deepseek-ai/DeepSeek-R1": {
        "context_length": 131_072,
        "capabilities": ["chat", "reasoning"],
    },
    # Google Gemma
    "google/gemma-2-9b-it": {
        "context_length": 8_192,
        "capabilities": ["chat"],
    },
    "google/gemma-2-27b-it": {
        "context_length": 8_192,
        "capabilities": ["chat", "code"],
    },
    # Databricks DBRX
    "databricks/dbrx-instruct": {
        "context_length": 32_768,
        "capabilities": ["chat", "code"],
    },
    # Microsoft Phi
    "microsoft/WizardLM-2-8x22B": {
        "context_length": 65_536,
        "capabilities": ["chat", "reasoning"],
    },
    # NousResearch
    "NousResearch/Nous-Hermes-2-Mixtral-8x7B-DPO": {
        "context_length": 32_768,
        "capabilities": ["chat"],
    },
}

DEFAULT_MODEL = "meta-llama/Llama-3.3-70B-Instruct-Turbo"
TOGETHER_BASE_URL = "https://api.together.xyz/v1"


class TogetherAIProvider(ModelProvider):
    """Together AI inference provider.

    Supports chat completion and streaming for any model available on
    Together's platform via their OpenAI-compatible REST API.

    Args:
        api_key:    Together AI API key.  Falls back to ``TOGETHER_API_KEY``
                    env-var when not provided.
        model_name: Together model identifier (see ``TOGETHER_MODELS``).
                    Defaults to Llama-3.3-70B-Instruct-Turbo.
    """

    BASE_URL = TOGETHER_BASE_URL

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = DEFAULT_MODEL,
    ) -> None:
        super().__init__(
            api_key=api_key or os.getenv("TOGETHER_API_KEY"),
            model_name=model_name,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _headers(self) -> Dict[str, str]:
        if not self.api_key:
            raise ValueError(
                "Together AI API key is required.  Set the TOGETHER_API_KEY "
                "environment variable or pass api_key= to TogetherAIProvider."
            )
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _messages_to_dicts(messages: List[Message]) -> List[Dict]:
        """Convert internal Message objects to OpenAI-style dicts."""
        result = []
        for msg in messages:
            entry: Dict = {"role": msg.role, "content": msg.content}
            if msg.name:
                entry["name"] = msg.name
            result.append(entry)
        return result

    def _build_payload(self, messages: List[Message], stream: bool, **kwargs) -> Dict:
        payload: Dict = {
            "model": self.model_name,
            "messages": self._messages_to_dicts(messages),
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 2048),
            "top_p": kwargs.get("top_p", 0.9),
            "stream": stream,
        }
        if "stop" in kwargs:
            payload["stop"] = kwargs["stop"]
        if "repetition_penalty" in kwargs:
            payload["repetition_penalty"] = kwargs["repetition_penalty"]
        return payload

    # ------------------------------------------------------------------
    # ModelProvider interface
    # ------------------------------------------------------------------

    async def generate(self, messages: List[Message], **kwargs) -> ModelResponse:
        """Send a blocking chat-completion request to Together AI.

        Supported kwargs:
            temperature (float):      Sampling temperature.  Default 0.7.
            max_tokens (int):         Max tokens to generate.  Default 2048.
            top_p (float):            Nucleus sampling.  Default 0.9.
            stop (list[str]):         Stop sequences.
            repetition_penalty (float): Penalise token repetition.  Default off.
        """
        import httpx

        payload = self._build_payload(messages, stream=False, **kwargs)
        url = f"{self.BASE_URL}/chat/completions"

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, headers=self._headers(), json=payload)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            body = exc.response.text
            if status == 401:
                raise ValueError(f"Together AI authentication failed: {body}") from exc
            if status == 429:
                raise RuntimeError(f"Together AI rate limit exceeded: {body}") from exc
            raise RuntimeError(f"Together AI API error {status}: {body}") from exc
        except httpx.ConnectError as exc:
            raise RuntimeError(f"Could not connect to Together AI API: {exc}") from exc

        choice = data["choices"][0]
        usage_raw = data.get("usage", {})
        usage = {
            "prompt_tokens": usage_raw.get("prompt_tokens", 0),
            "completion_tokens": usage_raw.get("completion_tokens", 0),
            "total_tokens": usage_raw.get("total_tokens", 0),
        }
        return ModelResponse(
            content=choice["message"]["content"] or "",
            model=data.get("model", self.model_name),
            usage=usage,
            finish_reason=choice.get("finish_reason") or "stop",
        )

    async def stream_generate(
        self, messages: List[Message], **kwargs
    ) -> AsyncIterator[str]:
        """Stream a chat completion from Together AI using SSE.

        Yields text delta chunks as they arrive.
        Supported kwargs are the same as :meth:`generate`.
        """
        import httpx

        payload = self._build_payload(messages, stream=True, **kwargs)
        url = f"{self.BASE_URL}/chat/completions"

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST", url, headers=self._headers(), json=payload
                ) as response:
                    response.raise_for_status()
                    async for raw_line in response.aiter_lines():
                        line = raw_line.strip()
                        if not line or not line.startswith("data:"):
                            continue
                        data_str = line[len("data:"):].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue
                        choices = chunk.get("choices", [])
                        if not choices:
                            continue
                        delta = choices[0].get("delta", {})
                        text = delta.get("content") or ""
                        if text:
                            yield text
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            body = exc.response.text
            if status == 401:
                raise ValueError(f"Together AI authentication failed: {body}") from exc
            if status == 429:
                raise RuntimeError(f"Together AI rate limit exceeded: {body}") from exc
            raise RuntimeError(f"Together AI API error {status}: {body}") from exc
        except httpx.ConnectError as exc:
            raise RuntimeError(f"Could not connect to Together AI API: {exc}") from exc

    # ------------------------------------------------------------------
    # Additional helpers exposed by this provider
    # ------------------------------------------------------------------

    @classmethod
    def list_models(cls) -> List[Dict]:
        """Return catalogue metadata for all built-in Together AI models."""
        return [
            {"id": model_id, **meta}
            for model_id, meta in TOGETHER_MODELS.items()
        ]

    @classmethod
    def get_model_info(cls, model_id: str) -> Optional[Dict]:
        """Return metadata for a specific model, or None if unknown."""
        meta = TOGETHER_MODELS.get(model_id)
        if meta is None:
            return None
        return {"id": model_id, **meta}

    def supports_capability(self, capability: str) -> bool:
        """Check whether the current model supports a given capability.

        Args:
            capability: One of ``'chat'``, ``'code'``, ``'reasoning'``.

        Returns:
            True if the model declares the capability, False otherwise.
            Unknown models are assumed to support 'chat'.
        """
        meta = TOGETHER_MODELS.get(self.model_name)
        if meta is None:
            return capability == "chat"
        return capability in meta.get("capabilities", [])

    async def health_check(self) -> Dict:
        """Perform a lightweight API reachability check.

        Sends a minimal single-token request and returns a status dict
        suitable for the /monitoring/health endpoint.
        """
        try:
            response = await self.generate(
                messages=[Message(role="user", content="ping")],
                max_tokens=1,
                temperature=0.0,
            )
            return {
                "provider": "together_ai",
                "status": "healthy",
                "model": self.model_name,
                "latency_ms": None,  # timing can be added by the caller
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "provider": "together_ai",
                "status": "unhealthy",
                "model": self.model_name,
                "error": str(exc),
            }


# Backwards-compatible alias expected by older registry/import paths.
TogetherProvider = TogetherAIProvider
