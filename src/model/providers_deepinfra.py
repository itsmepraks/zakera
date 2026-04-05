import httpx
import json
import logging
from typing import AsyncGenerator, List, Optional, Dict, Any
from .providers import ModelProvider, Message, ModelResponse

logger = logging.getLogger(__name__)

class DeepInfraProvider(ModelProvider):
    """Provider for DeepInfra (OpenAI-compatible) models."""
    
    def __init__(
        self, 
        api_key: str, 
        model: str = "meta-llama/Llama-3-70b-chat-hf", 
        base_url: str = "https://api.deepinfra.com/v1/openai"
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url

    async def generate(self, messages: List[Message], **kwargs) -> ModelResponse:
        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
            **kwargs
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json=payload,
                    timeout=60.0
                )
                response.raise_for_status()
                data = response.json()
                
                content = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})
                finish_reason = data["choices"][0].get("finish_reason")
                
                return ModelResponse(
                    content=content,
                    usage=usage,
                    finish_reason=finish_reason
                )
            except Exception as e:
                logger.error(f"DeepInfra API error: {e}")
                raise

    async def stream_generate(self, messages: List[Message], **kwargs) -> AsyncGenerator[str, None]:
        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": True,
            **kwargs
        }
        
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
                timeout=60.0
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            delta = data["choices"][0].get("delta", {})
                            if "content" in delta:
                                yield delta["content"]
                        except json.JSONDecodeError:
                            continue

    def supports_tools(self) -> bool:
        return True
