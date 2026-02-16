# Enhanced Conversation Memory System

## Overview

Zakera's enhanced conversation memory system provides intelligent context management for long conversations. It automatically summarizes older messages, extracts important facts, and optimizes the context window to ensure the AI always has relevant information while staying within token limits.

## Key Features

### 🧠 Hierarchical Memory
- **Short-term memory**: Recent conversation (always included)
- **Long-term memory**: Older messages with importance scoring
- **Summaries**: Compressed representations of past conversations
- **Important facts**: Critical information that's always remembered

### 📊 Smart Context Optimization
- Automatic token counting and management
- Priority-based message selection
- Token-efficient summarization
- Adaptive context window sizing

### 💾 Enhanced Persistence
- Summaries stored in conversation metadata
- Important facts preserved across sessions
- Full conversation export/import
- Memory health monitoring

### ⚙️ Configurable Strategies
- **None**: No summarization
- **Sliding Window**: Summarize old messages
- **Hierarchical**: Multi-level summaries
- **Adaptive**: Context-aware optimization (default)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Enhanced Memory System                    │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────┐    ┌──────────────────┐               │
│  │  Important Facts │    │    Summaries     │               │
│  │  - User prefs    │    │  - Compressed    │               │
│  │  - Key info      │    │  - Timestamped   │               │
│  │  - Always kept   │    │  - Efficient     │               │
│  └──────────────────┘    └──────────────────┘               │
│                                                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              Conversation Turns (Prioritized)         │  │
│  ├───────────────────────────────────────────────────────┤  │
│  │  [High Importance] → Always included if space         │  │
│  │  [Medium] → Included based on recency & space         │  │
│  │  [Low] → First to be summarized/dropped               │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │           Short-term Window (Recent 3-5)              │  │
│  │              Always included in context               │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## Usage Guide

### Basic Usage

```python
from src.model.memory_enhanced import EnhancedConversationMemory

# Create memory instance
memory = EnhancedConversationMemory(
    max_tokens=4000,
    conversation_id="conv_123",
    db=db_session
)

# Add conversation turns
memory.add_turn("user", "What is machine learning?")
memory.add_turn("assistant", "Machine learning is...")

# Get optimized context
messages = memory.get_messages(optimize_context=True)

# Get statistics
stats = memory.get_context_stats()
print(f"Token usage: {stats['token_usage_percent']}%")
print(f"Memory health: {stats['memory_health']}")
```

### Advanced Configuration

```python
from src.model.memory_enhanced import (
    EnhancedConversationMemory,
    SummarizationStrategy
)

memory = EnhancedConversationMemory(
    max_tokens=8000,                          # Higher token limit
    max_turns=200,                            # Keep more turns
    summarization_strategy=SummarizationStrategy.ADAPTIVE,
    summary_threshold=15,                      # Summarize after 15 old turns
    min_compression_ratio=0.3,                # Target 30% compression
    short_term_window=5                       # Keep last 5 turns always
)
```

### Manual Optimization

```python
# Check if optimization needed
if memory._should_summarize():
    memory.optimize_memory(aggressive=False)

# Aggressive optimization (removes more old content)
memory.optimize_memory(aggressive=True)

# Get results
stats = memory.get_context_stats()
print(f"Compression ratio: {stats['compression_ratio']:.2f}")
print(f"Summaries created: {stats['summaries_count']}")
```

---

## API Endpoints

### Get Memory Statistics

```http
GET /api/v1/conversations/{conversation_id}/memory/stats
```

**Response:**
```json
{
  "conversation_id": "conv_123",
  "total_turns": 45,
  "active_turns": 38,
  "summarized_turns": 7,
  "summaries_count": 2,
  "important_facts_count": 3,
  "token_count": 3200,
  "max_tokens": 4000,
  "token_usage_percent": 80.0,
  "available_tokens": 800,
  "compression_ratio": 0.35,
  "strategy": "adaptive",
  "memory_health": "good"
}
```

### Optimize Memory

