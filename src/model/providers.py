from abc import ABC, abstractmethod
from typing import List, Dict, Optional, AsyncIterator, Tuple
from dataclasses import dataclass
import os


@dataclass
class Message:
    role: str
    content: str
    name: Optional[str] = None


@dataclass
class ModelResponse:
    content: str
    model: str
    usage: Dict[str, int]
    finish_reason: str


class ModelProvider(ABC):
    """Abstract base class for AI model providers"""

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = api_key
        self.model_name = model_name

    @abstractmethod
    async def generate(self, messages: List[Message], **kwargs) -> ModelResponse:
        """Generate a response from the model"""
        pass

    @abstractmethod
    async def stream_generate(self, messages: List[Message], **kwargs) -> AsyncIterator[str]:
        """Stream a response from the model"""
        pass


class OpenAIProvider(ModelProvider):
    """OpenAI API provider using the official openai Python SDK."""

    def __init__(self, api_key: Optional[str] = None, model_name: str = "gpt-4-turbo-preview"):
        super().__init__(api_key or os.getenv("OPENAI_API_KEY"), model_name)
        self.base_url = "https://api.openai.com/v1"

    def _get_client(self):
        """Lazily create an async OpenAI client."""
        try:
            from openai import AsyncOpenAI, AuthenticationError, RateLimitError, APIConnectionError
        except ImportError as exc:
            raise ImportError(
                "openai package is required. Install it with: pip install openai"
            ) from exc

        if not self.api_key:
            raise ValueError(
                "OpenAI API key is required. Set the OPENAI_API_KEY environment variable "
                "or pass api_key= to OpenAIProvider."
            )
        return AsyncOpenAI(api_key=self.api_key)

    @staticmethod
    def _messages_to_dicts(messages: List[Message]) -> List[Dict]:
        """Convert internal Message objects to OpenAI chat format."""
        result = []
        for msg in messages:
            entry: Dict = {"role": msg.role, "content": msg.content}
            if msg.name:
                entry["name"] = msg.name
            result.append(entry)
        return result

    async def generate(self, messages: List[Message], **kwargs) -> ModelResponse:
        """
        Generate a chat completion using the OpenAI API.

        Supported kwargs:
            temperature (float): Sampling temperature, 0–2. Default 0.7.
            max_tokens (int):    Maximum tokens to generate. Default 2048.
            top_p (float):       Nucleus sampling. Default 1.0.
            presence_penalty (float):  Default 0.0.
            frequency_penalty (float): Default 0.0.
            stop (list[str]):    Stop sequences.
        """
        try:
            from openai import AuthenticationError, RateLimitError, APIConnectionError
        except ImportError as exc:
            raise ImportError("openai package is required") from exc

        client = self._get_client()
        params = {
            "model": self.model_name,
            "messages": self._messages_to_dicts(messages),
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 2048),
            "top_p": kwargs.get("top_p", 1.0),
            "presence_penalty": kwargs.get("presence_penalty", 0.0),
            "frequency_penalty": kwargs.get("frequency_penalty", 0.0),
        }
        if "stop" in kwargs:
            params["stop"] = kwargs["stop"]

        try:
            response = await client.chat.completions.create(**params)
        except AuthenticationError as exc:
            raise ValueError(f"OpenAI authentication failed: {exc}") from exc
        except RateLimitError as exc:
            raise RuntimeError(f"OpenAI rate limit exceeded: {exc}") from exc
        except APIConnectionError as exc:
            raise RuntimeError(f"Could not connect to OpenAI API: {exc}") from exc

        choice = response.choices[0]
        usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        }
        return ModelResponse(
            content=choice.message.content or "",
            model=response.model,
            usage=usage,
            finish_reason=choice.finish_reason or "stop",
        )

    async def stream_generate(self, messages: List[Message], **kwargs) -> AsyncIterator[str]:
        """
        Stream a chat completion using the OpenAI API.

        Yields text delta chunks as they arrive from the SSE stream.
        Supported kwargs are the same as generate().
        """
        try:
            from openai import AuthenticationError, RateLimitError, APIConnectionError
        except ImportError as exc:
            raise ImportError("openai package is required") from exc

        client = self._get_client()
        params = {
            "model": self.model_name,
            "messages": self._messages_to_dicts(messages),
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 2048),
            "top_p": kwargs.get("top_p", 1.0),
            "presence_penalty": kwargs.get("presence_penalty", 0.0),
            "frequency_penalty": kwargs.get("frequency_penalty", 0.0),
            "stream": True,
        }
        if "stop" in kwargs:
            params["stop"] = kwargs["stop"]

        try:
            async with await client.chat.completions.create(**params) as stream:
                async for chunk in stream:
                    delta = chunk.choices[0].delta if chunk.choices else None
                    if delta and delta.content:
                        yield delta.content
        except AuthenticationError as exc:
            raise ValueError(f"OpenAI authentication failed: {exc}") from exc
        except RateLimitError as exc:
            raise RuntimeError(f"OpenAI rate limit exceeded: {exc}") from exc
        except APIConnectionError as exc:
            raise RuntimeError(f"Could not connect to OpenAI API: {exc}") from exc


