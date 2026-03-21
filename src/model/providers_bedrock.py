"""AWS Bedrock Provider - Managed foundation model inference.

AWS Bedrock gives access to a broad set of foundation models from Amazon,
Anthropic, Meta, Mistral, and others through a unified API, with enterprise
features like VPC endpoints, PrivateLink, CloudWatch logging, and IAM-based
access control.

Supported model families:
- Amazon Titan (Text Express, Text Premier, Text Lite)
- Anthropic Claude 3 (Haiku, Sonnet, Opus) & Claude 3.5 Sonnet
- Meta Llama 3 (8B, 70B Instruct)
- Mistral (7B Instruct, 8x7B Instruct)

Authentication:
  Uses boto3 credential chain: environment variables, ~/.aws/credentials,
  IAM instance profiles, or explicit key/secret in config.

Documentation:
  https://docs.aws.amazon.com/bedrock/latest/userguide/
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, AsyncIterator, Dict, List, Optional

from pydantic import BaseModel, Field

from .providers import BaseProvider, ModelResponse

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Model family detection helpers
# ---------------------------------------------------------------------------

_CLAUDE_PREFIXES = ("anthropic.claude",)
_LLAMA_PREFIXES = ("meta.llama",)
_MISTRAL_PREFIXES = ("mistral.",)
_TITAN_PREFIXES = ("amazon.titan-text",)


def _model_family(model_id: str) -> str:
    """Return the canonical model family for a Bedrock model ID."""
    mid = model_id.lower()
    if any(mid.startswith(p) for p in _CLAUDE_PREFIXES):
        return "claude"
    if any(mid.startswith(p) for p in _LLAMA_PREFIXES):
        return "llama"
    if any(mid.startswith(p) for p in _MISTRAL_PREFIXES):
        return "mistral"
    if any(mid.startswith(p) for p in _TITAN_PREFIXES):
        return "titan"
    return "unknown"


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


class BedrockConfig(BaseModel):
    """AWS Bedrock provider configuration."""

    region: str = Field(default="us-east-1", description="AWS region")
    aws_access_key_id: Optional[str] = Field(
        default=None, description="AWS access key (falls back to boto3 chain)"
    )
    aws_secret_access_key: Optional[str] = Field(
        default=None, description="AWS secret key"
    )
    aws_session_token: Optional[str] = Field(
        default=None, description="AWS session token for temporary credentials"
    )
    default_model: str = Field(
        default="anthropic.claude-3-haiku-20240307-v1:0",
        description="Default Bedrock model ID",
    )
    timeout: int = Field(default=120, description="Request timeout in seconds")
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    temperature: float = Field(default=0.7, ge=0.0, le=1.0)
    max_tokens: int = Field(default=4096, gt=0)
    top_p: float = Field(default=0.9, ge=0.0, le=1.0)


# ---------------------------------------------------------------------------
# Model registry
# ---------------------------------------------------------------------------

_MODEL_SPECS: Dict[str, Dict[str, Any]] = {
    # Anthropic Claude 3 family
    "anthropic.claude-3-haiku-20240307-v1:0": {
        "context_length": 200_000,
        "family": "claude",
        "speed": "fast",
        "quality": "good",
        "best_for": "fast responses, summarisation, Q&A",
        "input_cost_per_1k": 0.00025,
        "output_cost_per_1k": 0.00125,
    },
    "anthropic.claude-3-sonnet-20240229-v1:0": {
        "context_length": 200_000,
        "family": "claude",
        "speed": "medium",
        "quality": "high",
        "best_for": "balanced tasks, coding, analysis",
        "input_cost_per_1k": 0.003,
        "output_cost_per_1k": 0.015,
    },
    "anthropic.claude-3-opus-20240229-v1:0": {
        "context_length": 200_000,
        "family": "claude",
        "speed": "slow",
        "quality": "highest",
        "best_for": "complex reasoning, research, nuanced writing",
        "input_cost_per_1k": 0.015,
        "output_cost_per_1k": 0.075,
    },
    "anthropic.claude-3-5-sonnet-20240620-v1:0": {
        "context_length": 200_000,
        "family": "claude",
        "speed": "medium",
        "quality": "very_high",
        "best_for": "coding, agentic tasks, tool use",
        "input_cost_per_1k": 0.003,
        "output_cost_per_1k": 0.015,
    },
    # Amazon Titan
    "amazon.titan-text-express-v1": {
        "context_length": 8_000,
        "family": "titan",
        "speed": "fast",
        "quality": "moderate",
        "best_for": "simple tasks, AWS-native workloads",
        "input_cost_per_1k": 0.0002,
        "output_cost_per_1k": 0.0006,
    },
    "amazon.titan-text-premier-v1:0": {
        "context_length": 32_000,
        "family": "titan",
        "speed": "medium",
        "quality": "good",
        "best_for": "enterprise tasks, long-form generation",
        "input_cost_per_1k": 0.0005,
        "output_cost_per_1k": 0.0015,
    },
    # Meta Llama 3
    "meta.llama3-8b-instruct-v1:0": {
        "context_length": 8_000,
        "family": "llama",
        "speed": "very_fast",
        "quality": "good",
        "best_for": "low-latency chat, lightweight reasoning",
        "input_cost_per_1k": 0.0003,
        "output_cost_per_1k": 0.0006,
    },
    "meta.llama3-70b-instruct-v1:0": {
        "context_length": 8_000,
        "family": "llama",
        "speed": "medium",
        "quality": "high",
        "best_for": "complex reasoning, instruction following",
        "input_cost_per_1k": 0.00265,
        "output_cost_per_1k": 0.0035,
    },
    # Mistral
    "mistral.mistral-7b-instruct-v0:2": {
        "context_length": 32_000,
        "family": "mistral",
        "speed": "fast",
        "quality": "good",
        "best_for": "efficient generation, multilingual",
        "input_cost_per_1k": 0.00015,
        "output_cost_per_1k": 0.0002,
    },
    "mistral.mixtral-8x7b-instruct-v0:1": {
        "context_length": 32_000,
        "family": "mistral",
        "speed": "medium",
        "quality": "high",
        "best_for": "high-quality generation, code, analysis",
        "input_cost_per_1k": 0.00045,
        "output_cost_per_1k": 0.0007,
    },
}


# ---------------------------------------------------------------------------
# Payload builders per model family
# ---------------------------------------------------------------------------


def _build_claude_payload(
    messages: List[Dict[str, str]],
    temperature: float,
    max_tokens: int,
    top_p: float,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Build the request body for Anthropic Claude on Bedrock."""
    system_prompt = ""
    chat_messages: List[Dict[str, str]] = []

    for msg in messages:
        role = msg["role"]
        content = msg["content"]
        if role == "system":
            system_prompt = content
        else:
            chat_messages.append({"role": role, "content": content})

    payload: Dict[str, Any] = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "messages": chat_messages,
        "temperature": temperature,
        "top_p": top_p,
    }
    if system_prompt:
        payload["system"] = system_prompt
    if "stop_sequences" in kwargs:
        payload["stop_sequences"] = kwargs["stop_sequences"]
    return payload


