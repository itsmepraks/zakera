from abc import ABC, abstractmethod
from typing import List, Dict, Optional, AsyncIterator, Any
from dataclasses import dataclass
import os
import json
import asyncio
from datetime import datetime

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
    """OpenAI API provider with full integration"""
    
    def __init__(self, api_key: Optional[str] = None, model_name: str = "gpt-4-turbo-preview"):
        super().__init__(api_key or os.getenv("OPENAI_API_KEY"), model_name)
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.organization = os.getenv("OPENAI_ORGANIZATION")
        self.max_retries = int(os.getenv("OPENAI_MAX_RETRIES", "3"))
        self.timeout = float(os.getenv("OPENAI_TIMEOUT", "60.0"))
        
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY environment variable.")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for OpenAI API requests"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        if self.organization:
            headers["OpenAI-Organization"] = self.organization
        return headers
    
    def _convert_messages(self, messages: List[Message]) -> List[Dict[str, Any]]:
        """Convert internal message format to OpenAI format"""
        openai_messages = []
        for msg in messages:
            message_dict = {
                "role": msg.role,
                "content": msg.content
            }
            if msg.name:
                message_dict["name"] = msg.name
            openai_messages.append(message_dict)
        return openai_messages
    
    async def _make_request_with_retry(self, client, method: str, url: str, **kwargs) -> Any:
        """Make HTTP request with exponential backoff retry logic"""
        import httpx
        
        last_exception = None
        for attempt in range(self.max_retries):
            try:
                if method == "POST":
                    response = await client.post(url, **kwargs)
                else:
                    response = await client.get(url, **kwargs)
                
                response.raise_for_status()
                return response
                
            except httpx.HTTPStatusError as e:
                last_exception = e
                # Don't retry on client errors (4xx) except rate limits
                if 400 <= e.response.status_code < 500 and e.response.status_code != 429:
                    raise OpenAIError(f"OpenAI API error: {e.response.text}", e.response.status_code)
                
                # Exponential backoff for retryable errors
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                    
            except httpx.TimeoutException as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                    
            except Exception as e:
                raise OpenAIError(f"Unexpected error: {str(e)}")
        
        # All retries exhausted
        if isinstance(last_exception, httpx.HTTPStatusError):
            raise OpenAIError(
                f"OpenAI API error after {self.max_retries} retries: {last_exception.response.text}",
                last_exception.response.status_code
            )
        else:
            raise OpenAIError(f"Request failed after {self.max_retries} retries: {str(last_exception)}")
    
    async def generate(self, messages: List[Message], **kwargs) -> ModelResponse:
        """
        Generate a response using OpenAI Chat Completions API
        
        Args:
            messages: List of conversation messages
            **kwargs: Additional parameters:
                - temperature (float): Sampling temperature (0-2)
                - top_p (float): Nucleus sampling parameter
                - max_tokens (int): Maximum tokens to generate
                - presence_penalty (float): Presence penalty (-2 to 2)
                - frequency_penalty (float): Frequency penalty (-2 to 2)
                - stop (List[str]): Stop sequences
                - functions (List[Dict]): Function definitions for function calling
                - function_call (str|Dict): Force function calling
                - response_format (Dict): Response format (e.g., {"type": "json_object"})
                - seed (int): Random seed for deterministic output
                - user (str): User identifier for abuse monitoring
        
        Returns:
            ModelResponse with generated content and metadata
        """
        import httpx
        
        # Build request payload
        payload = {
            "model": self.model_name,
            "messages": self._convert_messages(messages),
        }
        
        # Add optional parameters
        optional_params = [
            "temperature", "top_p", "max_tokens", "presence_penalty",
            "frequency_penalty", "stop", "functions", "function_call",
            "response_format", "seed", "user", "n", "logit_bias"
        ]
        for param in optional_params:
            if param in kwargs:
                payload[param] = kwargs[param]
        
        url = f"{self.base_url}/chat/completions"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await self._make_request_with_retry(
                    client, "POST", url,
                    json=payload,
                    headers=self._get_headers()
                )
                
                result = response.json()
                
                # Extract response
                if "choices" not in result or len(result["choices"]) == 0:
                    raise OpenAIError("No response choices returned from OpenAI API")
                
                choice = result["choices"][0]
                message = choice["message"]
                
                # Handle function calls
                if "function_call" in message:
                    content = json.dumps(message["function_call"])
                else:
                    content = message.get("content", "")
                
                # Extract usage information
                usage = result.get("usage", {})
                
                return ModelResponse(
                    content=content,
                    model=result.get("model", self.model_name),
                    usage={
                        "prompt_tokens": usage.get("prompt_tokens", 0),
                        "completion_tokens": usage.get("completion_tokens", 0),
                        "total_tokens": usage.get("total_tokens", 0)
                    },
                    finish_reason=choice.get("finish_reason", "stop")
                )
                
        except OpenAIError:
            raise
        except Exception as e:
            raise OpenAIError(f"Error generating response from OpenAI: {str(e)}")
    
    async def stream_generate(self, messages: List[Message], **kwargs) -> AsyncIterator[str]:
        """
        Stream a response using OpenAI Chat Completions API with SSE
        
        Args:
            messages: List of conversation messages
            **kwargs: Same as generate() method
        
        Yields:
            Chunks of generated text as they become available
        """
        import httpx
        
        # Build request payload
        payload = {
            "model": self.model_name,
            "messages": self._convert_messages(messages),
            "stream": True
        }
        
        # Add optional parameters
        optional_params = [
            "temperature", "top_p", "max_tokens", "presence_penalty",
            "frequency_penalty", "stop", "functions", "function_call",
            "response_format", "seed", "user"
        ]
        for param in optional_params:
            if param in kwargs:
                payload[param] = kwargs[param]
        
        url = f"{self.base_url}/chat/completions"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST", url,
                    json=payload,
                    headers=self._get_headers()
                ) as response:
                    response.raise_for_status()
                    
                    async for line in response.aiter_lines():
                        # OpenAI SSE format: "data: {json}\n\n"
                        if line.startswith("data: "):
                            data_str = line[6:].strip()
                            
                            # Stream end signal
                            if data_str == "[DONE]":
                                break
                            
                            try:
                                data = json.loads(data_str)
                                
                                if "choices" in data and len(data["choices"]) > 0:
                                    choice = data["choices"][0]
                                    delta = choice.get("delta", {})
                                    
                                    # Yield content chunks
                                    if "content" in delta and delta["content"]:
                                        yield delta["content"]
                                    
                                    # Handle function calls in streaming
                                    if "function_call" in delta:
                                        function_data = delta["function_call"]
                                        if "arguments" in function_data:
                                            yield function_data["arguments"]
                                            
                            except json.JSONDecodeError:
                                continue  # Skip invalid JSON lines
                                
        except httpx.HTTPStatusError as e:
            error_detail = e.response.text if hasattr(e.response, 'text') else str(e)
            raise OpenAIError(f"OpenAI API streaming error: {error_detail}", e.response.status_code)
        except Exception as e:
            raise OpenAIError(f"Error streaming response from OpenAI: {str(e)}")

class OpenAIError(Exception):
    """Custom exception for OpenAI API errors"""
    
    def __init__(self, message: str, status_code: Optional[int] = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class AnthropicProvider(ModelProvider):
    """Anthropic Claude API provider"""
    
    def __init__(self, api_key: Optional[str] = None, model_name: str = "claude-3-sonnet-20240229"):
        super().__init__(api_key or os.getenv("ANTHROPIC_API_KEY"), model_name)
        self.base_url = "https://api.anthropic.com/v1"
    
    async def generate(self, messages: List[Message], **kwargs) -> ModelResponse:
        """
        Generate a response using Anthropic API
        
        TODO: Implement actual Anthropic API call
        """
        return ModelResponse(
            content="This is a placeholder response. Implement Anthropic API integration.",
            model=self.model_name,
            usage={"input_tokens": 0, "output_tokens": 0},
            finish_reason="end_turn"
        )
    
    async def stream_generate(self, messages: List[Message], **kwargs) -> AsyncIterator[str]:
        """
        Stream a response using Anthropic API
        
        TODO: Implement actual streaming with Anthropic API
        """
        response = "This is a streaming placeholder. Implement Anthropic streaming."
        for word in response.split():
            yield word + " "

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
