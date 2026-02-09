from typing import List, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime
import tiktoken

@dataclass
class ConversationTurn:
    role: str
    content: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict = field(default_factory=dict)

class ConversationMemory:
    """
    Manages conversation history with intelligent context window management
    """
    
    def __init__(
        self,
        max_tokens: int = 4000,
        max_turns: int = 50,
        system_prompt: Optional[str] = None,
        model: str = "gpt-4"
    ):
        self.max_tokens = max_tokens
        self.max_turns = max_turns
        self.system_prompt = system_prompt or "You are a helpful AI assistant."
        self.model = model
        self.turns: List[ConversationTurn] = []
        
        try:
            self.encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            self.encoding = tiktoken.get_encoding("cl100k_base")
    
    def add_turn(self, role: str, content: str, metadata: Optional[Dict] = None):
        """Add a new conversation turn"""
        turn = ConversationTurn(
            role=role,
            content=content,
            metadata=metadata or {}
        )
        self.turns.append(turn)
        
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
            "total_turns": len(self.turns),
            "user_turns": sum(1 for t in self.turns if t.role == "user"),
            "assistant_turns": sum(1 for t in self.turns if t.role == "assistant"),
            "estimated_tokens": self._count_tokens(self.get_messages()),
            "first_turn": self.turns[0].timestamp if self.turns else None,
            "last_turn": self.turns[-1].timestamp if self.turns else None
        }
    
    def clear(self):
        """Clear all conversation turns"""
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
