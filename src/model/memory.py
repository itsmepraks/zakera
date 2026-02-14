from typing import List, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime
import tiktoken
from sqlalchemy.orm import Session

@dataclass
class ConversationTurn:
    role: str
    content: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict = field(default_factory=dict)

class ConversationMemory:
    """
    Manages conversation history with intelligent context window management
    and database persistence integration
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
        self.max_tokens = max_tokens
        self.max_turns = max_turns
        self.system_prompt = system_prompt or "You are a helpful AI assistant."
        self.model = model
        self.conversation_id = conversation_id
        self.db = db
        self.turns: List[ConversationTurn] = []
        
        try:
            self.encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            self.encoding = tiktoken.get_encoding("cl100k_base")
        
        # Load from database if conversation_id and db provided
        if conversation_id and db:
            self._load_from_db()
    
    def _load_from_db(self):
        """Load conversation history from database"""
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
                
                # Load messages
                messages = self.db.query(Message).filter(
                    Message.conversation_id == self.conversation_id
                ).order_by(Message.created_at).all()
                
                for msg in messages:
                    if msg.role != "system":  # Skip system messages as they're in system_prompt
                        self.turns.append(ConversationTurn(
                            role=msg.role,
                            content=msg.content,
                            timestamp=msg.created_at.isoformat() if msg.created_at else datetime.utcnow().isoformat(),
                            metadata=msg.metadata or {}
                        ))
        except Exception as e:
            print(f"Error loading conversation from database: {e}")
    
    def _save_to_db(self, role: str, content: str, metadata: Optional[Dict] = None):
        """Save a message to the database"""
        if not self.db or not self.conversation_id:
            return None
        
        try:
            from src.api.models import Message, Conversation
            from sqlalchemy import func
            
            # Create message
            message = Message(
                conversation_id=self.conversation_id,
                role=role,
                content=content,
                model_name=self.model,
                tokens_used=len(self.encoding.encode(content)),
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
            
            self.db.commit()
            self.db.refresh(message)
            
            return message
        except Exception as e:
            print(f"Error saving message to database: {e}")
            self.db.rollback()
            return None
    
    def add_turn(self, role: str, content: str, metadata: Optional[Dict] = None):
        """Add a new conversation turn and persist to database"""
        turn = ConversationTurn(
            role=role,
            content=content,
            metadata=metadata or {}
        )
        self.turns.append(turn)
        
        # Save to database if available
        self._save_to_db(role, content, metadata)
        
        # Trim if exceeds max turns
        if len(self.turns) > self.max_turns:
            self.turns = self.turns[-self.max_turns:]
    
    def get_messages(self, include_system: bool = True) -> List[Dict[str, str]]:
        """Get messages in API format with token management"""
        messages = []
        
        if include_system and self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        
        # Calculate token budget
        current_tokens = self._count_tokens([messages[0]]) if messages else 0
        
        # Add turns in reverse order (most recent first) until token limit
        included_turns = []
        for turn in reversed(self.turns):
            turn_message = {"role": turn.role, "content": turn.content}
            turn_tokens = self._count_tokens([turn_message])
            
            if current_tokens + turn_tokens <= self.max_tokens:
                included_turns.insert(0, turn_message)
                current_tokens += turn_tokens
            else:
                break
        
        messages.extend(included_turns)
        return messages
    
    def _count_tokens(self, messages: List[Dict[str, str]]) -> int:
        """Count tokens in messages"""
        num_tokens = 0
        for message in messages:
            # Rough approximation: 4 tokens per message overhead
            num_tokens += 4
            for key, value in message.items():
                num_tokens += len(self.encoding.encode(value))
        return num_tokens
    
    def get_summary(self) -> Dict:
        """Get conversation summary statistics"""
        return {
            "conversation_id": self.conversation_id,
            "total_turns": len(self.turns),
            "user_turns": sum(1 for t in self.turns if t.role == "user"),
            "assistant_turns": sum(1 for t in self.turns if t.role == "assistant"),
            "estimated_tokens": self._count_tokens(self.get_messages()),
            "first_turn": self.turns[0].timestamp if self.turns else None,
            "last_turn": self.turns[-1].timestamp if self.turns else None
        }
    
    def clear(self):
        """Clear all conversation turns (in memory only, database is preserved)"""
        self.turns = []
    
    def export(self) -> List[Dict]:
        """Export conversation for storage"""
        return [
            {
                "role": turn.role,
                "content": turn.content,
                "timestamp": turn.timestamp,
                "metadata": turn.metadata
            }
            for turn in self.turns
        ]
    
    @classmethod
    def from_export(cls, data: List[Dict], **kwargs) -> "ConversationMemory":
        """Restore conversation from exported data"""
        memory = cls(**kwargs)
        for turn_data in data:
            memory.add_turn(
                role=turn_data["role"],
                content=turn_data["content"],
                metadata=turn_data.get("metadata", {})
            )
        return memory
    
    @classmethod
    def from_conversation_id(
        cls, 
        conversation_id: str, 
        db: Session,
        max_tokens: int = 4000,
        max_turns: int = 50
    ) -> "ConversationMemory":
        """Create memory instance from existing conversation in database"""
        return cls(
            max_tokens=max_tokens,
            max_turns=max_turns,
            conversation_id=conversation_id,
            db=db
        )
    
    def update_conversation_stats(self, total_tokens: int = 0, total_cost: float = 0.0):
        """Update conversation statistics in database"""
        if not self.db or not self.conversation_id:
            return
        
        try:
            from src.api.models import Conversation
            
            conversation = self.db.query(Conversation).filter(
                Conversation.id == self.conversation_id
            ).first()
            
            if conversation:
                conversation.total_tokens = (conversation.total_tokens or 0) + total_tokens
                conversation.total_cost = (conversation.total_cost or 0.0) + total_cost
                self.db.commit()
        except Exception as e:
            print(f"Error updating conversation stats: {e}")
            self.db.rollback()
