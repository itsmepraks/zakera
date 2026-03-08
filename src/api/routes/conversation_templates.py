"""
API routes for conversation templates.

This module defines RESTful endpoints for managing conversation templates,
including CRUD operations, search, filtering, and analytics.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status, Path
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.conversation_templates import (
    ConversationTemplateCreate,
    ConversationTemplateUpdate,
    ConversationTemplateResponse,
    ConversationTemplateListResponse,
    TemplateUsageStats,
    BulkTemplateImport,
    BulkImportResponse,
    TemplateCategory,
    TemplateDifficulty
)
from ..services.conversation_template_service import ConversationTemplateService
from ..auth import get_current_user  # Adjust import based on your auth implementation

# Create router
router = APIRouter(
    prefix="/conversation-templates",
    tags=["Conversation Templates"],
    responses={
        404: {"description": "Template not found"},
        500: {"description": "Internal server error"}
    }
)


@router.get(
    "/",
    response_model=ConversationTemplateListResponse,
    summary="List conversation templates",
    description="Retrieve a paginated list of conversation templates with optional filtering"
)
async def list_templates(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of records to return"),
    category: Optional[TemplateCategory] = Query(None, description="Filter by category"),
    difficulty: Optional[TemplateDifficulty] = Query(None, description="Filter by difficulty level"),
    tags: Optional[List[str]] = Query(None, description="Filter by tags (comma-separated)"),
    search: Optional[str] = Query(None, min_length=2, description="Search in title and description"),
    is_public: Optional[bool] = Query(None, description="Filter by public status"),
    is_active: bool = Query(True, description="Filter by active status"),
    sort_by: str = Query("created_at", regex="^(created_at|updated_at|usage_count|title)$", description="Field to sort by"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order"),
    db: Session = Depends(get_db)
):
    """
    Get a paginated list of conversation templates.
    
    **Filters:**
    - `category`: Filter by template category
    - `difficulty`: Filter by difficulty level
    - `tags`: Filter by tags (any match)
    - `search`: Search in title and description
    - `is_public`: Filter public/private templates
    - `is_active`: Filter active/inactive templates
    
    **Sorting:**
    - `sort_by`: Field to sort by (created_at, updated_at, usage_count, title)
    - `sort_order`: Sort order (asc, desc)
    
    **Pagination:**
    - `skip`: Number of records to skip
    - `limit`: Maximum records to return (1-100)
    
    Returns a paginated response with total count and list of templates.
    """
    try:
        category_value = category.value if category else None
        difficulty_value = difficulty.value if difficulty else None
        
        templates, total = ConversationTemplateService.get_templates(
            db=db,
            skip=skip,
            limit=limit,
            category=category_value,
            difficulty=difficulty_value,
            tags=tags,
            search=search,
            is_public=is_public,
            is_active=is_active,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        return ConversationTemplateListResponse(
            total=total,
            page=skip // limit + 1,
            page_size=limit,
            templates=[ConversationTemplateResponse.model_validate(t) for t in templates]
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve templates: {str(e)}"
        )


@router.post(
    "/",
    response_model=ConversationTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new conversation template",
    description="Create a new conversation template with system prompt and metadata"
)
async def create_template(
    template: ConversationTemplateCreate,
    db: Session = Depends(get_db),
    # current_user = Depends(get_current_user)  # Uncomment when auth is ready
):
    """
    Create a new conversation template.
    
    **Required fields:**
    - `title`: Template title (3-200 characters)
    - `description`: Detailed description (10-1000 characters)
    - `category`: Template category
    - `system_prompt`: System prompt for AI behavior (20-5000 characters)
    
    **Optional fields:**
    - `difficulty`: Difficulty level (default: intermediate)
    - `starter_message`: Initial conversation message
    - `suggested_questions`: List of suggested prompts
    - `tags`: Tags for searching (lowercase, alphanumeric)
    - `model_recommendations`: Recommended model providers
    - `is_public`: Public visibility (default: true)
    - `is_active`: Active status (default: true)
    
    Returns the created template with generated ID and timestamps.
    """
    try:
        # user_id = current_user.id  # Uncomment when auth is ready
        user_id = None  # Temporary until auth is implemented
        
        db_template = ConversationTemplateService.create_template(
            db=db,
            template=template,
            user_id=user_id
        )
        
        return ConversationTemplateResponse.model_validate(db_template)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create template: {str(e)}"
        )


@router.get(
    "/{template_id}",
    response_model=ConversationTemplateResponse,
    summary="Get a specific conversation template",
    description="Retrieve details of a conversation template by ID"
)
async def get_template(
    template_id: int = Path(..., ge=1, description="Template ID"),
    db: Session = Depends(get_db)
):
    """
    Get a specific conversation template by ID.
    
    **Path parameters:**
    - `template_id`: Unique template identifier
    
    Returns the complete template details including:
    - Basic information (title, description, category)
    - Template content (system prompt, starter message)
    - Metadata (tags, model recommendations)
    - Usage statistics
    - Timestamps
    
    **Raises:**
    - 404: Template not found
    - 500: Internal server error
    """
    template = ConversationTemplateService.get_template(
        db=db,
        template_id=template_id
    )
    
    return ConversationTemplateResponse.model_validate(template)


@router.put(
    "/{template_id}",
    response_model=ConversationTemplateResponse,
    summary="Update a conversation template",
    description="Update an existing conversation template (partial updates supported)"
)
async def update_template(
    template_update: ConversationTemplateUpdate,
    template_id: int = Path(..., ge=1, description="Template ID"),
    db: Session = Depends(get_db),
    # current_user = Depends(get_current_user)  # Uncomment when auth is ready
):
    """
    Update an existing conversation template.
    
    **Path parameters:**
    - `template_id`: Template ID to update
    
    **Request body:**
    All fields are optional - only provided fields will be updated:
    - `title`: New template title
    - `description`: New description
    - `category`: New category
    - `difficulty`: New difficulty level
    - `system_prompt`: Updated system prompt
    - `starter_message`: Updated starter message
    - `suggested_questions`: Updated question list
    - `tags`: Updated tags
    - `model_recommendations`: Updated recommendations
    - `is_public`: Public visibility
    - `is_active`: Active status
    
    Returns the updated template with new timestamp.
    
    **Raises:**
    - 404: Template not found
    - 403: Not authorized (if permissions enabled)
    - 500: Update failed
    """
    try:
        # user_id = current_user.id  # Uncomment when auth is ready
        user_id = None
        
        updated_template = ConversationTemplateService.update_template(
            db=db,
            template_id=template_id,
            template_update=template_update,
            user_id=user_id
        )
        
        return ConversationTemplateResponse.model_validate(updated_template)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update template: {str(e)}"
        )


@router.delete(
    "/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a conversation template",
    description="Delete a conversation template (soft delete by default)"
)
async def delete_template(
    template_id: int = Path(..., ge=1, description="Template ID"),
    hard_delete: bool = Query(False, description="Permanently delete (vs soft delete)"),
    db: Session = Depends(get_db),
    # current_user = Depends(get_current_user)  # Uncomment when auth is ready
):
    """
    Delete a conversation template.
    
    **Path parameters:**
    - `template_id`: Template ID to delete
    
    **Query parameters:**
    - `hard_delete`: If true, permanently delete; if false, soft delete (set is_active=false)
    
    **Soft delete (default):**
    - Sets `is_active` to false
    - Template remains in database for analytics
    - Can be reactivated later
    
    **Hard delete:**
    - Permanently removes template from database
    - Cannot be recovered
    - Use with caution
    
    Returns 204 No Content on success.
    
    **Raises:**
    - 404: Template not found
    - 403: Not authorized (if permissions enabled)
    - 500: Deletion failed
    """
    ConversationTemplateService.delete_template(
        db=db,
        template_id=template_id,
        soft_delete=not hard_delete
    )
    
    return None


@router.get(
    "/popular/top",
    response_model=List[ConversationTemplateResponse],
    summary="Get popular templates",
    description="Retrieve most popular templates by usage count"
)
async def get_popular_templates(
    limit: int = Query(10, ge=1, le=50, description="Number of templates to return"),
    category: Optional[TemplateCategory] = Query(None, description="Filter by category"),
    db: Session = Depends(get_db)
):
    """
    Get most popular conversation templates.
    
    **Query parameters:**
    - `limit`: Number of templates to return (1-50, default: 10)
    - `category`: Optional category filter
    
    Returns templates ordered by usage count (descending).
    Only includes active, public templates.
    
    Useful for:
    - Discovering commonly used templates
    - Featuring popular templates in UI
    - Understanding user preferences
    """
    category_value = category.value if category else None
    
    templates = ConversationTemplateService.get_popular_templates(
        db=db,
        limit=limit,
        category=category_value
    )
    
    return [ConversationTemplateResponse.model_validate(t) for t in templates]


@router.get(
    "/{template_id}/stats",
    response_model=TemplateUsageStats,
    summary="Get template usage statistics",
    description="Retrieve detailed usage statistics for a template"
)
async def get_template_stats(
    template_id: int = Path(..., ge=1, description="Template ID"),
    db: Session = Depends(get_db)
):
    """
    Get usage statistics for a conversation template.
    
    **Path parameters:**
    - `template_id`: Template ID
    
    Returns detailed statistics including:
    - Total usage count
    - Unique users who used template
    - Last usage timestamp
    - Model provider distribution
    - Creation and status information
    
    Useful for:
    - Template performance analytics
    - Understanding user behavior
    - Optimizing template recommendations
    """
    stats = ConversationTemplateService.get_template_stats(
        db=db,
        template_id=template_id
    )
    
    return TemplateUsageStats(**stats)


@router.post(
    "/{template_id}/use",
    status_code=status.HTTP_200_OK,
    summary="Log template usage",
    description="Record template usage for analytics"
)
async def log_template_usage(
    template_id: int = Path(..., ge=1, description="Template ID"),
    conversation_id: Optional[int] = Query(None, description="Associated conversation ID"),
    model_used: Optional[str] = Query(None, description="Model provider used"),
    db: Session = Depends(get_db),
    # current_user = Depends(get_current_user)  # Uncomment when auth is ready
):
    """
    Log usage of a conversation template.
    
    **Path parameters:**
    - `template_id`: Template ID being used
    
    **Query parameters:**
    - `conversation_id`: ID of conversation created from template
    - `model_used`: Model provider used for conversation
    
    This endpoint should be called when a user starts a conversation
    using a template. It:
    - Increments the usage counter
    - Creates a usage log entry
    - Tracks which models are commonly used with the template
    
    Returns success status.
    """
    try:
        # user_id = current_user.id  # Uncomment when auth is ready
        user_id = None
        
        ConversationTemplateService.log_template_usage(
            db=db,
            template_id=template_id,
            user_id=user_id,
            conversation_id=conversation_id,
            model_used=model_used
        )
        
        return {"message": "Usage logged successfully"}
        
    except Exception as e:
        # Don't raise error - usage logging shouldn't block functionality
        return {"message": f"Warning: Failed to log usage: {str(e)}"}


@router.post(
    "/bulk-import",
    response_model=BulkImportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Bulk import templates",
    description="Import multiple conversation templates at once"
)
async def bulk_import_templates(
    bulk_import: BulkTemplateImport,
    db: Session = Depends(get_db),
    # current_user = Depends(get_current_user)  # Uncomment when auth is ready
):
    """
    Import multiple conversation templates in bulk.
    
    **Request body:**
    - `templates`: List of templates to import (1-50)
    - `skip_duplicates`: Skip templates with duplicate titles (default: true)
    
    Useful for:
    - Initial setup with predefined templates
    - Importing templates from external sources
    - Batch template creation
    
    Returns import results including:
    - Total attempted imports
    - Successful imports count
    - Failed imports count
    - Skipped duplicates count
    - IDs of imported templates
    - Error messages for failures
    """
    try:
        # user_id = current_user.id  # Uncomment when auth is ready
        user_id = None
        
        results = ConversationTemplateService.bulk_create_templates(
            db=db,
            templates=bulk_import.templates,
            user_id=user_id,
            skip_duplicates=bulk_import.skip_duplicates
        )
        
        return BulkImportResponse(**results)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Bulk import failed: {str(e)}"
        )


@router.get(
    "/categories/list",
    response_model=List[str],
    summary="Get available categories",
    description="List all available template categories"
)
async def list_categories():
    """
    Get list of available template categories.
    
    Returns all defined template categories from the TemplateCategory enum.
    
    Useful for:
    - Populating category dropdowns in UI
    - Validation
    - Discovery
    """
    return [category.value for category in TemplateCategory]


@router.get(
    "/difficulties/list",
    response_model=List[str],
    summary="Get available difficulty levels",
    description="List all available difficulty levels"
)
async def list_difficulties():
    """
    Get list of available difficulty levels.
    
    Returns all defined difficulty levels from the TemplateDifficulty enum.
    
    Useful for:
    - Populating difficulty dropdowns in UI
    - Filtering templates by skill level
    - User experience customization
    """
    return [difficulty.value for difficulty in TemplateDifficulty]
