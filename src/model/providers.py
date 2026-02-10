from abc import ABC, abstractmethod
from typing import List, Dict, Optional, AsyncIterator
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
    """OpenAI API provider"""
    
    def __init__(self, api_key: Optional[str] = None, model_name: str = "gpt-4-turbo-preview"):
        super().__init__(api_key or os.getenv("OPENAI_API_KEY"), model_name)
        self.base_url = "https://api.openai.com/v1"
    
    async def generate(self, messages: List[Message], **kwargs) -> ModelResponse:
        """
        Generate a response using OpenAI API
        
        TODO: Implement actual OpenAI API call using httpx or openai library
        """
        # Placeholder implementation
        return ModelResponse(
            content="This is a placeholder response. Implement OpenAI API integration.",
            model=self.model_name,
            usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            finish_reason="stop"
        )
    
    async def stream_generate(self, messages: List[Message], **kwargs) -> AsyncIterator[str]:
        """
        Stream a response using OpenAI API
        
        TODO: Implement actual streaming with OpenAI API
        """
        # Placeholder implementation
        response = "This is a streaming placeholder. Implement OpenAI streaming."
        for word in response.split():
            yield word + " "

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
