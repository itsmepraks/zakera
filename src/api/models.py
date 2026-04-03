from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, JSON, Index, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import uuid

from .database import Base

class User(Base):
    """User model for authentication and profile"""
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100))
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_login = Column(DateTime(timezone=True))

    # Relationships
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    preferences = relationship("UserPreferences", back_populates="user", uselist=False, cascade="all, delete-orphan")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, email={self.email})>"

class UserPreferences(Base):
    """User preferences and settings"""
    __tablename__ = "user_preferences"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, unique=True)
    theme = Column(String(20), default="light")  # light, dark, auto
    language = Column(String(10), default="en")
    model_preference = Column(String(50), default="gpt-4-turbo-preview")
    temperature = Column(Integer, default=7)  # 0-10 scale (divide by 10 for actual)
    system_prompt = Column(Text)
    preferences_data = Column(JSON, default=dict)  # Additional flexible preferences
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="preferences")

    def __repr__(self):
        return f"<UserPreferences(user_id={self.user_id}, theme={self.theme})>"

class UserSession(Base):
    """Track user sessions for analytics and security"""
    __tablename__ = "user_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    session_token = Column(String(255), unique=True, nullable=False, index=True)
    ip_address = Column(String(45))  # IPv6 compatible
    user_agent = Column(String(255))
    device_info = Column(JSON, default=dict)
    is_active = Column(Boolean, default=True)
    last_activity = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True))

    # Relationships
    user = relationship("User", back_populates="sessions")

    # Indexes
    __table_args__ = (
        Index('idx_session_user_active', 'user_id', 'is_active'),
        Index('idx_session_expires', 'expires_at'),
    )

    def __repr__(self):
        return f"<UserSession(id={self.id}, user_id={self.user_id}, is_active={self.is_active})>"

class Conversation(Base):
    """Conversation model for chat sessions"""
    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    system_prompt = Column(Text)
    model_name = Column(String(50), default="gpt-4-turbo-preview")
    temperature = Column(Float, default=0.7)
    max_tokens = Column(Integer, default=4000)
    is_archived = Column(Boolean, default=False, index=True)
    is_pinned = Column(Boolean, default=False, index=True)
    is_deleted = Column(Boolean, default=False, index=True)  # Soft delete
    deleted_at = Column(DateTime(timezone=True))
    total_tokens = Column(Integer, default=0)  # Total tokens used in conversation
    total_cost = Column(Float, default=0.0)  # Total cost in USD
    message_count = Column(Integer, default=0)  # Denormalized for performance
    last_message_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    metadata = Column(JSON, default=dict)  # Additional flexible data
    tags = Column(JSON, default=list)  # Tags for categorization

    # Relationships
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at")

    # Indexes for better query performance
    __table_args__ = (
        Index('idx_user_updated', 'user_id', 'updated_at'),
        Index('idx_user_archived', 'user_id', 'is_archived'),
        Index('idx_user_deleted', 'user_id', 'is_deleted'),
        Index('idx_user_pinned', 'user_id', 'is_pinned'),
        Index('idx_last_message', 'user_id', 'last_message_at'),
    )

    def __repr__(self):
        return f"<Conversation(id={self.id}, title={self.title}, user_id={self.user_id})>"

class Message(Base):
    """Message model for chat messages"""
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String(36), ForeignKey("conversations.id"), nullable=False, index=True)
    role = Column(String(20), nullable=False, index=True)  # user, assistant, system, tool
    content = Column(Text, nullable=False)
    tokens_used = Column(Integer, default=0)
    cost = Column(Float, default=0.0)  # Cost in USD for this message
    model_name = Column(String(50))
    finish_reason = Column(String(50))  # stop, length, tool_calls, etc.
    error = Column(Text)  # Store error message if generation failed
    latency_ms = Column(Integer)  # Response latency in milliseconds
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    metadata = Column(JSON, default=dict)  # Store additional data like tool calls, function calls, etc.
    
    # For threaded conversations / message branching
    parent_message_id = Column(String(36), ForeignKey("messages.id"), nullable=True)
    version = Column(Integer, default=1)  # For regenerated responses

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    parent_message = relationship("Message", remote_side=[id], backref="child_messages")
    feedbacks = relationship("MessageFeedback", back_populates="message", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('idx_conversation_created', 'conversation_id', 'created_at'),
        Index('idx_conversation_role', 'conversation_id', 'role'),
        Index('idx_parent_message', 'parent_message_id'),
    )

    def __repr__(self):
        return f"<Message(id={self.id}, role={self.role}, conversation_id={self.conversation_id})>"

class MessageFeedback(Base):
    """Model to store user feedback on individual messages"""
    __tablename__ = "message_feedbacks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    message_id = Column(String(36), ForeignKey("messages.id"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    is_positive = Column(Boolean, nullable=False)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    message = relationship("Message", back_populates="feedbacks")

    def __repr__(self):
        return f"<MessageFeedback(id={self.id}, message_id={self.message_id}, is_positive={self.is_positive})>"

class ConversationShare(Base):
    """Share conversations with other users or publicly"""
    __tablename__ = "conversation_shares"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String(36), ForeignKey("conversations.id"), nullable=False, index=True)
    share_token = Column(String(64), unique=True, nullable=False, index=True)  # Public share URL token
    shared_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    shared_with = Column(String(36), ForeignKey("users.id"), nullable=True)  # Null for public shares
    is_public = Column(Boolean, default=False)
    can_edit = Column(Boolean, default=False)
    view_count = Column(Integer, default=0)
    expires_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_accessed = Column(DateTime(timezone=True))

    # Indexes
    __table_args__ = (
        Index('idx_conversation_share', 'conversation_id'),
        Index('idx_shared_by', 'shared_by'),
        Index('idx_expires', 'expires_at'),
    )

    def __repr__(self):
        return f"<ConversationShare(id={self.id}, conversation_id={self.conversation_id}, is_public={self.is_public})>"

class ConversationExport(Base):
    """Track conversation exports for analytics and recovery"""
    __tablename__ = "conversation_exports"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String(36), ForeignKey("conversations.id"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    export_format = Column(String(20), nullable=False)  # json, markdown, pdf, txt
    file_path = Column(String(500))  # S3 path or local file path
    file_size = Column(Integer)  # Size in bytes
    status = Column(String(20), default="pending")  # pending, processing, completed, failed
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))

    # Indexes
    __table_args__ = (
        Index('idx_user_exports', 'user_id', 'created_at'),
        Index('idx_export_status', 'status'),
    )

    def __repr__(self):
        return f"<ConversationExport(id={self.id}, format={self.export_format}, status={self.status})>"
