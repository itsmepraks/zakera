"""
Enhanced Conversation Memory System with Summarization and Context Optimization

Features:
- Automatic conversation summarization for long conversations
- Hierarchical memory (short-term, long-term, summaries)
- Smart context window optimization
- Token-efficient memory compaction
- Better persistence strategies
- Memory importance scoring
"""

from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import tiktoken
import json
import hashlib
from sqlalchemy.orm import Session
from sqlalchemy import func


class MemoryImportance(Enum):
    """Importance levels for memory entries"""
    CRITICAL = 1.0  # Must keep (user preferences, important facts)
    HIGH = 0.8      # Very relevant
    MEDIUM = 0.5    # Moderately relevant
    LOW = 0.2       # Can be summarized/dropped
    MINIMAL = 0.1   # First to be removed


class SummarizationStrategy(Enum):
    """Strategies for summarizing conversations"""
    NONE = "none"
    SLIDING_WINDOW = "sliding_window"  # Summarize old messages
    HIERARCHICAL = "hierarchical"      # Multi-level summaries
    ADAPTIVE = "adaptive"              # Context-aware summarization


@dataclass
class ConversationTurn:
    """Enhanced conversation turn with metadata"""
    role: str
    content: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict = field(default_factory=dict)
    token_count: int = 0
    importance: float = 0.5
    turn_id: Optional[str] = None
    is_summarized: bool = False
    
    def __post_init__(self):
        if not self.turn_id:
            self.turn_id = self._generate_id()
    
    def _generate_id(self) -> str:
        """Generate unique ID for this turn"""
        content = f"{self.role}:{self.content}:{self.timestamp}"
        return hashlib.md5(content.encode()).hexdigest()[:16]