class AnthropicProvider(ModelProvider):
    """Anthropic Claude API provider using the official anthropic Python SDK."""

    # Models that support the extended context window
    EXTENDED_CONTEXT_MODELS = {
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229",
        "claude-3-haiku-20240307",
        "claude-3-5-sonnet-20241022",
        "claude-3-5-haiku-20241022",
    }

    def __init__(self, api_key: Optional[str] = None, model_name: str = "claude-3-sonnet-20240229"):
        super().__init__(api_key or os.getenv("ANTHROPIC_API_KEY"), model_name)
        self.base_url = "https://api.anthropic.com/v1"

    def _get_client(self):
        """Lazily create an async Anthropic client."""
        try:
            from anthropic import AsyncAnthropic
        except ImportError as exc:
            raise ImportError(
                "anthropic package is required. Install it with: pip install anthropic"
            ) from exc

        if not self.api_key:
            raise ValueError(
                "Anthropic API key is required. Set the ANTHROPIC_API_KEY environment variable "
                "or pass api_key= to AnthropicProvider."
            )
        return AsyncAnthropic(api_key=self.api_key)

    @staticmethod
    def _extract_system_prompt(messages: List[Message]) -> Tuple[Optional[str], List[Message]]:
        """
        Anthropic's messages endpoint requires the system prompt as a top-level
        parameter rather than inside the messages list. This helper strips any
        leading system message and returns it separately.
        """
        if messages and messages[0].role == "system":
            return messages[0].content, messages[1:]
        return None, messages

    @staticmethod
    def _messages_to_dicts(messages: List[Message]) -> List[Dict]:
        """Convert internal Message objects to Anthropic messages format."""
        # Anthropic only accepts 'user' and 'assistant' roles.
        return [
            {"role": msg.role, "content": msg.content}
            for msg in messages
            if msg.role in ("user", "assistant")
        ]

    @staticmethod
    def _normalise_finish_reason(stop_reason: Optional[str]) -> str:
        mapping = {
            "end_turn": "stop",
            "max_tokens": "length",
            "stop_sequence": "stop",
            "tool_use": "tool_calls",
        }
        return mapping.get(stop_reason or "end_turn", stop_reason or "stop")

    async def generate(self, messages: List[Message], **kwargs) -> ModelResponse:
        """
        Generate a response using the Anthropic messages API.

        Supported kwargs:
            temperature (float): Default 1.0 (Anthropic's recommended default).
            max_tokens (int):    Default 2048.
            top_p (float):       Default 1.0.
            top_k (int):         Top-k sampling. Default not set.
            stop_sequences (list[str]): Custom stop sequences.
        """
        try:
            from anthropic import AuthenticationError, RateLimitError, APIConnectionError
        except ImportError as exc:
            raise ImportError("anthropic package is required") from exc

        client = self._get_client()
        system_prompt, conversation = self._extract_system_prompt(messages)

        create_kwargs: Dict = {
            "model": self.model_name,
            "max_tokens": kwargs.get("max_tokens", 2048),
            "messages": self._messages_to_dicts(conversation),
            "temperature": kwargs.get("temperature", 1.0),
        }
        if system_prompt:
            create_kwargs["system"] = system_prompt
        if "top_p" in kwargs:
            create_kwargs["top_p"] = kwargs["top_p"]
        if "top_k" in kwargs:
            create_kwargs["top_k"] = kwargs["top_k"]
        if "stop_sequences" in kwargs:
            create_kwargs["stop_sequences"] = kwargs["stop_sequences"]

        try:
            response = await client.messages.create(**create_kwargs)
        except AuthenticationError as exc:
            raise ValueError(f"Anthropic authentication failed: {exc}") from exc
        except RateLimitError as exc:
            raise RuntimeError(f"Anthropic rate limit exceeded: {exc}") from exc
        except APIConnectionError as exc:
            raise RuntimeError(f"Could not connect to Anthropic API: {exc}") from exc

        # Extract text content (may be list of content blocks)
        text_content = ""
        for block in response.content:
            if hasattr(block, "text"):
                text_content += block.text

        usage = {
            "prompt_tokens": response.usage.input_tokens,
            "completion_tokens": response.usage.output_tokens,
            "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
        }
        return ModelResponse(
            content=text_content,
            model=response.model,
            usage=usage,
            finish_reason=self._normalise_finish_reason(response.stop_reason),
        )

    async def stream_generate(self, messages: List[Message], **kwargs) -> AsyncIterator[str]:
        """
        Stream a response using the Anthropic streaming messages API.

        Yields text delta chunks as they arrive. Supported kwargs are the
        same as generate().
        """
        try:
            from anthropic import AuthenticationError, RateLimitError, APIConnectionError
        except ImportError as exc:
            raise ImportError("anthropic package is required") from exc

        client = self._get_client()
        system_prompt, conversation = self._extract_system_prompt(messages)

        create_kwargs: Dict = {
            "model": self.model_name,
            "max_tokens": kwargs.get("max_tokens", 2048),
            "messages": self._messages_to_dicts(conversation),
            "temperature": kwargs.get("temperature", 1.0),
        }
        if system_prompt:
            create_kwargs["system"] = system_prompt
        if "top_p" in kwargs:
            create_kwargs["top_p"] = kwargs["top_p"]
        if "top_k" in kwargs:
            create_kwargs["top_k"] = kwargs["top_k"]
        if "stop_sequences" in kwargs:
            create_kwargs["stop_sequences"] = kwargs["stop_sequences"]

        try:
            async with client.messages.stream(**create_kwargs) as stream:
                async for text in stream.text_stream:
                    yield text
        except AuthenticationError as exc:
            raise ValueError(f"Anthropic authentication failed: {exc}") from exc
        except RateLimitError as exc:
            raise RuntimeError(f"Anthropic rate limit exceeded: {exc}") from exc
        except APIConnectionError as exc:
            raise RuntimeError(f"Could not connect to Anthropic API: {exc}") from exc


