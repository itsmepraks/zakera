# Memory System

Zakera uses `ConversationMemory` (in `src/model/memory.py`) to manage context across conversation turns. It tracks what's been said, counts tokens, and trims history so the model stays within its context window.

## How it works

When a user sends a message, the memory object:

1. Loads the conversation history from the database
2. Adds the new user message
3. Trims older messages if the total exceeds the token budget
4. Passes the trimmed history to the model provider
5. Persists the assistant response back to the database

The token budget is configurable per conversation (default: 4000 tokens). Token counting uses `tiktoken` for accurate estimates.

## Usage in the chat route

```python
memory = ConversationMemory(
    max_tokens=4000,
    conversation_id=conversation.id,
    model=conversation.model_name,
    system_prompt=conversation.system_prompt,
    db=db,
)
memory.add_turn("user", user_message)

# Get trimmed message history for the provider
messages = memory.get_messages()
```

## What it stores

Each conversation turn has:
- `role` — user, assistant, system, or tool
- `content` — the message text
- `timestamp` — when it was sent
- `metadata` — additional data (tool calls, token counts, etc.)

Messages are persisted in the `messages` table (SQLAlchemy) and loaded from the database when the memory object is initialized with a conversation ID.

## Token management

The memory system counts tokens for each message and keeps a running total. When the total exceeds `max_tokens`, it drops the oldest non-system messages first, keeping the system prompt and recent turns intact.

## Where it's headed

The current memory system is basic — it trims by recency. Future work includes:
- Summarizing older turns instead of dropping them
- Importance scoring so critical context isn't lost
- Cross-session memory that carries user preferences and habits between conversations
