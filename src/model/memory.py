"""Conversation memory management with database persistence.

This module handles conversation history, context window management, and
integration with database storage for persistent conversations.
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import tiktoken
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)


@dataclass
class ConversationTurn:
    """Represents a single turn in a conversation.
    
    Attributes:
        role: Message role (user, assistant, system)
        content: Message content
        timestamp: ISO format timestamp
        metadata: Additional metadata (model used, tokens, etc.)
    """
    role: str
    content: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert turn to dictionary representation."""
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "metadata": self.metadata
        }


class ConversationMemory:
    """
    Manages conversation history with intelligent context window management
    and database persistence integration.
    
    This class handles:
    - Conversation history storage and retrieval
    - Token counting and context window management
    - Database persistence integration
    - Automatic trimming of old messages
    - Conversation statistics and metadata
    """
    
    def __init__(
        self,
        max_tokens: int = 4000,
        max_turns: int = 50,
        system_prompt: Optional[str] = None,
        model: str = "gpt-4",
        conversation_id: Optional[str] = None,
        db: Optional[Session] = None
    ):
        """Initialize conversation memory.
        
        Args:
            max_tokens: Maximum tokens to include in context
            max_turns: Maximum number of conversation turns to keep
            system_prompt: System prompt for the conversation
            model: Model identifier for token encoding
            conversation_id: Database conversation ID for persistence
            db: SQLAlchemy database session
        """
        self.max_tokens = max_tokens
        self.max_turns = max_turns
        self.system_prompt = system_prompt or "You are a helpful AI assistant."
        self.model = model
        self.conversation_id = conversation_id
        self.db = db
        self.turns: List[ConversationTurn] = []
        
        # Initialize token encoder
        try:
            self.encoding = tiktoken.encoding_for_model(model)
            logger.debug(f"Initialized tiktoken encoder for model: {model}")
        except KeyError:
            logger.warning(
                f"Model '{model}' not found in tiktoken, using default encoder"
            )
            self.encoding = tiktoken.get_encoding("cl100k_base")
        
        # Load from database if conversation_id and db provided
        if conversation_id and db:
            self._load_from_db()
    
    def _load_from_db(self) -> None:
        """Load conversation history from database.
        
        Raises:
            Exception: Logs but does not raise on database errors
        """
        if not self.db or not self.conversation_id:
            logger.debug("No database session or conversation ID, skipping load")
            return
        
        try:
            from src.api.models import Message, Conversation
            
            # Load conversation metadata
            conversation = self.db.query(Conversation).filter(
                Conversation.id == self.conversation_id
            ).first()
            
            if not conversation:
                logger.warning(
                    f"Conversation not found in database: {self.conversation_id}"
                )
                return
            
            # Update settings from conversation
            self.system_prompt = conversation.system_prompt or self.system_prompt
            self.model = conversation.model_name or self.model
            
            # Load messages
            messages = self.db.query(Message).filter(
                Message.conversation_id == self.conversation_id
            ).order_by(Message.created_at).all()
            
            loaded_count = 0
            for msg in messages:
                if msg.role != "system":  # Skip system messages
                    self.turns.append(ConversationTurn(
                        role=msg.role,
                        content=msg.content,
                        timestamp=msg.created_at.isoformat() if msg.created_at else datetime.utcnow().isoformat(),
                        metadata=msg.metadata or {}
                    ))
                    loaded_count += 1
            
            logger.info(
                f"Loaded {loaded_count} messages for conversation {self.conversation_id}"
            )
            
        except Exception as e:
            logger.error(
                f"Error loading conversation from database: {e}",
                exc_info=True,
                extra={"conversation_id": self.conversation_id}
            )
    
    def _save_to_db(self, role: str, content: str, metadata: Optional[Dict] = None) -> Optional[Any]:
        """Save a message to the database.
        
        Args:
            role: Message role
            content: Message content
            metadata: Optional metadata
            
        Returns:
            Saved message object or None on error
        """
        if not self.db or not self.conversation_id:
            logger.debug("No database session or conversation ID, skipping save")
            return None
        
        try:
            from src.api.models import Message, Conversation
            from sqlalchemy import func
            
            # Calculate token count
            token_count = len(self.encoding.encode(content))
            
            # Create message
            message = Message(
                conversation_id=self.conversation_id,
                role=role,
                content=content,
                model_name=self.model,
                tokens_used=token_count,
                metadata=metadata or {}
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
                
                logger.debug(
                    f"Updated conversation {self.conversation_id}: "
                    f"message_count={conversation.message_count}, tokens={token_count}"
                )
            
            self.db.commit()
            self.db.refresh(message)
            
            logger.info(
                f"Saved message to database",
                extra={
                    "conversation_id": self.conversation_id,
                    "role": role,
                    "tokens": token_count
                }
            )
            
            return message
            
        except Exception as e:
            logger.error(
                f"Error saving message to database: {e}",
                exc_info=True,
                extra={
                    "conversation_id": self.conversation_id,
                    "role": role
                }
            )
            if self.db:
                self.db.rollback()
            return None
    
    def add_turn(self, role: str, content: str, metadata: Optional[Dict] = None) -> None:
        """Add a new conversation turn and persist to database.
        
        Args:
            role: Message role (user, assistant, system)
            content: Message content
            metadata: Optional metadata dictionary
        """
        if not content or not content.strip():
            logger.warning(f"Attempted to add empty turn with role: {role}")
            return
        
        turn = ConversationTurn(
            role=role,
            content=content.strip(),
            metadata=metadata or {}
        )
        self.turns.append(turn)
        
        logger.debug(
            f"Added turn to memory",
            extra={"role": role, "content_length": len(content)}
        )
        
        # Save to database if available
        self._save_to_db(role, content, metadata)
        
        # Trim if exceeds max turns
        if len(self.turns) > self.max_turns:
            removed = len(self.turns) - self.max_turns
            self.turns = self.turns[-self.max_turns:]
            logger.info(
                f"Trimmed {removed} old turns, keeping most recent {self.max_turns}"
            )
    
    def get_messages(self, include_system: bool = True) -> List[Dict[str, str]]:
        """Get messages in API format with token management.
        
        Automatically manages context window by including most recent messages
        that fit within the token budget.
        
        Args:
            include_system: Whether to include system prompt
            
        Returns:
            List of messages in API format [{"role": ..., "content": ...}]
        """
        messages: List[Dict[str, str]] = []
        
        # Add system prompt
        if include_system and self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        
        # Calculate token budget
        current_tokens = self._count_tokens([messages[0]]) if messages else 0
        
        # Add turns in reverse order (most recent first) until token limit
        included_turns: List[Dict[str, str]] = []
        trimmed_count = 0
        
        for turn in reversed(self.turns):
            turn_message = {"role": turn.role, "content": turn.content}
            turn_tokens = self._count_tokens([turn_message])
            
            if current_tokens + turn_tokens <= self.max_tokens:
                included_turns.insert(0, turn_message)
                current_tokens += turn_tokens
            else:
                trimmed_count += 1
        
        if trimmed_count > 0:
            logger.debug(
                f"Trimmed {trimmed_count} old messages to fit token budget of {self.max_tokens}"
            )
        
        messages.extend(included_turns)
        
        logger.debug(
            f"Prepared {len(messages)} messages ({current_tokens} tokens) for model"
        )
        
        return messages
    
    def _count_tokens(self, messages: List[Dict[str, str]]) -> int:
        """Count tokens in messages.
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            Total token count
        """
        num_tokens = 0
        for message in messages:
            # Rough approximation: 4 tokens per message overhead
            num_tokens += 4
            for key, value in message.items():
                try:
                    num_tokens += len(self.encoding.encode(str(value)))
                except Exception as e:
                    logger.warning(f"Error encoding message field '{key}': {e}")
                    # Fallback: rough estimation
                    num_tokens += len(str(value)) // 4
        
        return num_tokens
    
    def get_summary(self) -> Dict[str, Any]:
        """Get conversation summary statistics.
        
        Returns:
            Dictionary with conversation statistics
        """
        summary = {
            "conversation_id": self.conversation_id,
            "total_turns": len(self.turns),
            "user_turns": sum(1 for t in self.turns if t.role == "user"),
            "assistant_turns": sum(1 for t in self.turns if t.role == "assistant"),
            "estimated_tokens": self._count_tokens(self.get_messages()),
            "first_turn": self.turns[0].timestamp if self.turns else None,
            "last_turn": self.turns[-1].timestamp if self.turns else None,
            "model": self.model
        }
        
        logger.debug(f"Generated conversation summary: {summary}")
        return summary
    
    def clear(self) -> None:
        """Clear all conversation turns (in memory only, database is preserved)."""
        turns_cleared = len(self.turns)
        self.turns = []
        logger.info(
            f"Cleared {turns_cleared} turns from memory for conversation {self.conversation_id}"
        )
    
    def export(self) -> List[Dict[str, Any]]:
        """Export conversation for storage or transfer.
        
        Returns:
            List of turn dictionaries
        """
        exported = [
            {
                "role": turn.role,
                "content": turn.content,
                "timestamp": turn.timestamp,
                "metadata": turn.metadata
            }
            for turn in self.turns
        ]
        
        logger.debug(f"Exported {len(exported)} turns")
        return exported
    
    @classmethod
    def from_export(cls, data: List[Dict], **kwargs) -> "ConversationMemory":
        """Restore conversation from exported data.
        
        Args:
            data: List of exported turn dictionaries
            **kwargs: Additional arguments for ConversationMemory initialization
            
        Returns:
            New ConversationMemory instance with loaded data
        """
        memory = cls(**kwargs)
        
        for turn_data in data:
            memory.add_turn(
                role=turn_data.get("role", "user"),
                content=turn_data.get("content", ""),
                metadata=turn_data.get("metadata", {})
            )
        
        logger.info(f"Restored conversation with {len(data)} turns from export")
        return memory
    
    @classmethod
    def from_conversation_id(
        cls, 
        conversation_id: str, 
        db: Session,
        max_tokens: int = 4000,
        max_turns: int = 50
    ) -> "ConversationMemory":
        """Create memory instance from existing conversation in database.
        
        Args:
            conversation_id: Database conversation ID
            db: SQLAlchemy database session
            max_tokens: Maximum tokens for context
            max_turns: Maximum turns to keep
            
        Returns:
            ConversationMemory instance loaded from database
        """
        logger.info(f"Loading conversation from database: {conversation_id}")
        
        return cls(
            max_tokens=max_tokens,
            max_turns=max_turns,
            conversation_id=conversation_id,
            db=db
        )
    
    def update_conversation_stats(
        self, 
        total_tokens: int = 0, 
        total_cost: float = 0.0
    ) -> bool:
        """Update conversation statistics in database.
        
        Args:
            total_tokens: Total tokens used in this interaction
            total_cost: Cost of this interaction (USD)
            
        Returns:
            True if update successful, False otherwise
        """
        if not self.db or not self.conversation_id:
            logger.debug("No database session or conversation ID, skipping stats update")
            return False
        
        try:
            from src.api.models import Conversation
            
            conversation = self.db.query(Conversation).filter(
                Conversation.id == self.conversation_id
            ).first()
            
            if not conversation:
                logger.warning(
                    f"Conversation not found for stats update: {self.conversation_id}"
                )
                return False
            
            # Update statistics
            conversation.total_tokens = (conversation.total_tokens or 0) + total_tokens
            conversation.total_cost = (conversation.total_cost or 0.0) + total_cost
            
            self.db.commit()
            
            logger.info(
                f"Updated conversation stats",
                extra={
                    "conversation_id": self.conversation_id,
                    "tokens_added": total_tokens,
                    "cost_added": total_cost,
                    "total_tokens": conversation.total_tokens,
                    "total_cost": conversation.total_cost
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(
                f"Error updating conversation stats: {e}",
                exc_info=True,
                extra={"conversation_id": self.conversation_id}
            )
            if self.db:
                self.db.rollback()
            return False
    
    def get_token_count(self) -> int:
        """Get total token count for current context.
        
        Returns:
            Total number of tokens in current context
        """
        messages = self.get_messages()
        return self._count_tokens(messages)
    
    def can_add_tokens(self, additional_tokens: int) -> Tuple[bool, int]:
        """Check if additional tokens can fit in context window.
        
        Args:
            additional_tokens: Number of tokens to add
            
        Returns:
            Tuple of (can_fit, available_tokens)
        """
        current_tokens = self.get_token_count()
        available = self.max_tokens - current_tokens
        
        return (additional_tokens <= available, available)