class GeminiProvider(ModelProvider):
    """
    Google Gemini API provider

    Supports Gemini Pro and Gemini Pro Vision models with full streaming capabilities.
    Integrates with Google's generative AI API for high-quality responses.
    """

    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-pro"):
        super().__init__(api_key or os.getenv("GOOGLE_API_KEY"), model_name)
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self._validate_model_name()

    def _validate_model_name(self):
        """Validate that the model name is supported"""
        valid_models = ["gemini-pro", "gemini-pro-vision", "gemini-1.5-pro", "gemini-1.5-flash"]
        if self.model_name not in valid_models:
            raise ValueError(
                f"Invalid model name: {self.model_name}. "
                f"Supported models: {', '.join(valid_models)}"
            )

    def _convert_messages_to_gemini_format(self, messages: List[Message]) -> List[Dict]:
        """
        Convert our message format to Gemini's expected format

        Gemini uses 'user' and 'model' roles instead of 'user' and 'assistant'
        """
        gemini_messages = []
        for msg in messages:
            role = "model" if msg.role == "assistant" else "user"
            gemini_messages.append({
                "role": role,
                "parts": [{"text": msg.content}]
            })
        return gemini_messages

    async def generate(self, messages: List[Message], **kwargs) -> ModelResponse:
        """
        Generate a response using Google Gemini API

        Args:
            messages: List of conversation messages
            **kwargs: Additional parameters like temperature, top_p, max_tokens

        Returns:
            ModelResponse with generated content and metadata
        """
        import httpx
        import json

        if not self.api_key:
            raise ValueError("Google API key is required. Set GOOGLE_API_KEY environment variable.")

        # Extract generation parameters
        temperature = kwargs.get("temperature", 0.7)
        top_p = kwargs.get("top_p", 0.95)
        top_k = kwargs.get("top_k", 40)
        max_tokens = kwargs.get("max_tokens", 2048)

        # Convert messages to Gemini format
        gemini_messages = self._convert_messages_to_gemini_format(messages)

        # Prepare request payload
        payload = {
            "contents": gemini_messages,
            "generationConfig": {
                "temperature": temperature,
                "topP": top_p,
                "topK": top_k,
                "maxOutputTokens": max_tokens,
            }
        }

        # Make API request
        url = f"{self.base_url}/models/{self.model_name}:generateContent?key={self.api_key}"

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()

                result = response.json()

                # Extract response content
                if "candidates" not in result or len(result["candidates"]) == 0:
                    raise ValueError("No response candidates returned from Gemini API")

                candidate = result["candidates"][0]
                content = candidate["content"]["parts"][0]["text"]
                finish_reason = candidate.get("finishReason", "STOP").lower()

                # Extract usage metadata
                usage_metadata = result.get("usageMetadata", {})
                usage = {
                    "prompt_tokens": usage_metadata.get("promptTokenCount", 0),
                    "completion_tokens": usage_metadata.get("candidatesTokenCount", 0),
                    "total_tokens": usage_metadata.get("totalTokenCount", 0)
                }

                return ModelResponse(
                    content=content,
                    model=self.model_name,
                    usage=usage,
                    finish_reason=finish_reason
                )

        except httpx.HTTPStatusError as e:
            error_detail = e.response.text if hasattr(e.response, 'text') else str(e)
            raise Exception(f"Gemini API error: {error_detail}")
        except Exception as e:
            raise Exception(f"Error generating response from Gemini: {str(e)}")

    async def stream_generate(self, messages: List[Message], **kwargs) -> AsyncIterator[str]:
        """
        Stream a response using Google Gemini API

        Args:
            messages: List of conversation messages
            **kwargs: Additional parameters like temperature, top_p, max_tokens

        Yields:
            Chunks of generated text as they become available
        """
        import httpx
        import json

        if not self.api_key:
            raise ValueError("Google API key is required. Set GOOGLE_API_KEY environment variable.")

        # Extract generation parameters
        temperature = kwargs.get("temperature", 0.7)
        top_p = kwargs.get("top_p", 0.95)
        top_k = kwargs.get("top_k", 40)
        max_tokens = kwargs.get("max_tokens", 2048)

        # Convert messages to Gemini format
        gemini_messages = self._convert_messages_to_gemini_format(messages)

        # Prepare request payload
        payload = {
            "contents": gemini_messages,
            "generationConfig": {
                "temperature": temperature,
                "topP": top_p,
                "topK": top_k,
                "maxOutputTokens": max_tokens,
            }
        }

        # Make streaming API request
        url = f"{self.base_url}/models/{self.model_name}:streamGenerateContent?key={self.api_key}&alt=sse"

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream("POST", url, json=payload) as response:
                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            try:
                                data = json.loads(line[6:])  # Remove "data: " prefix

                                if "candidates" in data and len(data["candidates"]) > 0:
                                    candidate = data["candidates"][0]
                                    if "content" in candidate:
                                        parts = candidate["content"].get("parts", [])
                                        if parts and "text" in parts[0]:
                                            yield parts[0]["text"]

                            except json.JSONDecodeError:
                                continue  # Skip invalid JSON lines

        except httpx.HTTPStatusError as e:
            error_detail = e.response.text if hasattr(e.response, 'text') else str(e)
            raise Exception(f"Gemini API streaming error: {error_detail}")
        except Exception as e:
            raise Exception(f"Error streaming response from Gemini: {str(e)}")


class LocalModelProvider(ModelProvider):
    """Local model provider (e.g., Ollama, LM Studio)"""

    def __init__(self, base_url: str = "http://localhost:11434", model_name: str = "llama2"):
        super().__init__(None, model_name)
        self.base_url = base_url

    async def generate(self, messages: List[Message], **kwargs) -> ModelResponse:
        """
        Generate a response using local model API

        TODO: Implement local model API integration (Ollama, etc.)
        """
        return ModelResponse(
            content="This is a placeholder for local model. Implement local API integration.",
            model=self.model_name,
            usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            finish_reason="stop"
        )

    async def stream_generate(self, messages: List[Message], **kwargs) -> AsyncIterator[str]:
        """Stream a response using local model API"""
        response = "This is a local streaming placeholder."
        for word in response.split():
            yield word + " "