```http
POST /api/v1/conversations/{conversation_id}/memory/optimize
Content-Type: application/json

{
  "aggressive": false,
  "min_turns": 10
}
```

**Response:**
```json
{
  "success": true,
  "message": "Memory optimized successfully. Created 2 new summaries.",
  "stats_before": { ... },
  "stats_after": { ... },
  "turns_removed": 5,
  "summaries_created": 2
}
```

### View Important Facts

```http
GET /api/v1/conversations/{conversation_id}/memory/facts
```

**Response:**
```json
{
  "conversation_id": "conv_123",
  "facts": [
    "User's name: Alice",
    "Prefers Python for coding",
    "Working on ML project"
  ],
  "total_count": 3
}
```

### View Summaries

```http
GET /api/v1/conversations/{conversation_id}/memory/summaries
```

**Response:**
```json
{
  "conversation_id": "conv_123",
  "summaries": [
    {
      "summary_text": "Discussion about Python basics...",
      "turn_count": 8,
      "start_timestamp": "2026-02-15T10:00:00Z",
      "end_timestamp": "2026-02-15T10:15:00Z",
      "token_count": 150,
      "compression_ratio": 0.3,
      "created_at": "2026-02-15T10:20:00Z"
    }
  ],
  "total_summaries": 1,
  "total_compressed_turns": 8,
  "average_compression": 0.3
}
```

### View Context Window

```http
GET /api/v1/conversations/{conversation_id}/memory/context?optimize=true
```

**Response:**
```json
{
  "conversation_id": "conv_123",
  "total_messages": 12,
  "breakdown": {
    "system": 3,
    "user": 5,
    "assistant": 4
  },
  "token_count": 2800,
  "max_tokens": 4000,
  "optimization_enabled": true,
  "messages": [ ... ],
  "stats": { ... }
}
```

### Update Memory Settings

```http
POST /api/v1/conversations/{conversation_id}/memory/settings
Content-Type: application/json

{
  "max_tokens": 8000,
  "max_turns": 150,
  "strategy": "adaptive",
  "summary_threshold": 20
}
```

### Export Memory

```http
GET /api/v1/conversations/{conversation_id}/memory/export
```

**Response:**
```json
{
  "conversation_id": "conv_123",
  "export_data": {
    "turns": [ ... ],
    "summaries": [ ... ],
    "important_facts": [ ... ],
    "metadata": { ... }
  },
  "file_size_estimate": 45678
}
```

---

## Importance Scoring

Messages are automatically scored based on multiple factors:

### Critical Importance (1.0)
- Contains: "my name is", "remember", "important", "don't forget"
- User preferences and requirements
- Personal information

### High Importance (0.8)
- Contains: "like", "dislike", "want", "need", "should"
- Questions from user
- Long, detailed messages

### Medium Importance (0.5)
- Regular conversation
- Standard questions and answers

### Low Importance (0.2)
- Short acknowledgments
- Filler content
- Already summarized information

---

## Summarization Strategies

### 1. None
```python
SummarizationStrategy.NONE
```
- No automatic summarization
- Simple truncation when needed
- Use for: Short conversations, debugging

### 2. Sliding Window
```python
SummarizationStrategy.SLIDING_WINDOW
```
- Summarizes oldest messages first
- Maintains fixed window of recent messages
- Use for: Standard conversations

### 3. Hierarchical
```python
SummarizationStrategy.HIERARCHICAL
```
- Multi-level summaries
- Summaries of summaries
- Use for: Very long conversations

### 4. Adaptive (Recommended)
```python
SummarizationStrategy.ADAPTIVE
```
- Context-aware optimization
- Balances recency and importance
- Adapts to conversation flow
- Use for: Production, general use

---

## Memory Optimization Tips

### For Long Conversations

1. **Enable adaptive strategy**:
   ```python
   strategy=SummarizationStrategy.ADAPTIVE
   ```

2. **Lower summary threshold**:
   ```python
   summary_threshold=10  # Summarize more aggressively
   ```

3. **Optimize periodically**:
   ```python
   if len(memory.turns) > 100:
       memory.optimize_memory(aggressive=True)
   ```