@dataclass
class ConversationSummary:
    """Summary of a conversation segment"""
    summary_text: str
    turn_ids: List[str]
    start_timestamp: str
    end_timestamp: str
    token_count: int
    compression_ratio: float  # Original tokens / Summary tokens
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class EnhancedConversationMemory:
    """
    Enhanced memory system with summarization and smart context management
    """
    
    def __init__(
        self,
        max_tokens: int = 4000,
        max_turns: int = 100,
        system_prompt: Optional[str] = None,
        model: str = "gpt-4",
        conversation_id: Optional[str] = None,
        db: Optional[Session] = None,
        summarization_strategy: SummarizationStrategy = SummarizationStrategy.ADAPTIVE,
        summary_threshold: int = 10,  # Summarize when > N turns old
        min_compression_ratio: float = 0.3  # Target compression
    ):
        self.max_tokens = max_tokens
        self.max_turns = max_turns
        self.system_prompt = system_prompt or "You are a helpful AI assistant."
        self.model = model
        self.conversation_id = conversation_id
        self.db = db
        self.summarization_strategy = summarization_strategy
        self.summary_threshold = summary_threshold
        self.min_compression_ratio = min_compression_ratio
        
        # Memory storage
        self.turns: List[ConversationTurn] = []
        self.summaries: List[ConversationSummary] = []
        self.important_facts: List[str] = []  # Key facts to always include
        
        # Context window management
        self.short_term_window = 5  # Last N turns always included
        self.reserved_tokens = 500  # Reserve for response
        
        # Token encoder
        try:
            self.encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            self.encoding = tiktoken.get_encoding("cl100k_base")
        
        # Load from database if available
        if conversation_id and db:
            self._load_from_db()
    
    def _load_from_db(self):
        """Load conversation history and summaries from database"""
        if not self.db or not self.conversation_id:
            return
        
        try:
            from src.api.models import Message, Conversation
            
            # Load conversation metadata
            conversation = self.db.query(Conversation).filter(
                Conversation.id == self.conversation_id
            ).first()
            
            if conversation:
                self.system_prompt = conversation.system_prompt or self.system_prompt
                self.model = conversation.model_name or self.model
                
                # Load summaries if stored in metadata
                if conversation.metadata and "summaries" in conversation.metadata:
                    self.summaries = [
                        ConversationSummary(**s) 
                        for s in conversation.metadata["summaries"]
                    ]
                
                if conversation.metadata and "important_facts" in conversation.metadata:
                    self.important_facts = conversation.metadata["important_facts"]
                
                # Load messages
                messages = self.db.query(Message).filter(
                    Message.conversation_id == self.conversation_id
                ).order_by(Message.created_at).all()
                
                for msg in messages:
                    if msg.role != "system":
                        turn = ConversationTurn(
                            role=msg.role,
                            content=msg.content,
                            timestamp=msg.created_at.isoformat() if msg.created_at else datetime.utcnow().isoformat(),
                            metadata=msg.metadata or {},
                            token_count=msg.tokens_used or 0,
                            importance=msg.metadata.get("importance", 0.5) if msg.metadata else 0.5,
                            turn_id=str(msg.id),
                            is_summarized=msg.metadata.get("is_summarized", False) if msg.metadata else False
                        )
                        self.turns.append(turn)
                        
        except Exception as e:
            print(f"Error loading conversation from database: {e}")
    
    def _save_to_db(self, role: str, content: str, metadata: Optional[Dict] = None) -> Optional[Any]:
        """Save a message to the database with enhanced metadata"""
        if not self.db or not self.conversation_id:
            return None
        
        try:
            from src.api.models import Message, Conversation
            
            # Count tokens
            token_count = len(self.encoding.encode(content))
            
            # Enhanced metadata
            enhanced_metadata = metadata or {}
            enhanced_metadata.update({
                "importance": self._calculate_importance(role, content),
                "token_count": token_count,
                "is_summarized": False
            })
            
            # Create message
            message = Message(
                conversation_id=self.conversation_id,
                role=role,
                content=content,
                model_name=self.model,
                tokens_used=token_count,
                metadata=enhanced_metadata
            )
            
            self.db.add(message)
            
            # Update conversation metadata
            conversation = self.db.query(Conversation).filter(
                Conversation.id == self.conversation_id
            ).first()
            
            if conversation:
                conversation.message_count = (conversation.message_count or 0) + 1
                conversation.last_message_at = func.now()
                conversation.updated_at = func.now()
                
                # Save summaries and important facts
                if not conversation.metadata:
                    conversation.metadata = {}
                
                conversation.metadata["summaries"] = [
                    {
                        "summary_text": s.summary_text,
                        "turn_ids": s.turn_ids,
                        "start_timestamp": s.start_timestamp,
                        "end_timestamp": s.end_timestamp,
                        "token_count": s.token_count,
                        "compression_ratio": s.compression_ratio,
                        "created_at": s.created_at
                    }
                    for s in self.summaries
                ]
                conversation.metadata["important_facts"] = self.important_facts
            
            self.db.commit()
            self.db.refresh(message)
            
            return message
        except Exception as e:
            print(f"Error saving message to database: {e}")
            self.db.rollback()
            return None
    
    def _calculate_importance(self, role: str, content: str) -> float:
        """Calculate importance score for a message"""
        importance = MemoryImportance.MEDIUM.value
        
        content_lower = content.lower()
        
        # Higher importance for specific keywords
        critical_keywords = [
            "my name is", "i am", "i prefer", "remember", "important",
            "don't forget", "always", "never", "must", "require"
        ]
        
        high_keywords = [
            "like", "dislike", "want", "need", "should", "would"
        ]
        
        if any(keyword in content_lower for keyword in critical_keywords):
            importance = MemoryImportance.CRITICAL.value
        elif any(keyword in content_lower for keyword in high_keywords):
            importance = MemoryImportance.HIGH.value
        
        # User messages generally more important than assistant
        if role == "user":
            importance *= 1.2
        
        # Questions are important
        if "?" in content:
            importance *= 1.1
        
        # Long messages might be more important
        if len(content) > 500:
            importance *= 1.15
        
        return min(importance, 1.0)
    
    def add_turn(
        self, 
        role: str, 
        content: str, 
        metadata: Optional[Dict] = None,
        importance: Optional[float] = None
    ):
        """Add a new conversation turn with enhanced tracking"""
        token_count = len(self.encoding.encode(content))
        
        turn = ConversationTurn(
            role=role,
            content=content,
            metadata=metadata or {},
            token_count=token_count,
            importance=importance or self._calculate_importance(role, content)
        )
        
        self.turns.append(turn)
        
        # Extract important facts
        self._extract_important_facts(turn)
        
        # Save to database
        self._save_to_db(role, content, metadata)
        
        # Check if summarization needed
        if self._should_summarize():
            self._create_summary()
    
    def _extract_important_facts(self, turn: ConversationTurn):
        """Extract important facts from a turn"""
        if turn.importance >= MemoryImportance.CRITICAL.value:
            content_lower = turn.content.lower()
            
            # Extract name
            if "my name is" in content_lower:
                parts = turn.content.split("my name is", 1)
                if len(parts) > 1:
                    name = parts[1].split()[0].strip().strip('.,!?')
                    fact = f"User's name: {name}"
                    if fact not in self.important_facts:
                        self.important_facts.append(fact)
            
            # Extract preferences
            for phrase in ["i prefer", "i like", "i always", "i never"]:
                if phrase in content_lower:
                    if turn.content not in self.important_facts:
                        self.important_facts.append(turn.content)
                    break
    
    def _should_summarize(self) -> bool:
        """Determine if summarization should occur"""
        if self.summarization_strategy == SummarizationStrategy.NONE:
            return False
        
        # Summarize if we have many old turns
        if len(self.turns) > self.short_term_window + self.summary_threshold:
            return True
        
        # Summarize if token count exceeds threshold
        total_tokens = sum(t.token_count for t in self.turns)
        if total_tokens > self.max_tokens * 0.8:
            return True
        
        return False
    
    def _create_summary(self, provider=None):
        """Create a summary of older conversation turns"""
        if len(self.turns) <= self.short_term_window:
            return
        
        # Identify turns to summarize (exclude recent and already summarized)
        recent_turns = self.turns[-self.short_term_window:]
        old_turns = [t for t in self.turns[:-self.short_term_window] if not t.is_summarized]
        
        if len(old_turns) < 3:
            return  # Not enough to summarize
        
        # Separate by importance
        important_turns = [t for t in old_turns if t.importance >= MemoryImportance.HIGH.value]
        regular_turns = [t for t in old_turns if t.importance < MemoryImportance.HIGH.value]
        
        # Summarize regular turns
        if regular_turns:
            summary_text = self._generate_summary_text(regular_turns, provider)
            
            if summary_text:
                turn_ids = [t.turn_id for t in regular_turns]
                original_tokens = sum(t.token_count for t in regular_turns)
                summary_tokens = len(self.encoding.encode(summary_text))
                
                summary = ConversationSummary(
                    summary_text=summary_text,
                    turn_ids=turn_ids,
                    start_timestamp=regular_turns[0].timestamp,
                    end_timestamp=regular_turns[-1].timestamp,
                    token_count=summary_tokens,
                    compression_ratio=summary_tokens / original_tokens if original_tokens > 0 else 1.0
                )
                
                self.summaries.append(summary)
                
                # Mark turns as summarized
                for turn in regular_turns:
                    turn.is_summarized = True
                
                # Remove summarized low-importance turns
                low_importance_turns = [
                    t for t in regular_turns 
                    if t.importance < MemoryImportance.MEDIUM.value
                ]
                for turn in low_importance_turns:
                    if turn in self.turns:
                        self.turns.remove(turn)
    
    def _generate_summary_text(self, turns: List[ConversationTurn], provider=None) -> str:
        """Generate summary text for a list of turns"""
        # Simple extraction-based summary for now
        # In production, you'd use the LLM provider here
        
        if not turns:
            return ""
        
        # Extract key points
        key_points = []
        current_topic = None
        
        for turn in turns:
            content = turn.content[:200]  # First 200 chars
            
            # User questions are important
            if turn.role == "user" and "?" in turn.content:
                key_points.append(f"User asked: {content}")
            
            # High importance turns
            if turn.importance >= MemoryImportance.HIGH.value:
                key_points.append(f"{turn.role}: {content}")
        
        # Format summary
        if key_points:
            summary = f"Summary of conversation ({turns[0].timestamp} to {turns[-1].timestamp}):\n"
            summary += "\n".join(f"- {point}" for point in key_points[:5])
            return summary
        
        # Fallback: basic summary
        user_turns = [t for t in turns if t.role == "user"]
        assistant_turns = [t for t in turns if t.role == "assistant"]
        
        return (
            f"Previous conversation segment ({len(turns)} messages): "
            f"{len(user_turns)} user messages, {len(assistant_turns)} assistant responses. "
            f"Topics discussed include general conversation."
        )
    
    async def _generate_summary_with_llm(
        self, 
        turns: List[ConversationTurn],
        provider
    ) -> str:
        """Generate summary using LLM (async method for production use)"""
        # Build prompt for summarization
        conversation_text = "\n".join([
            f"{turn.role}: {turn.content}"
            for turn in turns
        ])
        
        prompt = f"""Summarize the following conversation segment concisely, preserving key information, decisions, and context:

{conversation_text}

Provide a brief summary (2-3 sentences) that captures the essential information."""
        
        try:
            # Use provider to generate summary
            if provider:
                response = await provider.generate(
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=200,
                    temperature=0.3
                )
                return response.get("content", "")
        except Exception as e:
            print(f"Error generating LLM summary: {e}")
        
        # Fallback to extraction-based
        return self._generate_summary_text(turns, provider)
    
    def get_messages(
        self, 
        include_system: bool = True,
        optimize_context: bool = True
    ) -> List[Dict[str, str]]:
        """
        Get messages with smart context window optimization
        
        Priority:
        1. System prompt
        2. Important facts
        3. Summaries
        4. Recent turns (short-term window)
        5. High-importance older turns
        6. Regular older turns (if space available)
        """
        messages = []
        
        # 1. System prompt
        if include_system and self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        
        # Calculate available tokens
        available_tokens = self.max_tokens - self.reserved_tokens
        current_tokens = self._count_tokens(messages)
        
        # 2. Add important facts as system context
        if self.important_facts and optimize_context:
            facts_text = "Important context:\n" + "\n".join(f"- {fact}" for fact in self.important_facts)
            facts_msg = {"role": "system", "content": facts_text}
            facts_tokens = self._count_tokens([facts_msg])
            
            if current_tokens + facts_tokens <= available_tokens:
                messages.append(facts_msg)
                current_tokens += facts_tokens
        
        # 3. Add summaries
        for summary in self.summaries:
            if optimize_context:
                summary_msg = {"role": "system", "content": summary.summary_text}
                summary_tokens = self._count_tokens([summary_msg])
                
                if current_tokens + summary_tokens <= available_tokens:
                    messages.append(summary_msg)
                    current_tokens += summary_tokens
        
        # 4. Add recent turns (short-term window) - always include
        recent_turns = self.turns[-self.short_term_window:]
        recent_messages = []
        
        for turn in recent_turns:
            if not turn.is_summarized:
                turn_msg = {"role": turn.role, "content": turn.content}
                recent_messages.append(turn_msg)
        
        recent_tokens = self._count_tokens(recent_messages)
        
        # 5. Add high-importance older turns
        older_turns = self.turns[:-self.short_term_window] if len(self.turns) > self.short_term_window else []
        important_older = [
            t for t in older_turns 
            if t.importance >= MemoryImportance.HIGH.value and not t.is_summarized
        ]
        important_older.sort(key=lambda t: t.importance, reverse=True)
        
        for turn in important_older:
            turn_msg = {"role": turn.role, "content": turn.content}
            turn_tokens = self._count_tokens([turn_msg])
            
            if current_tokens + turn_tokens + recent_tokens <= available_tokens:
                messages.append(turn_msg)
                current_tokens += turn_tokens
        
        # 6. Add recent messages
        messages.extend(recent_messages)
        
        return messages
    
    def _count_tokens(self, messages: List[Dict[str, str]]) -> int:
        """Count tokens in messages with proper formatting overhead"""
        num_tokens = 0
        for message in messages:
            # Message formatting overhead
            num_tokens += 4
            for key, value in message.items():
                num_tokens += len(self.encoding.encode(str(value)))
                if key == "name":
                    num_tokens += -1
        num_tokens += 2  # Priming tokens
        return num_tokens
    
    def get_context_stats(self) -> Dict:
        """Get detailed statistics about context usage"""
        total_turns = len(self.turns)
        summarized_turns = sum(1 for t in self.turns if t.is_summarized)
        active_turns = total_turns - summarized_turns
        
        messages = self.get_messages()
        token_count = self._count_tokens(messages)
        token_usage = token_count / self.max_tokens if self.max_tokens > 0 else 0
        
        return {
            "total_turns": total_turns,
            "active_turns": active_turns,
            "summarized_turns": summarized_turns,
            "summaries_count": len(self.summaries),
            "important_facts_count": len(self.important_facts),
            "current_messages": len(messages),
            "token_count": token_count,
            "max_tokens": self.max_tokens,
            "token_usage_percent": round(token_usage * 100, 2),
            "available_tokens": self.max_tokens - token_count,
            "compression_ratio": self._calculate_overall_compression(),
            "strategy": self.summarization_strategy.value
        }
    
    def _calculate_overall_compression(self) -> float:
        """Calculate overall compression ratio"""
        if not self.summaries:
            return 1.0
        
        total_original = sum(
            sum(
                t.token_count for t in self.turns 
                if t.turn_id in s.turn_ids
            )
            for s in self.summaries
        )
        
        total_summary = sum(s.token_count for s in self.summaries)
        
        if total_original == 0:
            return 1.0
        
        return total_summary / total_original
    
    def optimize_memory(self, aggressive: bool = False):
        """
        Optimize memory by creating summaries and removing old content
        
        Args:
            aggressive: If True, more aggressive optimization
        """
        if aggressive:
            # Lower thresholds for aggressive optimization
            old_threshold = self.summary_threshold
            self.summary_threshold = max(5, self.summary_threshold // 2)
        
        # Create summaries
        while self._should_summarize():
            self._create_summary()
        
        # Remove very old, low-importance, summarized turns
        if aggressive:
            cutoff_date = datetime.utcnow() - timedelta(hours=24)
            self.turns = [
                t for t in self.turns
                if not (
                    t.is_summarized 
                    and t.importance < MemoryImportance.MEDIUM.value
                    and datetime.fromisoformat(t.timestamp) < cutoff_date
                )
            ]
        
        if aggressive:
            self.summary_threshold = old_threshold
    
    def clear_old_summaries(self, keep_recent: int = 5):
        """Keep only the most recent summaries"""
        if len(self.summaries) > keep_recent:
            self.summaries = self.summaries[-keep_recent:]
    
    def export(self) -> Dict:
        """Export conversation for storage"""
        return {
            "turns": [
                {
                    "role": turn.role,
                    "content": turn.content,
                    "timestamp": turn.timestamp,
                    "metadata": turn.metadata,
                    "token_count": turn.token_count,
                    "importance": turn.importance,
                    "turn_id": turn.turn_id,
                    "is_summarized": turn.is_summarized
                }
                for turn in self.turns
            ],
            "summaries": [
                {
                    "summary_text": s.summary_text,
                    "turn_ids": s.turn_ids,
                    "start_timestamp": s.start_timestamp,
                    "end_timestamp": s.end_timestamp,
                    "token_count": s.token_count,
                    "compression_ratio": s.compression_ratio,
                    "created_at": s.created_at
                }
                for s in self.summaries
            ],
            "important_facts": self.important_facts,
            "metadata": {
                "max_tokens": self.max_tokens,
                "max_turns": self.max_turns,
                "strategy": self.summarization_strategy.value,
                "model": self.model
            }
        }
    
    @classmethod
    def from_export(cls, data: Dict, **kwargs) -> "EnhancedConversationMemory":
        """Restore conversation from exported data"""
        memory = cls(**kwargs)
        
        # Restore turns
        for turn_data in data.get("turns", []):
            turn = ConversationTurn(**turn_data)
            memory.turns.append(turn)
        
        # Restore summaries
        for summary_data in data.get("summaries", []):
            summary = ConversationSummary(**summary_data)
            memory.summaries.append(summary)
        
        # Restore important facts
        memory.important_facts = data.get("important_facts", [])
        
        return memory
    
    def get_summary(self) -> Dict:
        """Get comprehensive conversation summary"""
        stats = self.get_context_stats()
        
        return {
            "conversation_id": self.conversation_id,
            "total_turns": stats["total_turns"],
            "active_turns": stats["active_turns"],
            "user_turns": sum(1 for t in self.turns if t.role == "user"),
            "assistant_turns": sum(1 for t in self.turns if t.role == "assistant"),
            "summaries_count": stats["summaries_count"],
            "important_facts_count": stats["important_facts_count"],
            "token_usage": f"{stats['token_usage_percent']}%",
            "compression_ratio": stats["compression_ratio"],
            "first_turn": self.turns[0].timestamp if self.turns else None,
            "last_turn": self.turns[-1].timestamp if self.turns else None,
            "memory_health": self._assess_memory_health()
        }
    
    def _assess_memory_health(self) -> str:
        """Assess the health of memory management"""
        stats = self.get_context_stats()
        usage = stats["token_usage_percent"]
        
        if usage < 50:
            return "excellent"
        elif usage < 70:
            return "good"
        elif usage < 85:
            return "moderate"
        else:
            return "needs_optimization"


# ---------------------------------------------------------------------------
# ConversationSummarizer
# ---------------------------------------------------------------------------


class ConversationSummarizer:
    """
    Standalone utility for automatic context compression via LLM-driven
    conversation summarization.

    This class complements ``EnhancedConversationMemory`` by providing a
    high-level async interface that:

    1. Inspects a message list and counts its tokens.
    2. Triggers summarization only when the token count exceeds
       ``max_tokens_threshold``.
    3. Delegates to the injected LLM provider for abstractive summary
       generation, falling back to an extractive heuristic when no provider
       is available.

    Usage::

        summarizer = ConversationSummarizer(
            provider=my_openai_provider,
            max_tokens_threshold=3000,
            model="gpt-4",
        )

        compressed = await summarizer.summarize_if_needed(messages)
        # `compressed` is either the original list (under threshold) or a
        # condensed list with a summary injected as the first system message.
    """

    def __init__(
        self,
        provider: Optional[Any] = None,
        max_tokens_threshold: int = 2000,
        model: str = "gpt-4",
        summary_max_tokens: int = 300,
        summary_temperature: float = 0.3,
        preserve_last_n_turns: int = 4,
    ) -> None:
        """
        Initialise the summarizer.

        Args:
            provider: An async LLM provider instance that exposes a
                ``generate(messages, max_tokens, temperature)`` coroutine.
                If ``None``, an extractive fallback is used.
            max_tokens_threshold: Token count above which summarization is
                triggered.  Defaults to ``2000``.
            model: Tiktoken model name used for token counting.
            summary_max_tokens: Maximum tokens the LLM may use for the
                generated summary.
            summary_temperature: Sampling temperature for summary generation
                (lower = more deterministic).
            preserve_last_n_turns: Number of recent turns to always keep
                verbatim at the end of the compressed message list.
        """
        self.provider = provider
        self.max_tokens_threshold = max_tokens_threshold
        self.summary_max_tokens = summary_max_tokens
        self.summary_temperature = summary_temperature
        self.preserve_last_n_turns = preserve_last_n_turns

        try:
            self._encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            self._encoding = tiktoken.get_encoding("cl100k_base")

    # ------------------------------------------------------------------ #
    # Token counting                                                       #
    # ------------------------------------------------------------------ #

    def _count_tokens(self, messages: List[Dict[str, str]]) -> int:
        """
        Estimate token consumption for a list of chat messages.

        Applies the standard OpenAI per-message overhead (4 tokens per
        message) plus 2 priming tokens so estimates are consistent with
        ``tiktoken`` chat-completion accounting.

        Args:
            messages: List of ``{"role": ..., "content": ...}`` dicts.

        Returns:
            Estimated total token count.
        """
        total = 2  # priming tokens
        for msg in messages:
            total += 4  # per-message overhead
            for value in msg.values():
                total += len(self._encoding.encode(str(value)))
        return total

    # ------------------------------------------------------------------ #
    # Prompt construction                                                  #
    # ------------------------------------------------------------------ #

    def _build_summary_prompt(self, messages: List[Dict[str, str]]) -> str:
        """
        Build the instruction prompt sent to the LLM for summarization.

        The prompt instructs the model to produce a concise, neutral-voice
        summary that preserves decisions, preferences, and factual details
        while discarding filler.

        Args:
            messages: The conversation slice to be summarized (system
                      messages are excluded from the transcript body).

        Returns:
            A single string containing the full summarization prompt.
        """
        # Exclude system messages from the transcript body; include only
        # the human/assistant dialogue turns for clarity.
        dialogue_lines: List[str] = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if role == "system":
                continue
            label = "User" if role == "user" else "Assistant"
            dialogue_lines.append(f"{label}: {content}")

        transcript = "\n".join(dialogue_lines)

        return (
            "You are a precise conversation summarizer. "
            "Summarize the following conversation excerpt in 3–5 sentences. "
            "Preserve: key decisions, user preferences, important facts, and "
            "any unresolved questions. Omit greetings and filler.\n\n"
            f"--- Conversation ---\n{transcript}\n--- End ---\n\n"
            "Summary:"
        )

    # ------------------------------------------------------------------ #
    # Summarization helpers                                                #
    # ------------------------------------------------------------------ #

    async def _summarize_with_llm(self, messages: List[Dict[str, str]]) -> str:
        """
        Request an abstractive summary from the configured LLM provider.

        Falls back to ``_extractive_summary`` on any error or if no
        provider has been configured.

        Args:
            messages: The conversation slice to summarize.

        Returns:
            A summary string.
        """
        if self.provider is None:
            return self._extractive_summary(messages)

        prompt = self._build_summary_prompt(messages)
        try:
            response = await self.provider.generate(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self.summary_max_tokens,
                temperature=self.summary_temperature,
            )
            summary = response.get("content", "").strip()
            if summary:
                return summary
        except Exception as exc:  # noqa: BLE001
            # Log but do not raise — fall through to extractive fallback.
            import logging
            logging.getLogger(__name__).warning(
                "ConversationSummarizer LLM call failed (%s); using extractive fallback.",
                exc,
            )

        return self._extractive_summary(messages)

    @staticmethod
    def _extractive_summary(messages: List[Dict[str, str]]) -> str:
        """
        Build a lightweight extractive summary when no LLM is available.

        Picks the first sentence of each user turn (up to five turns) and
        wraps them in a compact summary string.

        Args:
            messages: The conversation slice to summarize.

        Returns:
            A plain-text extractive summary.
        """
        snippets: List[str] = []
        for msg in messages:
            if msg.get("role") == "user":
                content = msg.get("content", "")
                # Take up to the first 120 characters / first sentence.
                first_sentence = content.split(".")[0][:120].strip()
                if first_sentence:
                    snippets.append(first_sentence)
            if len(snippets) >= 5:
                break

        if not snippets:
            return "Earlier conversation context has been compressed."

        joined = "; ".join(snippets)
        return f"[Summary of earlier context] The user discussed: {joined}."

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    async def summarize_if_needed(
        self,
        messages: List[Dict[str, str]],
    ) -> List[Dict[str, str]]:
        """
        Return a token-optimised version of *messages*.

        If the total token count is at or below ``max_tokens_threshold``,
        the original list is returned unchanged.  Otherwise the method:

        1. Splits the list into an *older* slice (everything except the
           last ``preserve_last_n_turns`` turns) and a *recent* slice.
        2. Generates a summary of the older slice via the LLM provider.
        3. Returns ``[system_summary_msg] + recent_slice``.

        Args:
            messages: Full conversation message list in
                      ``[{"role": ..., "content": ...}]`` format.

        Returns:
            The original list if under threshold, or a compressed list
            consisting of a summary system message followed by the most
            recent turns.
        """
        token_count = self._count_tokens(messages)

        if token_count <= self.max_tokens_threshold:
            # Nothing to do — return as-is.
            return messages

        # Separate system setup messages from dialogue turns.
        system_msgs = [m for m in messages if m.get("role") == "system"]
        dialogue_msgs = [m for m in messages if m.get("role") != "system"]

        # Guard: if there's nothing to compress, bail out.
        if len(dialogue_msgs) <= self.preserve_last_n_turns:
            return messages

        older_slice = dialogue_msgs[: -self.preserve_last_n_turns]
        recent_slice = dialogue_msgs[-self.preserve_last_n_turns :]

        summary_text = await self._summarize_with_llm(older_slice)

        summary_msg: Dict[str, str] = {
            "role": "system",
            "content": f"[Conversation summary]\n{summary_text}",
        }

        # Reconstruct: original system prompts → summary → recent turns.
        return system_msgs + [summary_msg] + recent_slice
