from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, JSON, Index
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

class Conversation(Base):
    """Conversation model for chat sessions"""
    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    system_prompt = Column(Text)
    model_name = Column(String(50), default="gpt-4-turbo-preview")
    temperature = Column(Integer, default=7)
    max_tokens = Column(Integer, default=4000)
    is_archived = Column(Boolean, default=False)
    is_pinned = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    metadata = Column(JSON, default=dict)  # Additional flexible data

    # Relationships
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at")

    # Indexes for better query performance
    __table_args__ = (
        Index('idx_user_updated', 'user_id', 'updated_at'),
        Index('idx_user_archived', 'user_id', 'is_archived'),
    )

    def __repr__(self):
        return f"<Conversation(id={self.id}, title={self.title}, user_id={self.user_id})>"

class Message(Base):
    """Message model for chat messages"""
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String(36), ForeignKey("conversations.id"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    tokens_used = Column(Integer, default=0)
    model_name = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    metadata = Column(JSON, default=dict)  # Store additional data like tool calls, etc.

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")

    # Indexes
    __table_args__ = (
        Index('idx_conversation_created', 'conversation_id', 'created_at'),
        Index('idx_conversation_role', 'conversation_id', 'role'),
    )

    def __repr__(self):
        return f"<Message(id={self.id}, role={self.role}, conversation_id={self.conversation_id})>"
