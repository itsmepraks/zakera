"""
Pydantic schemas for conversation templates API.

This module defines request/response models for the conversation templates
endpoints, including validation rules and documentation.
"""

from datetime import datetime
from typing import List, Optional
from enum import Enum

from pydantic import BaseModel, Field, validator, ConfigDict


class TemplateCategory(str, Enum):
    """Categories for conversation templates."""
    CODE_REVIEW = "code_review"
    TECHNICAL = "technical"
    CREATIVE = "creative"
    PROBLEM_SOLVING = "problem_solving"
    LEARNING = "learning"
    BRAINSTORMING = "brainstorming"
    ANALYSIS = "analysis"
    GENERAL = "general"


class TemplateDifficulty(str, Enum):
    """Difficulty levels for templates."""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class ConversationTemplateBase(BaseModel):
    """Base schema for conversation template."""
    
    title: str = Field(
        ...,
        min_length=3,
        max_length=200,
        description="Template title",
        examples=["Code Review Assistant"]
    )
    description: str = Field(
        ...,
        min_length=10,
        max_length=1000,
        description="Detailed description of the template",
        examples=["A template for conducting thorough code reviews with best practices"]
    )
    category: TemplateCategory = Field(
        ...,
        description="Template category"
    )
    difficulty: Optional[TemplateDifficulty] = Field(
        default=TemplateDifficulty.INTERMEDIATE,
        description="Difficulty level of the template"
    )
    system_prompt: str = Field(
        ...,
        min_length=20,
        max_length=5000,
        description="System prompt that defines the AI's behavior for this template",
        examples=["You are an expert code reviewer. Analyze code for bugs, performance, and best practices."]
    )
    starter_message: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Optional starter message to begin the conversation",
        examples=["Hello! I'm ready to review your code. Please share the code you'd like me to analyze."]
    )
    suggested_questions: Optional[List[str]] = Field(
        default_factory=list,
        description="List of suggested questions/prompts for users",
        examples=[["What are the potential bugs?", "How can I improve performance?", "Are there any security issues?"]]
    )
    tags: Optional[List[str]] = Field(
        default_factory=list,
        max_items=10,
        description="Tags for searching and filtering templates",
        examples=[["code", "review", "python", "best-practices"]]
    )
    model_recommendations: Optional[List[str]] = Field(
        default_factory=list,
        description="Recommended model providers for this template",
        examples=[["gpt-4-turbo", "claude-3-opus", "gemini-1.5-pro"]]
    )
    is_public: bool = Field(
        default=True,
        description="Whether the template is publicly accessible"
    )
    is_active: bool = Field(
        default=True,
        description="Whether the template is active and available for use"
    )
    
    @validator('tags')
    def validate_tags(cls, v):
        """Validate tags are lowercase and alphanumeric with hyphens."""
        if v:
            for tag in v:
                if not all(c.isalnum() or c in ['-', '_'] for c in tag):
                    raise ValueError(f"Tag '{tag}' contains invalid characters. Use only alphanumeric, hyphens, and underscores.")
                if len(tag) < 2 or len(tag) > 30:
                    raise ValueError(f"Tag '{tag}' must be between 2 and 30 characters.")
        return [tag.lower() for tag in v] if v else []
    
    @validator('suggested_questions')
    def validate_suggested_questions(cls, v):
        """Validate suggested questions list."""
        if v and len(v) > 20:
            raise ValueError("Maximum 20 suggested questions allowed.")
        if v:
            for question in v:
                if len(question) < 5 or len(question) > 500:
                    raise ValueError("Each suggested question must be between 5 and 500 characters.")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Python Code Review",
                "description": "Comprehensive Python code review focusing on PEP 8, performance, and best practices",
                "category": "code_review",
                "difficulty": "intermediate",
                "system_prompt": "You are an expert Python developer and code reviewer. Analyze code for PEP 8 compliance, bugs, performance issues, and suggest improvements.",
                "starter_message": "Hello! I'm your Python code review assistant. Share your code and I'll provide detailed feedback.",
                "suggested_questions": [
                    "Is this code PEP 8 compliant?",
                    "Are there any potential bugs?",
                    "How can I improve performance?",
                    "What are the security concerns?"
                ],
                "tags": ["python", "code-review", "pep8", "best-practices"],
                "model_recommendations": ["gpt-4-turbo", "claude-3-opus"],
                "is_public": True,
                "is_active": True
            }
        }
    )


class ConversationTemplateCreate(ConversationTemplateBase):
    """Schema for creating a new conversation template."""
    pass


class ConversationTemplateUpdate(BaseModel):
    """Schema for updating an existing conversation template."""
    
    title: Optional[str] = Field(None, min_length=3, max_length=200)
    description: Optional[str] = Field(None, min_length=10, max_length=1000)
    category: Optional[TemplateCategory] = None
    difficulty: Optional[TemplateDifficulty] = None
    system_prompt: Optional[str] = Field(None, min_length=20, max_length=5000)
    starter_message: Optional[str] = Field(None, max_length=2000)
    suggested_questions: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    model_recommendations: Optional[List[str]] = None
    is_public: Optional[bool] = None
    is_active: Optional[bool] = None
    
    @validator('tags')
    def validate_tags(cls, v):
        """Validate tags are lowercase and alphanumeric with hyphens."""
        if v is not None:
            for tag in v:
                if not all(c.isalnum() or c in ['-', '_'] for c in tag):
                    raise ValueError(f"Tag '{tag}' contains invalid characters.")
                if len(tag) < 2 or len(tag) > 30:
                    raise ValueError(f"Tag '{tag}' must be between 2 and 30 characters.")
            return [tag.lower() for tag in v]
        return v


class ConversationTemplateResponse(ConversationTemplateBase):
    """Schema for conversation template response."""
    
    id: int = Field(..., description="Template unique identifier")
    created_by: Optional[int] = Field(None, description="User ID who created the template")
    usage_count: int = Field(0, description="Number of times this template has been used")
    created_at: datetime = Field(..., description="Template creation timestamp")
    updated_at: datetime = Field(..., description="Template last update timestamp")
    
    model_config = ConfigDict(from_attributes=True)


class ConversationTemplateListResponse(BaseModel):
    """Schema for paginated list of templates."""
    
    total: int = Field(..., description="Total number of templates")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    templates: List[ConversationTemplateResponse] = Field(..., description="List of templates")


class TemplateUsageStats(BaseModel):
    """Schema for template usage statistics."""
    
    template_id: int
    title: str
    usage_count: int
    last_used: Optional[datetime]
    average_conversation_length: Optional[float]
    user_ratings: Optional[float]


class BulkTemplateImport(BaseModel):
    """Schema for bulk importing templates."""
    
    templates: List[ConversationTemplateCreate] = Field(
        ...,
        min_items=1,
        max_items=50,
        description="List of templates to import"
    )
    skip_duplicates: bool = Field(
        default=True,
        description="Skip templates with duplicate titles"
    )


class BulkImportResponse(BaseModel):
    """Response for bulk import operation."""
    
    total_attempted: int
    successful: int
    failed: int
    skipped: int
    imported_ids: List[int]
    errors: List[str]
