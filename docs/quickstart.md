# Zakera Quick Start Guide

## 5-Minute Quick Start

Get up and running with Zakera in just 5 minutes!

### Step 1: Get Your API Key

1. Sign up at [https://zakera.app/signup](https://zakera.app/signup)
2. Navigate to [API Keys](https://zakera.app/dashboard/api-keys)
3. Click "Create New Key"
4. Copy your API key (starts with `zk_`)

### Step 2: Choose Your Language

<details>
<summary><b>Python</b></summary>

```bash
# Install the client
pip install zakera-client
```

```python
import asyncio
from zakera import ZakeraClient

async def main():
    client = ZakeraClient(api_key="your-api-key")
    
    response = await client.chat.send(
        message="Explain quantum computing in simple terms",
        model="gemini-1.5-flash"  # Fast and affordable
    )
    
    print(f"AI: {response.content}")
    print(f"Cost: ${response.cost:.6f}")

if __name__ == "__main__":
    asyncio.run(main())
```

</details>

<details>
<summary><b>JavaScript/TypeScript</b></summary>

```bash
# Install the SDK
npm install zakera-sdk
# or
yarn add zakera-sdk
```

```javascript
import { ZakeraClient } from 'zakera-sdk';

const client = new ZakeraClient({
  apiKey: process.env.ZAKERA_API_KEY
});

const response = await client.chat.send({
  message: 'Explain quantum computing in simple terms',
  model: 'gemini-1.5-flash'
});

console.log('AI:', response.content);
console.log('Cost: $' + response.cost.toFixed(6));
```

</details>

<details>
<summary><b>cURL</b></summary>

```bash
curl -X POST https://api.zakera.app/v1/chat/send \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Explain quantum computing in simple terms",
    "model": "gemini-1.5-flash"
  }'
```

</details>

### Step 3: Try Streaming

For real-time responses:

```python
async for chunk in client.chat.stream(
    message="Write a short story about AI",
    model="gpt-4-turbo"
):
    print(chunk.content, end="", flush=True)
```

## 15-Minute Tutorial

### Build a Simple Chatbot

```python
import asyncio
from zakera import ZakeraClient

class SimpleChatbot:
    def __init__(self, api_key: str):
        self.client = ZakeraClient(api_key=api_key)
        self.conversation_id = None
    
    async def start(self):
        # Create a new conversation
        conv = await self.client.conversations.create(
            title="My First Chatbot"
        )
        self.conversation_id = conv.id
        print("Chatbot started! Type 'quit' to exit.\n")
    
    async def chat(self, message: str) -> str:
        response = await self.client.chat.send(
            message=message,
            conversation_id=self.conversation_id,
            model="gemini-1.5-flash"
        )
        return response.content
    
    async def run(self):
        await self.start()
        
        while True:
            # Get user input
            user_input = input("You: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'bye']:
                print("Goodbye!")
                break
            
            if not user_input:
                continue
            
            # Get AI response
            response = await self.chat(user_input)
            print(f"AI: {response}\n")

# Run the chatbot
if __name__ == "__main__":
    bot = SimpleChatbot(api_key="your-api-key")
    asyncio.run(bot.run())
```

## Next Steps

- 📚 [Full API Guide](api-integration-guide.md)
- 🔐 [Authentication Guide](authentication.md)
- 🎯 [Real-World Examples](use-cases/)
- 🚀 [Production Deployment](deployment.md)
- 🤝 [Join our Discord](https://discord.gg/zakera)

## Common Issues

### Authentication Error

```
Error: Invalid API key
```

**Solution**: Verify your API key at https://zakera.app/dashboard/api-keys

### Rate Limit Exceeded

```
Error: Rate limit exceeded. Retry after 30s
```

**Solution**: Implement retry logic or upgrade your plan

### Model Not Found

```
Error: Model 'invalid-model' not found
```

**Solution**: Check available models with `GET /v1/models`

## Need Help?

- 💬 [Discord Community](https://discord.gg/zakera)
- 📧 Email: support@zakera.app
- 📖 [Documentation](https://docs.zakera.app)
- 🐛 [Report Issues](https://github.com/itsmepraks/zakera/issues)