def _build_llama_payload(
    messages: List[Dict[str, str]],
    temperature: float,
    max_tokens: int,
    top_p: float,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Build the request body for Meta Llama 3 on Bedrock (prompt-based API)."""
    # Llama 3 uses a special chat template
    prompt_parts: List[str] = ["<|begin_of_text|>"]
    for msg in messages:
        role = msg["role"]
        content = msg["content"]
        prompt_parts.append(
            f"<|start_header_id|>{role}<|end_header_id|>\n\n{content}<|eot_id|>"
        )
    prompt_parts.append("<|start_header_id|>assistant<|end_header_id|>\n\n")
    prompt = "".join(prompt_parts)

    return {
        "prompt": prompt,
        "max_gen_len": max_tokens,
        "temperature": temperature,
        "top_p": top_p,
    }


def _build_mistral_payload(
    messages: List[Dict[str, str]],
    temperature: float,
    max_tokens: int,
    top_p: float,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Build the request body for Mistral models on Bedrock."""
    # Mistral uses OpenAI-style messages
    return {
        "messages": [{"role": m["role"], "content": m["content"]} for m in messages],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "top_p": top_p,
    }


def _build_titan_payload(
    messages: List[Dict[str, str]],
    temperature: float,
    max_tokens: int,
    top_p: float,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Build the request body for Amazon Titan Text models."""
    # Titan uses a single inputText with a turn-based format
    turns: List[str] = []
    for msg in messages:
        role = msg["role"].capitalize()
        turns.append(f"{role}: {msg['content']}")
    turns.append("Bot:")
    input_text = "\n".join(turns)

    return {
        "inputText": input_text,
        "textGenerationConfig": {
            "maxTokenCount": max_tokens,
            "temperature": temperature,
            "topP": top_p,
        },
    }


# ---------------------------------------------------------------------------
# Response parsers per model family
# ---------------------------------------------------------------------------


def _parse_claude_response(body: Dict[str, Any], model: str) -> ModelResponse:
    content_block = body.get("content", [{}])[0]
    text = content_block.get("text", "")
    usage = body.get("usage", {})
    return ModelResponse(
        text=text,
        provider="bedrock",
        model=model,
        finish_reason=body.get("stop_reason"),
        usage={
            "prompt_tokens": usage.get("input_tokens", 0),
            "completion_tokens": usage.get("output_tokens", 0),
            "total_tokens": usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
        },
        metadata={"model_family": "claude", "bedrock_id": body.get("id")},
    )


def _parse_llama_response(body: Dict[str, Any], model: str) -> ModelResponse:
    text = body.get("generation", "")
    return ModelResponse(
        text=text,
        provider="bedrock",
        model=model,
        finish_reason=body.get("stop_reason"),
        usage={
            "prompt_tokens": body.get("prompt_token_count", 0),
            "completion_tokens": body.get("generation_token_count", 0),
            "total_tokens": (
                body.get("prompt_token_count", 0)
                + body.get("generation_token_count", 0)
            ),
        },
        metadata={"model_family": "llama"},
    )


def _parse_mistral_response(body: Dict[str, Any], model: str) -> ModelResponse:
    choice = (body.get("outputs") or body.get("choices") or [{}])[0]
    # Mistral Bedrock returns outputs[].text or choices[].message.content
    text = choice.get("text") or (choice.get("message") or {}).get("content", "")
    return ModelResponse(
        text=text,
        provider="bedrock",
        model=model,
        finish_reason=choice.get("stop_reason") or choice.get("finish_reason"),
        usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        metadata={"model_family": "mistral"},
    )


def _parse_titan_response(body: Dict[str, Any], model: str) -> ModelResponse:
    results = body.get("results", [{}])
    text = results[0].get("outputText", "") if results else ""
    return ModelResponse(
        text=text,
        provider="bedrock",
        model=model,
        finish_reason=results[0].get("completionReason") if results else None,
        usage={
            "prompt_tokens": body.get("inputTextTokenCount", 0),
            "completion_tokens": results[0].get("tokenCount", 0) if results else 0,
            "total_tokens": body.get("inputTextTokenCount", 0)
            + (results[0].get("tokenCount", 0) if results else 0),
        },
        metadata={"model_family": "titan"},
    )


# ---------------------------------------------------------------------------
# Provider implementation
# ---------------------------------------------------------------------------


class BedrockProvider(BaseProvider):
    """AWS Bedrock managed-model provider.

    Features:
    - Multi-family model support (Claude, Llama, Mistral, Titan)
    - Streaming via Bedrock Runtime InvokeModelWithResponseStream
    - Automatic retry with exponential backoff on throttling
    - Per-model pricing and metadata registry
    - Health check via ListFoundationModels
    - Full async interface using asyncio thread pool for boto3 calls
    """

    def __init__(self, config: BedrockConfig) -> None:
        """Initialise the Bedrock provider.

        Args:
            config: Bedrock configuration including region and credentials.
        """
        self.config = config
        self._client: Any = None  # lazy-init boto3 client
        logger.info(
            "Initialised Bedrock provider | region=%s default_model=%s",
            config.region,
            config.default_model,
        )

    # ------------------------------------------------------------------
    # Boto3 client (lazy, thread-safe via asyncio loop executor)
    # ------------------------------------------------------------------

    def _get_client(self) -> Any:
        """Return a boto3 bedrock-runtime client, creating it if necessary."""
        if self._client is None:
            try:
                import boto3  # type: ignore
            except ImportError as exc:
                raise ImportError(
                    "boto3 is required for the Bedrock provider. "
                    "Install it with: pip install boto3"
                ) from exc

            session_kwargs: Dict[str, Any] = {"region_name": self.config.region}
            if self.config.aws_access_key_id:
                session_kwargs["aws_access_key_id"] = self.config.aws_access_key_id
                session_kwargs["aws_secret_access_key"] = (
                    self.config.aws_secret_access_key
                )
            if self.config.aws_session_token:
                session_kwargs["aws_session_token"] = self.config.aws_session_token

            session = boto3.Session(**session_kwargs)
            self._client = session.client(
                "bedrock-runtime",
                config=__import__("botocore").config.Config(
                    connect_timeout=self.config.timeout,
                    read_timeout=self.config.timeout,
                    retries={"max_attempts": 1},  # we handle retries ourselves
                ),
            )
        return self._client

    # ------------------------------------------------------------------
    # Payload / response dispatch
    # ------------------------------------------------------------------

    def _build_payload(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
        top_p: float,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        family = _model_family(model)
        builders = {
            "claude": _build_claude_payload,
            "llama": _build_llama_payload,
            "mistral": _build_mistral_payload,
            "titan": _build_titan_payload,
        }
        builder = builders.get(family)
        if builder is None:
            raise ValueError(
                f"Unsupported Bedrock model family for model '{model}'. "
                f"Supported families: {list(builders)}"
            )
        return builder(messages, temperature, max_tokens, top_p, **kwargs)

    def _parse_response(self, body: Dict[str, Any], model: str) -> ModelResponse:
        family = _model_family(model)
        parsers = {
            "claude": _parse_claude_response,
            "llama": _parse_llama_response,
            "mistral": _parse_mistral_response,
            "titan": _parse_titan_response,
        }
        parser = parsers.get(family)
        if parser is None:
            raise ValueError(f"No response parser for model family: {family}")
        return parser(body, model)

    # ------------------------------------------------------------------
    # Core generate (sync + async wrappers)
    # ------------------------------------------------------------------

    def _invoke_sync(self, model: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronous Bedrock InvokeModel call (runs in executor)."""
        client = self._get_client()
        response = client.invoke_model(
            modelId=model,
            body=json.dumps(payload),
            contentType="application/json",
            accept="application/json",
        )
        return json.loads(response["body"].read())

    async def generate(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        stream: bool = False,
        **kwargs: Any,
    ) -> ModelResponse:
        """Generate a completion using AWS Bedrock.

        Args:
            messages: Conversation messages [{role, content}, ...].
            model: Bedrock model ID (overrides config default).
            stream: If True, delegates to streaming endpoint.
            **kwargs: temperature, max_tokens, top_p, stop_sequences, etc.

        Returns:
            ModelResponse with text and usage metadata.

        Raises:
            Exception: After max_retries exhausted.
        """
        model = model or self.config.default_model
        temperature = float(kwargs.get("temperature", self.config.temperature))
        max_tokens = int(kwargs.get("max_tokens", self.config.max_tokens))
        top_p = float(kwargs.get("top_p", self.config.top_p))

        if stream:
            # Callers should use generate_stream() directly; here we fall back
            # to non-streaming for simplicity when stream=True is passed.
            logger.debug("stream=True passed to generate(); using non-streaming path")

        payload = self._build_payload(
            messages, model, temperature, max_tokens, top_p, **kwargs
        )

        last_error: Optional[Exception] = None
        for attempt in range(self.config.max_retries):
            try:
                loop = asyncio.get_event_loop()
                body = await loop.run_in_executor(
                    None, self._invoke_sync, model, payload
                )
                response = self._parse_response(body, model)
                logger.info(
                    "Bedrock generation OK | model=%s tokens=%s",
                    model,
                    response.usage.get("total_tokens", "?"),
                )
                return response

            except Exception as exc:  # noqa: BLE001
                last_error = exc
                exc_name = type(exc).__name__
                should_retry = any(
                    kw in exc_name
                    for kw in ("Throttling", "ServiceUnavailable", "RequestTimeout")
                )
                if should_retry and attempt < self.config.max_retries - 1:
                    wait = 2**attempt
                    logger.warning(
                        "Bedrock throttled/unavailable, retrying in %ss (attempt %s/%s)",
                        wait,
                        attempt + 1,
                        self.config.max_retries,
                    )
                    await asyncio.sleep(wait)
                else:
                    logger.error(
                        "Bedrock call failed (attempt %s): %s", attempt + 1, exc
                    )
                    if not should_retry:
                        break

        raise Exception(
            f"Bedrock generation failed after {self.config.max_retries} attempts: {last_error}"
        )

    # ------------------------------------------------------------------
    # Streaming generate
    # ------------------------------------------------------------------

    def _invoke_stream_sync(
        self, model: str, payload: Dict[str, Any]
    ) -> Any:
        """Synchronous InvokeModelWithResponseStream call (runs in executor)."""
        client = self._get_client()
        return client.invoke_model_with_response_stream(
            modelId=model,
            body=json.dumps(payload),
            contentType="application/json",
            accept="application/json",
        )

    async def generate_stream(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Stream tokens from AWS Bedrock.

        Yields individual text chunks as they arrive from the model.
        Currently supports Claude streaming; other families fall back to
        full-response chunking.

        Args:
            messages: Conversation messages.
            model: Bedrock model ID.
            **kwargs: Generation parameters.

        Yields:
            Text string chunks.
        """
        model = model or self.config.default_model
        temperature = float(kwargs.get("temperature", self.config.temperature))
        max_tokens = int(kwargs.get("max_tokens", self.config.max_tokens))
        top_p = float(kwargs.get("top_p", self.config.top_p))

        payload = self._build_payload(
            messages, model, temperature, max_tokens, top_p, **kwargs
        )
        family = _model_family(model)

        loop = asyncio.get_event_loop()
        try:
            raw = await loop.run_in_executor(
                None, self._invoke_stream_sync, model, payload
            )
        except Exception as exc:
            logger.error("Bedrock streaming initiation failed: %s", exc)
            raise

        stream = raw.get("body")
        if stream is None:
            logger.warning("Bedrock stream body is None; yielding empty")
            return

        for event in stream:
            chunk = event.get("chunk")
            if chunk is None:
                continue
            chunk_data = json.loads(chunk["bytes"])

            if family == "claude":
                # Claude streaming events: content_block_delta
                if chunk_data.get("type") == "content_block_delta":
                    delta = chunk_data.get("delta", {})
                    text = delta.get("text", "")
                    if text:
                        yield text
            elif family == "llama":
                text = chunk_data.get("generation", "")
                if text:
                    yield text
            elif family == "mistral":
                outputs = chunk_data.get("outputs", [])
                for out in outputs:
                    text = out.get("text", "")
                    if text:
                        yield text
            elif family == "titan":
                text = chunk_data.get("outputText", "")
                if text:
                    yield text

    # ------------------------------------------------------------------
    # Health & metadata
    # ------------------------------------------------------------------

    async def health_check(self) -> Dict[str, Any]:
        """Check Bedrock API reachability by listing foundation models.

        Returns:
            Dict with status, region, and available model count.
        """
        try:
            import boto3  # noqa: F401  (ensure importable)

            def _list_models() -> List[str]:
                session_kwargs: Dict[str, Any] = {"region_name": self.config.region}
                if self.config.aws_access_key_id:
                    session_kwargs["aws_access_key_id"] = self.config.aws_access_key_id
                    session_kwargs["aws_secret_access_key"] = (
                        self.config.aws_secret_access_key
                    )
                import boto3  # noqa: F811

                session = boto3.Session(**session_kwargs)
                bedrock_client = session.client("bedrock", region_name=self.config.region)
                resp = bedrock_client.list_foundation_models(
                    byOutputModality="TEXT"
                )
                return [
                    m["modelId"]
                    for m in resp.get("modelSummaries", [])
                ]

            loop = asyncio.get_event_loop()
            models = await loop.run_in_executor(None, _list_models)

            return {
                "status": "healthy",
                "provider": "bedrock",
                "region": self.config.region,
                "available_models_count": len(models),
                "default_model": self.config.default_model,
            }
        except Exception as exc:
            logger.error("Bedrock health check failed: %s", exc)
            return {
                "status": "unhealthy",
                "provider": "bedrock",
                "region": self.config.region,
                "error": str(exc),
            }

    async def get_available_models(self) -> List[str]:
        """Return the list of model IDs in the local registry."""
        return list(_MODEL_SPECS.keys())

    def get_model_info(self, model: str) -> Dict[str, Any]:
        """Return metadata for a registered model.

        Args:
            model: Bedrock model ID.

        Returns:
            Dict with context_length, cost, speed, etc., or empty dict.
        """
        return _MODEL_SPECS.get(model, {})

    def recommend_model(self, priority: str = "balanced") -> str:
        """Return a recommended model ID based on priority.

        Args:
            priority: One of 'speed', 'quality', 'cost', or 'balanced'.

        Returns:
            Bedrock model ID string.
        """
        table = {
            "speed": "anthropic.claude-3-haiku-20240307-v1:0",
            "quality": "anthropic.claude-3-5-sonnet-20240620-v1:0",
            "cost": "amazon.titan-text-express-v1",
            "balanced": "anthropic.claude-3-sonnet-20240229-v1:0",
        }
        return table.get(priority, self.config.default_model)

    async def close(self) -> None:
        """Close the underlying boto3 client (no-op; boto3 manages sessions)."""
        self._client = None
        logger.info("Bedrock provider client released")
