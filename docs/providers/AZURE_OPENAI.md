# Azure OpenAI Provider

Comprehensive guide for using Azure OpenAI with Zakera AI Chat Agent.

## Overview

The Azure OpenAI provider enables you to use your Azure OpenAI deployments with full enterprise compliance, data residency, and security requirements. Perfect for organizations that need:

- **Data Residency**: Keep data within specific geographic regions
- **Enterprise SLAs**: Azure-backed service level agreements
- **Integration**: Seamless Azure ecosystem integration
- **Compliance**: Meet regulatory and compliance requirements
- **Private Networking**: VNet and Private Link support

## Features

✅ **Full Model Support**: GPT-4, GPT-3.5-Turbo, GPT-4-Vision  
✅ **Multi-Region**: Deploy across multiple Azure regions  
✅ **Custom Deployments**: Use your deployment names  
✅ **Automatic Retry**: Exponential backoff for resilience  
✅ **Streaming**: Real-time response streaming  
✅ **Cost Tracking**: Detailed token usage and costs  
✅ **Authentication**: API key and Azure AD support  

## Quick Start

### 1. Environment Setup

```bash
# Required
export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com"
export AZURE_OPENAI_API_KEY="your-api-key"
export AZURE_OPENAI_DEPLOYMENT_NAME="your-deployment-name"

# Optional
export AZURE_OPENAI_API_VERSION="2024-02-15-preview"
```

### 2. Configuration

```python
from src.model.providers_azure import AzureOpenAIProvider

config = {
    "azure_endpoint": "https://your-resource.openai.azure.com",
    "api_key": "your-api-key",
    "deployment_name": "gpt-4-deployment",
    "api_version": "2024-02-15-preview",
    "region": "eastus",
    "max_retries": 3,
    "timeout": 60,
}

provider = AzureOpenAIProvider(config)
```

### 3. Basic Usage

```python
# Generate response
messages = [
    {"role": "user", "content": "Explain quantum computing"}
]

response = await provider.generate(
    messages=messages,
    temperature=0.7,
    max_tokens=500
)

print(response["content"])
print(f"Cost: ${response['cost']:.6f}")
print(f"Tokens: {response['tokens']['total']}")
```

## Supported Models

| Model | Context Window | Input ($/1K) | Output ($/1K) | Best For |
|-------|----------------|--------------|---------------|----------|
| GPT-4 | 8K | $0.03 | $0.06 | Complex reasoning |
| GPT-4-32K | 32K | $0.06 | $0.12 | Long documents |
| GPT-4-Turbo | 128K | $0.01 | $0.03 | Large context |
| GPT-3.5-Turbo | 4K | $0.0015 | $0.002 | Fast, affordable |
| GPT-3.5-Turbo-16K | 16K | $0.003 | $0.004 | Extended context |

## Advanced Usage

### Streaming Responses

```python
async for chunk in provider.stream_generate(
    messages=messages,
    temperature=0.7
):
    print(chunk, end="", flush=True)
```

### Multi-Region Setup

```python
# Primary region
primary = AzureOpenAIProvider({
    "azure_endpoint": "https://eastus.openai.azure.com",
    "deployment_name": "gpt-4",
    "region": "eastus",
    # ... other config
})

# Failover region
failover = AzureOpenAIProvider({
    "azure_endpoint": "https://westus.openai.azure.com",
    "deployment_name": "gpt-4",
    "region": "westus",
    # ... other config
})

# Use with automatic failover
try:
    response = await primary.generate(messages)
except Exception:
    response = await failover.generate(messages)
```

### Custom Parameters

```python
response = await provider.generate(
    messages=messages,
    temperature=0.8,
    max_tokens=1000,
    top_p=0.95,
    frequency_penalty=0.2,
    presence_penalty=0.2,
    stop=["\n\n", "END"]
)
```

## Setup Guide

### Azure Portal Setup

1. **Create Azure OpenAI Resource**
   - Navigate to Azure Portal
   - Search for "Azure OpenAI"
   - Click "Create" and fill in details
   - Select your region and pricing tier

2. **Deploy a Model**
   - Go to your Azure OpenAI resource
   - Click "Model deployments"
   - Select "Create new deployment"
   - Choose model and give it a name
   - Note the deployment name

3. **Get Credentials**
   - Click "Keys and Endpoint"
   - Copy KEY 1 or KEY 2
   - Copy the Endpoint URL

### Azure CLI Setup

```bash
# Create resource
az cognitiveservices account create \
  --name my-openai-resource \
  --resource-group my-rg \
  --kind OpenAI \
  --sku S0 \
  --location eastus

# Deploy model
az cognitiveservices account deployment create \
  --name my-openai-resource \
  --resource-group my-rg \
  --deployment-name gpt-4 \
  --model-name gpt-4 \
  --model-version "0613" \
  --model-format OpenAI \
  --scale-settings-scale-type "Standard"

# Get keys
az cognitiveservices account keys list \
  --name my-openai-resource \
  --resource-group my-rg
```