### For Token Efficiency

1. **Increase compression target**:
   ```python
   min_compression_ratio=0.2  # More aggressive compression
   ```

2. **Reduce short-term window**:
   ```python
   short_term_window=3  # Keep fewer recent messages
   ```

3. **Reserve tokens for response**:
   ```python
   reserved_tokens=1000  # Leave room for long responses
   ```

### For Important Conversations

1. **Increase max tokens**:
   ```python
   max_tokens=8000  # More context
   ```

2. **Keep more turns**:
   ```python
   max_turns=200
   ```

3. **Higher summary threshold**:
   ```python
   summary_threshold=20  # Less aggressive summarization
   ```

---

## Memory Health Monitoring

### Health Status Levels

| Status | Token Usage | Action |
|--------|-------------|--------|
| **Excellent** | < 50% | No action needed |
| **Good** | 50-70% | Monitor |
| **Moderate** | 70-85% | Consider optimization |
| **Needs Optimization** | > 85% | Optimize immediately |

### Monitoring Example

```python
# Get health status
stats = memory.get_context_stats()
health = stats['memory_health']

if health == 'needs_optimization':
    memory.optimize_memory(aggressive=True)
    print("Memory optimized")
elif health == 'moderate':
    print("Warning: Memory usage high")
else:
    print(f"Memory health: {health}")
```

---

## Best Practices

### 1. Set Appropriate Token Limits

```python
# For GPT-4 (8K context)
max_tokens=4000  # Leave room for response

# For GPT-4 Turbo (128K context)
max_tokens=64000  # Can be much larger

# For local models (varies)
max_tokens=2000  # Conservative
```

### 2. Use Important Facts

```python
# Manually add critical information
memory.important_facts.append("User is a Python developer")
memory.important_facts.append("Prefers detailed explanations")

# These will always be included in context
```

### 3. Periodic Optimization

```python
# Optimize every N turns
if len(memory.turns) % 50 == 0:
    memory.optimize_memory()
```

### 4. Monitor Token Usage

```python
stats = memory.get_context_stats()
usage = stats['token_usage_percent']

if usage > 90:
    # Increase max_tokens or optimize
    memory.optimize_memory(aggressive=True)
```

### 5. Export for Backup

```python
# Periodically export important conversations
if len(memory.turns) > 100:
    export_data = memory.export()
    # Save to file or backup storage
```

---

## Performance Metrics

### Token Efficiency

| Scenario | Before | After | Compression |
|----------|--------|-------|-------------|
| 50 turns, no optimization | 4500 | 4500 | 1.0x |
| 50 turns, with summaries | 4500 | 2800 | 1.6x |
| 100 turns, aggressive | 8000 | 3200 | 2.5x |

### Memory Usage

- **Active turn storage**: ~100 bytes per turn
- **Summary storage**: ~50 bytes per summary
- **Important facts**: ~50 bytes per fact
- **Metadata overhead**: ~1KB per conversation

### Performance

- **Add turn**: < 1ms
- **Get messages**: < 5ms (optimized)
- **Create summary**: 10-50ms (extraction-based)
- **Optimize memory**: 50-200ms

---

## Troubleshooting

### Issue: Token limit exceeded

```python
# Solution 1: Optimize memory
memory.optimize_memory(aggressive=True)

# Solution 2: Increase limit
memory.max_tokens = 8000

# Solution 3: Clear old summaries
memory.clear_old_summaries(keep_recent=3)
```

### Issue: Important context lost

```python
# Solution: Add to important facts
memory.important_facts.append("Critical context here")

# Or: Increase importance of specific messages
memory.add_turn("user", "Important info", importance=1.0)
```

### Issue: Too many summaries

```python
# Solution: Clear old summaries
memory.clear_old_summaries(keep_recent=5)

# Or: Adjust summary threshold
memory.summary_threshold = 20  # Less frequent
```

### Issue: Poor memory health

