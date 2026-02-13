"""HuggingFace Transformers provider for local models"""

from typing import List, Dict, Optional, AsyncIterator
import asyncio
import torch
from .providers import ModelProvider, Message, ModelResponse


class HuggingFaceProvider(ModelProvider):
    """
    HuggingFace Transformers provider for running models locally
    
    Supports any HuggingFace model with proper device management,
    quantization, and optimization.
    """
    
    def __init__(
        self,
        model_name: str = "mistralai/Mistral-7B-Instruct-v0.2",
        device: Optional[str] = None,
        load_in_8bit: bool = False,
        load_in_4bit: bool = False,
        trust_remote_code: bool = False
    ):
        super().__init__(None, model_name)
        
        # Auto-detect device if not specified
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
        
        self.load_in_8bit = load_in_8bit
        self.load_in_4bit = load_in_4bit
        self.trust_remote_code = trust_remote_code
        
        self.model = None
        self.tokenizer = None
        self._initialized = False
    
    async def _initialize(self):
        """Initialize model and tokenizer (lazy loading)"""
        if self._initialized:
            return
        
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
            
            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                trust_remote_code=self.trust_remote_code
            )
            
            # Prepare model loading kwargs
            model_kwargs = {
                "trust_remote_code": self.trust_remote_code,
                "torch_dtype": torch.float16 if self.device == "cuda" else torch.float32,
            }
            
            # Add quantization if specified
            if self.load_in_8bit:
                model_kwargs["load_in_8bit"] = True
                model_kwargs["device_map"] = "auto"
            elif self.load_in_4bit:
                model_kwargs["load_in_4bit"] = True
                model_kwargs["device_map"] = "auto"
            elif self.device == "cuda":
                model_kwargs["device_map"] = "auto"
            
            # Load model (this is CPU-bound, run in thread pool)
            loop = asyncio.get_event_loop()
            self.model = await loop.run_in_executor(
                None,
                lambda: AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    **model_kwargs
                )
            )
            
            # Move to device if not using device_map
            if "device_map" not in model_kwargs and self.device != "cpu":
                self.model = self.model.to(self.device)
            
            self._initialized = True
            
        except Exception as e:
            raise Exception(f"Failed to initialize HuggingFace model: {str(e)}")
    
    def _convert_messages_to_prompt(self, messages: List[Message]) -> str:
        """
        Convert messages to a prompt string
        
        This is a generic implementation. Override for specific model formats.
        """
        prompt_parts = []
        
        for msg in messages:
            if msg.role == "system":
                prompt_parts.append(f"System: {msg.content}")
            elif msg.role == "user":
                prompt_parts.append(f"User: {msg.content}")
            elif msg.role == "assistant":
                prompt_parts.append(f"Assistant: {msg.content}")
        
        # Add assistant prefix for next response
        prompt_parts.append("Assistant:")
        
        return "\n\n".join(prompt_parts)
    
    async def generate(self, messages: List[Message], **kwargs) -> ModelResponse:
        """
        Generate a response using HuggingFace model
        
        Args:
            messages: List of conversation messages
            **kwargs: Generation parameters
        
        Returns:
            ModelResponse with generated content
        """
        await self._initialize()
        
        # Extract generation parameters
        temperature = kwargs.get("temperature", 0.7)
        top_p = kwargs.get("top_p", 0.9)
        top_k = kwargs.get("top_k", 50)
        max_tokens = kwargs.get("max_tokens", 512)
        
        # Convert messages to prompt
        prompt = self._convert_messages_to_prompt(messages)
        
        # Tokenize
        inputs = self.tokenizer(
            prompt,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=4096
        )
        
        # Move to device
        if self.device != "cpu":
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        # Generate (CPU-bound, run in thread pool)
        loop = asyncio.get_event_loop()
        
        def _generate():
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=max_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    top_k=top_k,
                    do_sample=True,
                    pad_token_id=self.tokenizer.pad_token_id or self.tokenizer.eos_token_id,
                    eos_token_id=self.tokenizer.eos_token_id,
                )
            return outputs
        
        try:
            outputs = await loop.run_in_executor(None, _generate)
            
            # Decode
            generated_text = self.tokenizer.decode(
                outputs[0][inputs["input_ids"].shape[1]:],
                skip_special_tokens=True
            )
            
            # Calculate token usage
            input_tokens = inputs["input_ids"].shape[1]
            output_tokens = outputs.shape[1] - input_tokens
            
            return ModelResponse(
                content=generated_text.strip(),
                model=self.model_name,
                usage={
                    "prompt_tokens": input_tokens,
                    "completion_tokens": output_tokens,
                    "total_tokens": input_tokens + output_tokens
                },
                finish_reason="stop"
            )
        
        except Exception as e:
            raise Exception(f"Error generating with HuggingFace: {str(e)}")
    
    async def stream_generate(self, messages: List[Message], **kwargs) -> AsyncIterator[str]:
        """
        Stream generation using HuggingFace model
        
        Note: True streaming with HuggingFace is complex. This implementation
        generates tokens and yields them incrementally.
        """
        await self._initialize()
        
        # Extract generation parameters
        temperature = kwargs.get("temperature", 0.7)
        top_p = kwargs.get("top_p", 0.9)
        top_k = kwargs.get("top_k", 50)
        max_tokens = kwargs.get("max_tokens", 512)
        
        # Convert messages to prompt
        prompt = self._convert_messages_to_prompt(messages)
        
        # Tokenize
        inputs = self.tokenizer(
            prompt,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=4096
        )
        
        # Move to device
        if self.device != "cpu":
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        # Generate token by token
        try:
            input_ids = inputs["input_ids"]
            attention_mask = inputs["attention_mask"]
            
            for _ in range(max_tokens):
                # Run in thread pool
                loop = asyncio.get_event_loop()
                
                def _forward():
                    with torch.no_grad():
                        outputs = self.model(
                            input_ids=input_ids,
                            attention_mask=attention_mask
                        )
                        logits = outputs.logits[:, -1, :]
                        
                        # Apply temperature
                        logits = logits / temperature
                        
                        # Apply top-p and top-k
                        filtered_logits = self._apply_top_k_top_p(logits, top_k, top_p)
                        
                        # Sample
                        probs = torch.softmax(filtered_logits, dim=-1)
                        next_token = torch.multinomial(probs, num_samples=1)
                        
                        return next_token
                
                next_token = await loop.run_in_executor(None, _forward)
                
                # Check for EOS
                if next_token.item() == self.tokenizer.eos_token_id:
                    break
                
                # Decode and yield token
                token_text = self.tokenizer.decode(next_token[0], skip_special_tokens=True)
                if token_text:
                    yield token_text
                
                # Update input_ids and attention_mask
                input_ids = torch.cat([input_ids, next_token], dim=-1)
                attention_mask = torch.cat([
                    attention_mask,
                    torch.ones((1, 1), dtype=torch.long, device=attention_mask.device)
                ], dim=-1)
        
        except Exception as e:
            raise Exception(f"Error streaming with HuggingFace: {str(e)}")
    
    def _apply_top_k_top_p(self, logits: torch.Tensor, top_k: int, top_p: float) -> torch.Tensor:
        """Apply top-k and top-p filtering to logits"""
        # Top-k filtering
        if top_k > 0:
            top_k = min(top_k, logits.size(-1))
            indices_to_remove = logits < torch.topk(logits, top_k)[0][..., -1, None]
            logits[indices_to_remove] = float('-inf')
        
        # Top-p filtering
        if top_p < 1.0:
            sorted_logits, sorted_indices = torch.sort(logits, descending=True)
            cumulative_probs = torch.cumsum(torch.softmax(sorted_logits, dim=-1), dim=-1)
            
            sorted_indices_to_remove = cumulative_probs > top_p
            sorted_indices_to_remove[..., 1:] = sorted_indices_to_remove[..., :-1].clone()
            sorted_indices_to_remove[..., 0] = False
            
            indices_to_remove = sorted_indices_to_remove.scatter(1, sorted_indices, sorted_indices_to_remove)
            logits[indices_to_remove] = float('-inf')
        
        return logits
    
    def unload(self):
        """Unload model from memory"""
        if self.model is not None:
            del self.model
            self.model = None
        if self.tokenizer is not None:
            del self.tokenizer
            self.tokenizer = None
        
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        self._initialized = False