## Authentication

### API Key (Simple)

```python
config = {
    "azure_endpoint": "https://your-resource.openai.azure.com",
    "api_key": "your-api-key",
    "deployment_name": "gpt-4",
}
```

### Azure AD (Recommended for Production)

```python
from azure.identity import DefaultAzureCredential

credential = DefaultAzureCredential()
token = credential.get_token("https://cognitiveservices.azure.com/.default")

config = {
    "azure_endpoint": "https://your-resource.openai.azure.com",
    "api_key": token.token,  # Use Azure AD token
    "deployment_name": "gpt-4",
}
```

## Monitoring & Observability

### Built-in Metrics

The provider automatically tracks:
- Request latency
- Token usage (input/output/total)
- Cost per request
- Error rates
- Retry attempts

### Health Checks

```python
# Check provider health
is_healthy = await provider.health_check()
if not is_healthy:
    logger.error("Azure OpenAI provider is unhealthy")
```

### Azure Monitor Integration

Configure diagnostic settings in Azure Portal:
1. Go to your Azure OpenAI resource
2. Click "Diagnostic settings"
3. Add diagnostic setting
4. Send to Log Analytics workspace
5. Enable:
   - Request/Response logs
   - Audit logs
   - Metrics

## Error Handling

### Automatic Retry

The provider includes automatic retry with exponential backoff:

```python
config = {
    # ...
    "max_retries": 3,      # Number of retry attempts
    "retry_delay": 1.0,    # Initial delay (seconds)
    "timeout": 60,         # Request timeout (seconds)
}
```

### Custom Error Handling

```python
try:
    response = await provider.generate(messages)
except asyncio.TimeoutError:
    logger.error("Request timed out")
except Exception as e:
    logger.error(f"Generation failed: {e}")
    # Implement custom fallback logic
```

## Best Practices

### 1. Use Multiple Regions

Deploy across multiple Azure regions for high availability:

```python
regions = [
    {"endpoint": "https://eastus.openai.azure.com", "region": "eastus"},
    {"endpoint": "https://westus.openai.azure.com", "region": "westus"},
]

providers = [AzureOpenAIProvider({**r, **config}) for r in regions]
```

### 2. Monitor Costs

```python
# Track cumulative costs
total_cost = 0
for response in responses:
    total_cost += response["cost"]
    
if total_cost > budget_threshold:
    logger.warning(f"Budget threshold exceeded: ${total_cost:.2f}")
```

### 3. Use Appropriate Models

- **GPT-4**: Complex reasoning, critical accuracy
- **GPT-4-Turbo**: Large context, cost-sensitive
- **GPT-3.5-Turbo**: High throughput, simple tasks

### 4. Optimize Token Usage

```python
# Set reasonable max_tokens
max_tokens = min(
    model_config["max_tokens"],
    estimated_response_length * 1.5  # Add buffer
)

response = await provider.generate(
    messages=messages,
    max_tokens=max_tokens
)
```

### 5. Implement Caching

```python
import hashlib
import json

def cache_key(messages):
    return hashlib.md5(
        json.dumps(messages, sort_keys=True).encode()
    ).hexdigest()

# Check cache before calling API
key = cache_key(messages)
cached = await redis.get(key)
if cached:
    return json.loads(cached)

# Call API and cache result
response = await provider.generate(messages)
await redis.setex(key, 3600, json.dumps(response))  # Cache for 1 hour
```

## Troubleshooting

### Common Issues

**Issue**: "Deployment not found"
- Verify deployment name matches Azure Portal
- Check API version compatibility
- Ensure model is deployed in correct region

**Issue**: "Rate limit exceeded"
- Implement exponential backoff
- Increase retry delay
- Request quota increase in Azure Portal

**Issue**: "Authentication failed"
- Verify API key is correct
- Check endpoint URL format
- For Azure AD, ensure token hasn't expired

### Debug Logging

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("src.model.providers_azure")
```

## FAQ

**Q: What's the difference between Azure OpenAI and OpenAI?**
A: Azure OpenAI provides the same models with enterprise SLAs, data residency, private networking, and Azure ecosystem integration.

**Q: Can I use the same code for both providers?**
A: Yes! The provider interface is consistent. Just change the provider configuration.

**Q: How do I handle rate limits?**
A: The provider includes automatic retry. For high-volume scenarios, implement request queuing and throttling.

**Q: What's the cost?**
A: Pricing matches OpenAI but is billed through Azure. Check Azure Portal for current rates.

**Q: Can I use Private Link?**
A: Yes! Configure Private Link in Azure Portal for private connectivity.

## Support

- **Documentation**: [Azure OpenAI Docs](https://learn.microsoft.com/azure/cognitive-services/openai/)
- **Issues**: [GitHub Issues](https://github.com/itsmepraks/zakera/issues)
- **Azure Support**: [Azure Portal](https://portal.azure.com)

---

**Last Updated**: February 2026  
**Provider Version**: 1.0.0  
**Status**: Production Ready ✅
