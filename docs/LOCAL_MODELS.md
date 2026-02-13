# Local LLM Models Guide

This guide covers setting up and using local LLM models with Zakera, including Ollama and HuggingFace Transformers.

## Table of Contents

- [Overview](#overview)
- [Ollama Setup](#ollama-setup)
- [HuggingFace Setup](#huggingface-setup)
- [Model Configuration](#model-configuration)
- [Fallback Strategies](#fallback-strategies)
- [Performance Optimization](#performance-optimization)
- [Troubleshooting](#troubleshooting)

## Overview

Zakera supports multiple ways to run LLM models:

1. **API-based Models**: OpenAI, Anthropic, Gemini (cloud-based, pay-per-use)
2. **Ollama**: Easy local model deployment (recommended for most users)
3. **HuggingFace**: Direct model loading with full control

### Why Use Local Models?

- ✅ **Privacy**: Data stays on your machine
- ✅ **Cost**: No API fees
- ✅ **Offline**: Works without internet
- ✅ **Customization**: Full control over models
- ✅ **Speed**: No network latency (with good hardware)

### Trade-offs

- ❌ **Hardware**: Requires GPU for good performance
- ❌ **Setup**: More complex initial configuration
- ❌ **Quality**: May not match flagship API models
- ❌ **Maintenance**: You manage updates

## Ollama Setup

### Installation

**macOS**:
```bash
brew install ollama
```

**Linux**:
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

**Windows**:
Download from [https://ollama.ai/download](https://ollama.ai/download)

### Starting Ollama

```bash
# Start the Ollama service
ollama serve

# Or run as background service (Linux/macOS)
sudo systemctl start ollama
```

### Installing Models

```bash
# Install Llama 3 8B (recommended - ~4.7GB)
ollama pull llama3:8b

# Install Mistral 7B (great performance - ~4.1GB)
ollama pull mistral:7b

# Install CodeLlama for coding tasks (~7.4GB)
ollama pull codellama:13b

# Install Mixtral for advanced tasks (~26GB)
ollama pull mixtral:8x7b

# List installed models
ollama list

# Remove a model
ollama rm llama3:8b
```

### Recommended Models by Use Case

| Use Case | Model | Size | Notes |
|----------|-------|------|-------|
| **General Chat** | `llama3:8b` | 4.7GB | Best balance |
| **Fast Responses** | `mistral:7b` | 4.1GB | Very efficient |
| **Code Generation** | `codellama:13b` | 7.4GB | Specialized |
| **Advanced Reasoning** | `mixtral:8x7b` | 26GB | Requires 16GB+ RAM |
| **Large Context** | `llama3:70b` | 40GB | Best quality, needs GPU |

### Configuration

Update your `.env` file:

```env
# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
DEFAULT_MODEL=llama3:8b
ENABLE_OLLAMA=true
```

### Testing Ollama

```bash
# Test directly with Ollama CLI
ollama run llama3:8b "Hello, how are you?"

# Test via Zakera API
curl -X POST http://localhost:8000/api/models/generate \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Hello!"}],
    "model": "llama3:8b"
  }'
```

## HuggingFace Setup

### Prerequisites

```bash
# Install PyTorch (CPU version)
pip install torch torchvision torchaudio

# Or for GPU (CUDA 11.8)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Install HuggingFace libraries
pip install transformers accelerate sentencepiece
```

### GPU Setup (Optional but Recommended)

**Check GPU availability**:
```python
import torch
print(f"CUDA available: {torch.cuda.is_available()}")
print(f"GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None'}")
```

**For 8-bit quantization** (reduces memory by ~50%):
```bash
pip install bitsandbytes
```

### Recommended Models

| Model | Size | Memory | Notes |
|-------|------|--------|-------|
| **mistralai/Mistral-7B-Instruct-v0.2** | 7B | 16GB | Excellent performance |
| **meta-llama/Llama-2-7b-chat-hf** | 7B | 16GB | Good for chat |
| **meta-llama/Llama-2-13b-chat-hf** | 13B | 28GB | Better quality |
| **codellama/CodeLlama-7b-Instruct-hf** | 7B | 16GB | Code generation |

### Model Loading Examples

**Basic (CPU)**:
```python
from src.model.providers_huggingface import HuggingFaceProvider

provider = HuggingFaceProvider(
    model_name="mistralai/Mistral-7B-Instruct-v0.2",
    device="cpu"
)
```

**With GPU**:
```python
provider = HuggingFaceProvider(
    model_name="mistralai/Mistral-7B-Instruct-v0.2",
    device="cuda"
)
```

**With 8-bit Quantization** (half the memory):
```python
provider = HuggingFaceProvider(
    model_name="mistralai/Mistral-7B-Instruct-v0.2",
    load_in_8bit=True  # Automatic GPU placement
)
```

**With 4-bit Quantization** (quarter memory, experimental):
```python
provider = HuggingFaceProvider(
    model_name="mistralai/Mistral-7B-Instruct-v0.2",
    load_in_4bit=True
)
```

### Configuration

Update your `.env` file:

```env
# HuggingFace Configuration
HUGGINGFACE_MODEL=mistralai/Mistral-7B-Instruct-v0.2
HUGGINGFACE_DEVICE=cuda  # or cpu
HUGGINGFACE_8BIT=true  # Enable 8-bit quantization
ENABLE_HUGGINGFACE=true
```

### Downloading Models

Models are automatically downloaded on first use to:
- Linux/Mac: `~/.cache/huggingface/hub/`
- Windows: `C:\Users\<username>\.cache\huggingface\hub\`

Pre-download models:
```python
from transformers import AutoModelForCausalLM, AutoTokenizer

model_name = "mistralai/Mistral-7B-Instruct-v0.2"
AutoTokenizer.from_pretrained(model_name)
AutoModelForCausalLM.from_pretrained(model_name)
```

## Model Configuration

### Setting Default Model

In `.env`:
```env
DEFAULT_MODEL=llama3:8b  # or gpt-3.5-turbo, claude-3-haiku, etc.
```

### Enabling/Disabling Providers

```python
from src.model.model_manager import ModelManager
from src.model.config import ModelConfig, ModelProviderType

# Disable a provider
ModelConfig.PROVIDER_DEFAULTS[ModelProviderType.OPENAI].enabled = False

# Change provider priority
ModelConfig.PROVIDER_DEFAULTS[ModelProviderType.OLLAMA].priority = 10
```

### Model Parameters

```python
response = await model_manager.generate(
    messages=messages,
    model="llama3:8b",
    temperature=0.7,      # 0.0-2.0, higher = more creative
    max_tokens=2048,      # Maximum response length
    top_p=0.9,           # Nucleus sampling threshold
    top_k=40,            # Top-k sampling (local models)
    frequency_penalty=0.0,  # Reduce repetition (API models)
    presence_penalty=0.0    # Encourage new topics (API models)
)
```

## Fallback Strategies

### Sequential Fallback (Default)

Tries models one by one until success:

```python
from src.model.model_manager import ModelManager, FallbackStrategy

model_manager = ModelManager(
    default_model="gpt-4-turbo",
    fallback_strategy=FallbackStrategy.SEQUENTIAL
)

# Will try: gpt-4-turbo → claude-3-sonnet → gpt-3.5-turbo
response = await model_manager.generate(messages, fallback=True)
```

### Custom Fallback Chain

```python
from src.model.config import ModelConfig

# Define custom fallback for a model
ModelConfig.get_fallback_chain = lambda primary: [
    primary,
    "llama3:8b",      # Local fallback
    "gpt-3.5-turbo"   # Cheap API fallback
]
```

### No Fallback

```python
model_manager = ModelManager(
    fallback_strategy=FallbackStrategy.NONE
)

# Will fail immediately if primary model unavailable
response = await model_manager.generate(messages, fallback=False)
```

### Provider Priority

Providers are tried in order of priority (higher = first):

```env
# In config.py
PROVIDER_DEFAULTS = {
    ModelProviderType.OPENAI: ProviderConfig(priority=10),
    ModelProviderType.OLLAMA: ProviderConfig(priority=9),  # Try local first!
    ModelProviderType.ANTHROPIC: ProviderConfig(priority=8),
}
```

## Performance Optimization

### Hardware Requirements

**Minimum (CPU only)**:
- RAM: 16GB
- Storage: 10GB
- Model: 7B parameters max
- Speed: Slow (1-5 tokens/sec)

**Recommended (GPU)**:
- GPU: NVIDIA RTX 3060+ (12GB VRAM)
- RAM: 16GB
- Storage: 50GB SSD
- Model: Up to 13B parameters
- Speed: Fast (20-50 tokens/sec)

**Optimal (High-end GPU)**:
- GPU: NVIDIA RTX 4090 (24GB VRAM)
- RAM: 32GB+
- Storage: 100GB NVMe SSD
- Model: Up to 70B parameters
- Speed: Very fast (50-100 tokens/sec)

### Optimization Tips

**1. Use Quantization**:
```python
# 8-bit: 50% less memory, ~5% quality loss
provider = HuggingFaceProvider(model_name="...", load_in_8bit=True)

# 4-bit: 75% less memory, ~10% quality loss
provider = HuggingFaceProvider(model_name="...", load_in_4bit=True)
```

**2. Choose Smaller Models**:
- 7B models: Fast, good quality
- 13B models: Better quality, slower
- 70B models: Best quality, requires high-end GPU

**3. Batch Processing** (HuggingFace only):
```python
# Process multiple requests together
batch_size = 4  # Adjust based on GPU memory
```

**4. Model Caching**:
```bash
# Keep model in memory between requests
# Saves 10-30 seconds per request
```

**5. Use Ollama for Better Performance**:
- Optimized inference engine
- Automatic memory management
- 2-3x faster than raw HuggingFace

### Monitoring Performance

```python
# Get statistics
stats = model_manager.get_statistics()
print(f"Requests: {stats['request_count']}")
print(f"Failures: {stats['failure_count']}")
print(f"Provider health: {stats['provider_health']}")
```

## Troubleshooting

### Ollama Issues

**Problem: "Connection refused"**
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama
ollama serve
```

**Problem: "Model not found"**
```bash
# List installed models
ollama list

# Pull the model
ollama pull llama3:8b
```

**Problem: Slow performance**
- Reduce `max_tokens` parameter
- Use smaller model (7B instead of 13B)
- Close other applications
- Check CPU/RAM usage

### HuggingFace Issues

**Problem: "Out of memory"**
```python
# Solution 1: Enable quantization
provider = HuggingFaceProvider(load_in_8bit=True)

# Solution 2: Use CPU
provider = HuggingFaceProvider(device="cpu")

# Solution 3: Smaller model
provider = HuggingFaceProvider(model_name="mistralai/Mistral-7B-Instruct-v0.2")
```

**Problem: "CUDA out of memory"**
```python
# Clear GPU cache
import torch
torch.cuda.empty_cache()

# Reduce max_tokens
response = await provider.generate(messages, max_tokens=512)
```

**Problem: Slow first request**
- Model loads on first use (10-60 seconds)
- Model stays in memory for subsequent requests
- Consider pre-warming:

```python
# Pre-load model at startup
await provider.generate([Message(role="user", content="Hi")], max_tokens=10)
```

### General Issues

**Problem: All providers failing**
```bash
# Check health
curl http://localhost:8000/api/models/health

# Check logs
tail -f logs/zakera.log
```

**Problem: Incorrect responses**
- Check temperature (lower = more focused)
- Verify model is appropriate for task
- Check prompt formatting

**Problem: Timeout errors**
```python
# Increase timeout
ModelConfig.PROVIDER_DEFAULTS[ModelProviderType.OLLAMA].timeout = 180
```

## API Examples

### List Available Models

```bash
curl http://localhost:8000/api/models/
```

### Get Model Info

```bash
curl http://localhost:8000/api/models/llama3:8b
```

### Generate with Specific Model

```bash
curl -X POST http://localhost:8000/api/models/generate \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Explain quantum computing"}
    ],
    "model": "llama3:8b",
    "temperature": 0.7,
    "max_tokens": 500
  }'
```

### Streaming Response

```bash
curl -X POST http://localhost:8000/api/models/generate \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Write a story"}],
    "model": "llama3:8b",
    "stream": true
  }'
```

### Check Provider Health

```bash
curl http://localhost:8000/api/models/health
```

## Best Practices

1. **Start with Ollama**: Easiest setup, good performance
2. **Use Fallback Chains**: Local → API for reliability
3. **Monitor Performance**: Check stats regularly
4. **Choose Right Model**: Balance quality vs. speed
5. **Optimize for Hardware**: Use quantization if needed
6. **Cache Models**: Keep frequently used models loaded
7. **Test Thoroughly**: Verify quality before production
8. **Update Regularly**: Keep models and libraries current

## Next Steps

- [Model Configuration Guide](./model-configuration.md)
- [API Documentation](./api-reference.md)
- [Performance Benchmarks](./benchmarks.md)
- [Production Deployment](./deployment.md)
