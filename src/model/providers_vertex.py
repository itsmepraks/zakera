"""
Google Vertex AI Generative Language Provider for Zakera.

Supports Gemini 1.5 Pro, Gemini 1.5 Flash, Gemini 1.0 Pro, and
Gemini 2.0 Flash Experimental via the Vertex AI REST API.

Authentication uses a Google service-account JSON key (set via the
``GOOGLE_VERTEX_SA_KEY_JSON`` environment variable).  The provider
exchanges the key for a short-lived OAuth 2 access token and refreshes
it automatically before expiry.

Interface contract
------------------
Implements the same ``generate()`` / ``stream_generate()`` / ``health_check()``
interface used by all other providers in the codebase (Groq, OpenAI, etc.).
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx
from pydantic import BaseModel, Field

from .providers import ModelProvider as BaseProvider, ModelResponse  # type: ignore[import]

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VERTEX_AI_BASE = "https://{location}-aiplatform.googleapis.com/v1"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
DEFAULT_LOCATION = "us-central1"
DEFAULT_MODEL = "gemini-1.5-pro-002"
TOKEN_REFRESH_BUFFER_SECONDS = 60  # refresh token 60 s before actual expiry

# ---------------------------------------------------------------------------
# Supported model catalogue
# ---------------------------------------------------------------------------

MODEL_SPECS: Dict[str, Dict[str, Any]] = {
    "gemini-1.5-pro-002": {
        "context_length": 1_000_000,
        "supports_system_instruction": True,
        "supports_vision": True,
        "best_for": "complex reasoning, long context, multimodal",
    },
    "gemini-1.5-flash-002": {
        "context_length": 1_000_000,
        "supports_system_instruction": True,
        "supports_vision": True,
        "best_for": "fast inference, cost-effective, long context",
    },
    "gemini-1.0-pro": {
        "context_length": 32_768,
        "supports_system_instruction": False,
        "supports_vision": False,
        "best_for": "general-purpose text generation",
    },
    "gemini-2.0-flash-exp": {
        "context_length": 1_000_000,
        "supports_system_instruction": True,
        "supports_vision": True,
        "best_for": "experimental next-gen capabilities, multimodal",
    },
}

DEFAULT_SAFETY_SETTINGS = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]


# ---------------------------------------------------------------------------
# Configuration model
# ---------------------------------------------------------------------------


class VertexConfig(BaseModel):
    """Configuration for the Vertex AI provider."""

    project_id: str = Field(..., description="GCP project ID")
    location: str = Field(default=DEFAULT_LOCATION, description="GCP region")
    sa_key_json: str = Field(
        ..., description="Service-account JSON key as a string (from env var)"
    )
    default_model: str = Field(
        default=DEFAULT_MODEL, description="Default Gemini model"
    )
    timeout: int = Field(default=120, description="HTTP timeout in seconds")
    max_retries: int = Field(default=3, description="Max retry attempts")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_output_tokens: int = Field(default=8192, gt=0)
    top_p: float = Field(default=0.95, ge=0.0, le=1.0)
    top_k: int = Field(default=40, ge=1)


# ---------------------------------------------------------------------------
# OAuth 2 token cache
# ---------------------------------------------------------------------------


@dataclass
class _AccessToken:
    token: str
    expires_at: float  # Unix timestamp

    def is_valid(self) -> bool:
        return time.monotonic() < self.expires_at - TOKEN_REFRESH_BUFFER_SECONDS


# ---------------------------------------------------------------------------
# Provider implementation
# ---------------------------------------------------------------------------


class VertexAIProvider(BaseProvider):
    """
    Google Vertex AI Generative Language provider.

    Usage::

        config = VertexConfig(
            project_id="my-project",
            sa_key_json=os.environ["GOOGLE_VERTEX_SA_KEY_JSON"],
        )
        provider = VertexAIProvider(config)

        # Non-streaming
        response = await provider.generate(messages)

        # Streaming
        async for chunk in provider.stream_generate(messages):
            print(chunk, end="", flush=True)
    """

    PROVIDER_NAME = "vertex"

    def __init__(self, config: VertexConfig) -> None:
        self.config = config
        self._token_cache: Optional[_AccessToken] = None
        self._sa_key: Dict[str, Any] = json.loads(config.sa_key_json)
        self._client: Optional[httpx.AsyncClient] = None
        logger.info(
            "Initialized VertexAIProvider: project=%s location=%s model=%s",
            config.project_id,
            config.location,
            config.default_model,
        )

    # ------------------------------------------------------------------
    # HTTP client lifecycle
    # ------------------------------------------------------------------

    def _base_url(self) -> str:
        return VERTEX_AI_BASE.format(location=self.config.location)

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self._base_url(),
                timeout=httpx.Timeout(self.config.timeout),
            )
        return self._client

    async def close(self) -> None:
        """Cleanly shut down the underlying HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "VertexAIProvider":
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()

    # ------------------------------------------------------------------
    # OAuth 2 token management
    # ------------------------------------------------------------------

    async def _get_access_token(self) -> str:
        """Return a valid access token, refreshing if necessary."""
        if self._token_cache and self._token_cache.is_valid():
            return self._token_cache.token

        token, expires_in = await self._fetch_access_token()
        self._token_cache = _AccessToken(
            token=token,
            expires_at=time.monotonic() + expires_in,
        )
        return token

    async def _fetch_access_token(self) -> tuple[str, float]:
        """
        Exchange service-account key for an OAuth 2 access token using
        the JWT bearer-token flow.
        """
        import base64
        import json as _json

        # Build a signed JWT (RS256) for the service-account
        # In production you would use google-auth; here we replicate the
        # minimal flow so that the file has no extra dependencies.
        try:
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import padding
            from cryptography.hazmat.backends import default_backend

            private_key_pem = self._sa_key["private_key"].encode()
            private_key = serialization.load_pem_private_key(
                private_key_pem, password=None, backend=default_backend()
            )

            now = int(time.time())
            header = base64.urlsafe_b64encode(
                _json.dumps({"alg": "RS256", "typ": "JWT"}).encode()
            ).rstrip(b"=").decode()

            payload_data = {
                "iss": self._sa_key["client_email"],
                "sub": self._sa_key["client_email"],
                "aud": TOKEN_ENDPOINT,
                "iat": now,
                "exp": now + 3600,
                "scope": "https://www.googleapis.com/auth/cloud-platform",
            }
            payload_b64 = base64.urlsafe_b64encode(
                _json.dumps(payload_data).encode()
            ).rstrip(b"=").decode()

            signing_input = f"{header}.{payload_b64}".encode()
            signature = private_key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
            sig_b64 = base64.urlsafe_b64encode(signature).rstrip(b"=").decode()

            jwt_token = f"{header}.{payload_b64}.{sig_b64}"

            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    TOKEN_ENDPOINT,
                    data={
                        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                        "assertion": jwt_token,
                    },
                )
                resp.raise_for_status()
                token_data = resp.json()
                return token_data["access_token"], float(token_data.get("expires_in", 3600))

        except ImportError:
            # If cryptography is unavailable fall back to Application Default Credentials
            logger.warning(
                "cryptography package not found; falling back to ADC for Vertex AI auth."
            )
            import google.auth  # type: ignore[import]
            import google.auth.transport.requests  # type: ignore[import]

            creds, _ = google.auth.default(
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
            auth_req = google.auth.transport.requests.Request()
            creds.refresh(auth_req)
            return creds.token, 3600.0

    # ------------------------------------------------------------------
    # Message conversion helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _convert_messages(
        messages: List[Dict[str, str]],
    ) -> tuple[Optional[str], List[Dict[str, Any]]]:
        """
        Split messages into (system_instruction, vertex_contents).

        Vertex AI expects:
          - A top-level ``systemInstruction`` field for system prompts
          - A ``contents`` list of {"role": "user"|"model", "parts": [...]}
        """
        system_instruction: Optional[str] = None
        contents: List[Dict[str, Any]] = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                system_instruction = content
                continue

            vertex_role = "model" if role == "assistant" else "user"
            contents.append({"role": vertex_role, "parts": [{"text": content}]})

        return system_instruction, contents

    # ------------------------------------------------------------------
    # Request builder
    # ------------------------------------------------------------------

    def _build_payload(
        self,
        messages: List[Dict[str, str]],
        *,
        stream: bool = False,
        safety_settings: Optional[List[Dict[str, str]]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        system_instruction, contents = self._convert_messages(messages)
        model_spec = MODEL_SPECS.get(self.config.default_model, {})

        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": kwargs.get("temperature", self.config.temperature),
                "topP": kwargs.get("top_p", self.config.top_p),
                "topK": kwargs.get("top_k", self.config.top_k),
                "maxOutputTokens": kwargs.get(
                    "max_output_tokens", self.config.max_output_tokens
                ),
            },
            "safetySettings": safety_settings or DEFAULT_SAFETY_SETTINGS,
        }

        if system_instruction and model_spec.get("supports_system_instruction", False):
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        return payload

    def _endpoint(self, model: str, *, stream: bool = False) -> str:
        action = "streamGenerateContent" if stream else "generateContent"
        project = self.config.project_id
        location = self.config.location
        return (
            f"/projects/{project}/locations/{location}"
            f"/publishers/google/models/{model}:{action}"
        )

    # ------------------------------------------------------------------
    # Retry helper
    # ------------------------------------------------------------------

    @staticmethod
    def _is_retryable(status_code: int) -> bool:
        return status_code in (429, 500, 502, 503, 504)

    async def _post_with_retry(
        self, endpoint: str, payload: Dict[str, Any]
    ) -> httpx.Response:
        client = await self._get_client()
        last_exc: Optional[Exception] = None

        for attempt in range(self.config.max_retries + 1):
            token = await self._get_access_token()
            headers = {"Authorization": f"Bearer {token}"}
            try:
                resp = await client.post(endpoint, json=payload, headers=headers)
                if resp.status_code == 200 or not self._is_retryable(resp.status_code):
                    return resp
                wait = 2.0 ** attempt
                logger.warning(
                    "VertexAI request failed (status=%s), retrying in %.1fs (attempt %d/%d)",
                    resp.status_code,
                    wait,
                    attempt + 1,
                    self.config.max_retries,
                )
                await asyncio.sleep(wait)
                last_exc = RuntimeError(f"HTTP {resp.status_code}: {resp.text[:200]}")
            except httpx.RequestError as exc:
                wait = 2.0 ** attempt
                logger.warning("VertexAI network error: %s, retrying in %.1fs", exc, wait)
                await asyncio.sleep(wait)
                last_exc = exc

        raise RuntimeError(
            f"VertexAI request failed after {self.config.max_retries} retries"
        ) from last_exc

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def generate(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        stream: bool = False,
        **kwargs: Any,
    ) -> ModelResponse:
        """
        Send a chat completion request and return the full response.

        Args:
            messages: List of {"role": str, "content": str} dicts.
            model:    Override the default model for this request.
            stream:   If True delegates to :meth:`stream_generate`.
            **kwargs: Overrides for ``temperature``, ``top_p``, ``top_k``,
                      ``max_output_tokens``, ``safety_settings``.

        Returns:
            :class:`ModelResponse` with ``content``, ``model``,
            ``usage``, and ``finish_reason``.
        """
        if stream:
            # Collect the stream into a single response object
            parts: List[str] = []
            async for chunk in self.stream_generate(messages, model=model, **kwargs):
                parts.append(chunk)
            return ModelResponse(
                content="".join(parts),
                model=model or self.config.default_model,
                usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                finish_reason="stop",
            )

        effective_model = model or self.config.default_model
        payload = self._build_payload(messages, **kwargs)
        endpoint = self._endpoint(effective_model)

        resp = await self._post_with_retry(endpoint, payload)
        if resp.status_code != 200:
            raise RuntimeError(
                f"VertexAI API error {resp.status_code}: {resp.text[:400]}"
            )

        data = resp.json()
        candidate = data["candidates"][0]
        text = candidate["content"]["parts"][0].get("text", "")
        finish_reason = candidate.get("finishReason", "STOP").lower()

        usage_meta = data.get("usageMetadata", {})
        usage = {
            "prompt_tokens": usage_meta.get("promptTokenCount", 0),
            "completion_tokens": usage_meta.get("candidatesTokenCount", 0),
            "total_tokens": usage_meta.get("totalTokenCount", 0),
        }

        logger.info(
            "VertexAI generation OK – model=%s tokens=%d finish=%s",
            effective_model,
            usage["total_tokens"],
            finish_reason,
        )
        return ModelResponse(
            content=text,
            model=effective_model,
            usage=usage,
            finish_reason=finish_reason,
        )

    async def stream_generate(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """
        Yield text chunks as they arrive from the streaming Vertex AI API.

        Usage::

            async for token in provider.stream_generate(messages):
                print(token, end="", flush=True)
        """
        effective_model = model or self.config.default_model
        payload = self._build_payload(messages, stream=True, **kwargs)
        endpoint = self._endpoint(effective_model, stream=True) + "?alt=sse"

        token = await self._get_access_token()
        headers = {"Authorization": f"Bearer {token}"}
        client = await self._get_client()

        try:
            async with client.stream(
                "POST", endpoint, json=payload, headers=headers
            ) as resp:
                if resp.status_code != 200:
                    body = await resp.aread()
                    raise RuntimeError(
                        f"VertexAI stream error {resp.status_code}: {body.decode()[:200]}"
                    )

                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    raw = line[len("data: "):].strip()
                    if raw in ("[DONE]", ""):
                        break
                    try:
                        event = json.loads(raw)
                    except json.JSONDecodeError:
                        logger.debug("VertexAI: failed to parse SSE line: %s", raw)
                        continue

                    candidates = event.get("candidates", [])
                    if not candidates:
                        continue
                    parts_list = (
                        candidates[0].get("content", {}).get("parts", [])
                    )
                    for part in parts_list:
                        text = part.get("text", "")
                        if text:
                            yield text
        except Exception as exc:
            logger.error("VertexAI streaming failed: %s", exc)
            raise

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    async def health_check(self) -> Dict[str, Any]:
        """
        Probe the Vertex AI discovery endpoint to confirm connectivity
        and valid credentials.
        """
        try:
            token = await self._get_access_token()
            client = await self._get_client()
            endpoint = (
                f"/projects/{self.config.project_id}"
                f"/locations/{self.config.location}"
                f"/publishers/google/models"
            )
            resp = await client.get(
                endpoint,
                headers={"Authorization": f"Bearer {token}"},
            )
            if resp.status_code == 200:
                return {
                    "status": "healthy",
                    "provider": self.PROVIDER_NAME,
                    "project": self.config.project_id,
                    "location": self.config.location,
                    "default_model": self.config.default_model,
                }
            return {
                "status": "degraded",
                "http_status": resp.status_code,
                "provider": self.PROVIDER_NAME,
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "status": "unhealthy",
                "error": str(exc),
                "provider": self.PROVIDER_NAME,
            }

    # ------------------------------------------------------------------
    # Metadata helpers
    # ------------------------------------------------------------------

    @staticmethod
    def list_models() -> List[str]:
        """Return all supported model identifiers."""
        return list(MODEL_SPECS.keys())

    def get_model_info(self, model: str) -> Dict[str, Any]:
        """Return capability metadata for a given model."""
        return MODEL_SPECS.get(model, {})

    def recommend_model(self, priority: str = "balanced") -> str:
        """
        Suggest a model based on the desired trade-off.

        Args:
            priority: ``"quality"``, ``"speed"``, ``"long_context"``,
                      or ``"balanced"`` (default).
        """
        mapping = {
            "quality": "gemini-1.5-pro-002",
            "speed": "gemini-1.5-flash-002",
            "long_context": "gemini-1.5-pro-002",
            "balanced": "gemini-1.5-flash-002",
            "experimental": "gemini-2.0-flash-exp",
        }
        return mapping.get(priority, self.config.default_model)

    def __repr__(self) -> str:
        return (
            f"VertexAIProvider("
            f"project={self.config.project_id!r}, "
            f"model={self.config.default_model!r})"
        )


# ---------------------------------------------------------------------------
# Factory helper
# ---------------------------------------------------------------------------


def create_vertex_provider(settings: Dict[str, Any]) -> VertexAIProvider:
    """
    Convenience factory that builds a :class:`VertexAIProvider` from a
    settings dict.

    Expected keys:
      - ``vertex_project``      (required) – GCP project ID
      - ``vertex_sa_key_json``  (required) – service-account JSON string
      - ``vertex_location``     (optional, default ``us-central1``)
      - ``vertex_model``        (optional, default ``gemini-1.5-pro-002``)
      - ``vertex_temperature``  (optional, default ``0.7``)
      - ``vertex_max_tokens``   (optional, default ``8192``)
    """
    config = VertexConfig(
        project_id=settings["vertex_project"],
        sa_key_json=settings["vertex_sa_key_json"],
        location=settings.get("vertex_location", DEFAULT_LOCATION),
        default_model=settings.get("vertex_model", DEFAULT_MODEL),
        temperature=float(settings.get("vertex_temperature", 0.7)),
        max_output_tokens=int(settings.get("vertex_max_tokens", 8192)),
    )
    return VertexAIProvider(config)
