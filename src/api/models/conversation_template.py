"""
SQLAlchemy models for conversation templates.

This module defines the database models for storing conversation templates
and related metadata.
"""

from datetime import datetime
from typing import List

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, Integer, String, Text, 
    ForeignKey, Index, JSON
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database import Base


class ConversationTemplate(Base):
    """
    SQLAlchemy model for conversation templates.
    
    Stores predefined conversation starters and system prompts that users
    can use to quickly begin conversations with specific contexts.
    """
    
    __tablename__ = "conversation_templates"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Basic information
    title = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=False)
    category = Column(
        String(50), 
        nullable=False, 
        index=True,
        comment="Template category (code_review, technical, creative, etc.)"
    )
    difficulty = Column(
        String(20),
        default="intermediate",
        comment="Difficulty level (beginner, intermediate, advanced, expert)"
    )
    
    # Template content
    system_prompt = Column(Text, nullable=False, comment="System prompt for AI behavior")
    starter_message = Column(Text, nullable=True, comment="Optional conversation starter")
    suggested_questions = Column(
        JSON, 
        default=list,
        comment="List of suggested questions/prompts"
    )
    
    # Metadata
    tags = Column(JSON, default=list, comment="Tags for searching and filtering")
    model_recommendations = Column(
        JSON,
        default=list,
        comment="Recommended model providers"
    )
    
    # Status flags
    is_public = Column(Boolean, default=True, index=True)
    is_active = Column(Boolean, default=True, index=True)
    
    # Usage tracking
    usage_count = Column(Integer, default=0, comment="Number of times used")
    
    # User relationship
    created_by = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User who created the template"
    )
    
    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    
    # Relationships
    creator = relationship(
        "User",
        back_populates="conversation_templates",
        foreign_keys=[created_by]
    )
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_template_category_active', 'category', 'is_active'),
        Index('idx_template_public_active', 'is_public', 'is_active'),
        Index('idx_template_created_at', 'created_at'),
        Index('idx_template_usage_count', 'usage_count'),
    )
    
    def __repr__(self):
        return f"<ConversationTemplate(id={self.id}, title='{self.title}', category='{self.category}')>"
    
    def increment_usage(self):
        """Increment the usage counter for this template."""
        self.usage_count += 1
    
    def to_dict(self):
        """Convert template to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "difficulty": self.difficulty,
            "system_prompt": self.system_prompt,
            "starter_message": self.starter_message,
            "suggested_questions": self.suggested_questions or [],
            "tags": self.tags or [],
            "model_recommendations": self.model_recommendations or [],
            "is_public": self.is_public,
            "is_active": self.is_active,
            "usage_count": self.usage_count,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class TemplateUsageLog(Base):
    """
    SQLAlchemy model for tracking template usage.
    
    Logs when templates are used to provide analytics and insights.
    """
    
    __tablename__ = "template_usage_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(
        Integer,
        ForeignKey("conversation_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    conversation_id = Column(
        Integer,
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=True
    )
    model_used = Column(String(100), nullable=True)
    used_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    template = relationship("ConversationTemplate")
    
    __table_args__ = (
        Index('idx_usage_template_date', 'template_id', 'used_at'),
        Index('idx_usage_user_date', 'user_id', 'used_at'),
    )
    
    def __repr__(self):
        return f"<TemplateUsageLog(id={self.id}, template_id={self.template_id}, used_at='{self.used_at}')>"
