"""Ollama provider for local LLM models"""

from typing import List, Dict, Optional, AsyncIterator
import httpx
import json
from .providers import ModelProvider, Message, ModelResponse


class OllamaProvider(ModelProvider):
    """
    Ollama provider for running local LLM models
    
    Supports models like Llama, Mistral, CodeLlama, Mixtral, etc.
    Ollama must be installed and running locally.
    
    Installation: https://ollama.ai/
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model_name: str = "llama3:8b"
    ):
        super().__init__(None, model_name)
        self.base_url = base_url.rstrip("/")
        self.api_generate = f"{self.base_url}/api/generate"
        self.api_chat = f"{self.base_url}/api/chat"
        self.api_tags = f"{self.base_url}/api/tags"
    
    def _convert_messages_to_ollama_format(self, messages: List[Message]) -> List[Dict]:
        """Convert messages to Ollama chat format"""
        ollama_messages = []
        for msg in messages:
            ollama_messages.append({
                "role": msg.role,
                "content": msg.content
            })
        return ollama_messages
    
    async def check_availability(self) -> bool:
        """Check if Ollama is running and accessible"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False
    
    async def list_models(self) -> List[str]:
        """List available Ollama models"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self.api_tags)
                response.raise_for_status()
                data = response.json()
                return [model["name"] for model in data.get("models", [])]
        except Exception as e:
            raise Exception(f"Failed to list Ollama models: {str(e)}")
    
    async def pull_model(self, model_name: str) -> AsyncIterator[Dict]:
        """Pull/download a model from Ollama library"""
        try:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/pull",
                    json={"name": model_name}
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line:
                            try:
                                yield json.loads(line)
                            except json.JSONDecodeError:
                                continue
        except Exception as e:
            raise Exception(f"Failed to pull model {model_name}: {str(e)}")
    
    async def generate(self, messages: List[Message], **kwargs) -> ModelResponse:
        """
        Generate a response using Ollama chat API
        
        Args:
            messages: List of conversation messages
            **kwargs: Additional parameters (temperature, top_p, etc.)
        
        Returns:
            ModelResponse with generated content
        """
        if not await self.check_availability():
            raise Exception(
                "Ollama is not running. Please start Ollama: https://ollama.ai/"
            )
        
        # Extract generation parameters
        temperature = kwargs.get("temperature", 0.7)
        top_p = kwargs.get("top_p", 0.9)
        top_k = kwargs.get("top_k", 40)
        max_tokens = kwargs.get("max_tokens", 2048)
        
        # Convert messages to Ollama format
        ollama_messages = self._convert_messages_to_ollama_format(messages)
        
        # Prepare request payload
        payload = {
            "model": self.model_name,
            "messages": ollama_messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "top_p": top_p,
                "top_k": top_k,
                "num_predict": max_tokens,
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(self.api_chat, json=payload)
                response.raise_for_status()
                
                result = response.json()
                
                # Extract response
                content = result.get("message", {}).get("content", "")
                
                # Extract token usage if available
                usage = {
                    "prompt_tokens": result.get("prompt_eval_count", 0),
                    "completion_tokens": result.get("eval_count", 0),
                    "total_tokens": result.get("prompt_eval_count", 0) + result.get("eval_count", 0)
                }
                
                return ModelResponse(
                    content=content,
                    model=self.model_name,
                    usage=usage,
                    finish_reason="stop"
                )
        
        except httpx.HTTPStatusError as e:
            error_detail = e.response.text if hasattr(e.response, 'text') else str(e)
            raise Exception(f"Ollama API error: {error_detail}")
        except Exception as e:
            raise Exception(f"Error generating response from Ollama: {str(e)}")
    
    async def stream_generate(self, messages: List[Message], **kwargs) -> AsyncIterator[str]:
        """
        Stream a response using Ollama chat API
        
        Args:
            messages: List of conversation messages
            **kwargs: Additional parameters
        
        Yields:
            Chunks of generated text
        """
        if not await self.check_availability():
            raise Exception(
                "Ollama is not running. Please start Ollama: https://ollama.ai/"
            )
        
        # Extract generation parameters
        temperature = kwargs.get("temperature", 0.7)
        top_p = kwargs.get("top_p", 0.9)
        top_k = kwargs.get("top_k", 40)
        max_tokens = kwargs.get("max_tokens", 2048)
        
        # Convert messages to Ollama format
        ollama_messages = self._convert_messages_to_ollama_format(messages)
        
        # Prepare request payload
        payload = {
            "model": self.model_name,
            "messages": ollama_messages,
            "stream": True,
            "options": {
                "temperature": temperature,
                "top_p": top_p,
                "top_k": top_k,
                "num_predict": max_tokens,
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream("POST", self.api_chat, json=payload) as response:
                    response.raise_for_status()
                    
                    async for line in response.aiter_lines():
                        if line:
                            try:
                                data = json.loads(line)
                                
                                if "message" in data:
                                    content = data["message"].get("content", "")
                                    if content:
                                        yield content
                                
                                # Check if done
                                if data.get("done", False):
                                    break
                            
                            except json.JSONDecodeError:
                                continue
        
        except httpx.HTTPStatusError as e:
            error_detail = e.response.text if hasattr(e.response, 'text') else str(e)
            raise Exception(f"Ollama streaming error: {error_detail}")
        except Exception as e:
            raise Exception(f"Error streaming from Ollama: {str(e)}")