```python
# Check stats
stats = memory.get_context_stats()
print(f"Active turns: {stats['active_turns']}")
print(f"Token usage: {stats['token_usage_percent']}%")

# Optimize if needed
if stats['memory_health'] != 'excellent':
    memory.optimize_memory(aggressive=True)
```

---

## Examples

### Example 1: Basic Conversation

```python
memory = EnhancedConversationMemory()

# Add turns
memory.add_turn("user", "Hello!")
memory.add_turn("assistant", "Hi! How can I help?")
memory.add_turn("user", "What's the weather?")
memory.add_turn("assistant", "I need your location.")

# Get context
messages = memory.get_messages()
# Returns: [system, user, assistant, user, assistant]
```

### Example 2: Long Conversation with Summarization

```python
memory = EnhancedConversationMemory(
    max_tokens=2000,
    summary_threshold=10
)

# Simulate long conversation
for i in range(50):
    memory.add_turn("user", f"Question {i}")
    memory.add_turn("assistant", f"Answer {i}")

# Check results
stats = memory.get_context_stats()
print(f"Total turns: {stats['total_turns']}")
print(f"Active turns: {stats['active_turns']}")
print(f"Summaries: {stats['summaries_count']}")
print(f"Token usage: {stats['token_usage_percent']}%")
```

### Example 3: Important Facts Extraction

```python
memory = EnhancedConversationMemory()

# User provides personal info
memory.add_turn("user", "My name is Alice and I prefer Python")

# Facts automatically extracted
print(memory.important_facts)
# Output: ["User's name: Alice", "I prefer Python"]

# Get context - facts always included
messages = memory.get_messages()
# Facts appear as system message
```

### Example 4: Manual Optimization

```python
memory = EnhancedConversationMemory()

# Add many turns...
for i in range(100):
    memory.add_turn("user", f"Message {i}")

# Check health
stats = memory.get_context_stats()
if stats['memory_health'] != 'excellent':
    # Optimize
    memory.optimize_memory(aggressive=True)
    
    # Check improvement
    new_stats = memory.get_context_stats()
    print(f"Turns reduced: {stats['total_turns'] - new_stats['total_turns']}")
    print(f"Token usage: {new_stats['token_usage_percent']}%")
```

---

## Integration with Chat

```python
# In chat route
from src.model.memory_enhanced import EnhancedConversationMemory

@app.post("/chat")
async def chat(message: str, conversation_id: str, db: Session):
    # Load memory
    memory = EnhancedConversationMemory(
        conversation_id=conversation_id,
        db=db,
        summarization_strategy=SummarizationStrategy.ADAPTIVE
    )
    
    # Add user message
    memory.add_turn("user", message)
    
    # Get optimized context
    messages = memory.get_messages(optimize_context=True)
    
    # Call LLM
    response = await llm.generate(messages)
    
    # Add assistant response
    memory.add_turn("assistant", response["content"])
    
    # Return response with stats
    return {
        "response": response["content"],
        "memory_stats": memory.get_context_stats()
    }
```

---

## Future Enhancements

### Planned Features

1. **LLM-based Summarization**
   - Use LLM to generate high-quality summaries
   - Async summarization in background

2. **Semantic Clustering**
   - Group related messages
   - Topic-based memory organization

3. **Retrieval-Augmented Memory**
   - Vector embeddings for messages
   - Semantic search for relevant context

4. **Multi-modal Memory**
   - Support for images, files
   - Context from attachments

5. **Memory Sharing**
   - Share context between conversations
   - Cross-conversation facts

---

## References

- [Token Counting Best Practices](https://platform.openai.com/docs/guides/chat)
- [Context Window Optimization](https://help.openai.com/en/articles/4936856)
- [Conversation Design](https://www.nngroup.com/articles/chatbot-conversation-design/)

---

## Support

For issues or questions:
- GitHub Issues: [zakera/issues](https://github.com/itsmepraks/zakera/issues)
- Documentation: [docs/](https://github.com/itsmepraks/zakera/docs)

---

**Version**: 1.0.0  
**Last Updated**: February 2026  
**Status**: Production Ready
