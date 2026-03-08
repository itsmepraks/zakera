"""
Service layer for conversation template operations.

This module contains business logic for managing conversation templates,
including CRUD operations, validation, and analytics.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import and_, or_, func, desc
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from ..models.conversation_template import ConversationTemplate, TemplateUsageLog
from ..schemas.conversation_templates import (
    ConversationTemplateCreate,
    ConversationTemplateUpdate,
    TemplateCategory
)
from fastapi import HTTPException, status


class ConversationTemplateService:
    """Service class for conversation template operations."""
    
    @staticmethod
    def get_template(db: Session, template_id: int, include_inactive: bool = False) -> ConversationTemplate:
        """
        Get a specific template by ID.
        
        Args:
            db: Database session
            template_id: Template ID
            include_inactive: Whether to include inactive templates
            
        Returns:
            ConversationTemplate object
            
        Raises:
            HTTPException: If template not found
        """
        query = db.query(ConversationTemplate).filter(ConversationTemplate.id == template_id)
        
        if not include_inactive:
            query = query.filter(ConversationTemplate.is_active == True)
        
        template = query.first()
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template with ID {template_id} not found"
            )
        
        return template
    
    @staticmethod
    def get_templates(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        category: Optional[str] = None,
        difficulty: Optional[str] = None,
        tags: Optional[List[str]] = None,
        search: Optional[str] = None,
        is_public: Optional[bool] = None,
        is_active: bool = True,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> tuple[List[ConversationTemplate], int]:
        """
        Get list of templates with filtering and pagination.
        
        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            category: Filter by category
            difficulty: Filter by difficulty level
            tags: Filter by tags (any match)
            search: Search in title and description
            is_public: Filter by public status
            is_active: Filter by active status
            sort_by: Field to sort by
            sort_order: Sort order (asc or desc)
            
        Returns:
            Tuple of (templates list, total count)
        """
        query = db.query(ConversationTemplate)
        
        # Apply filters
        filters = []
        
        if is_active is not None:
            filters.append(ConversationTemplate.is_active == is_active)
        
        if is_public is not None:
            filters.append(ConversationTemplate.is_public == is_public)
        
        if category:
            filters.append(ConversationTemplate.category == category)
        
        if difficulty:
            filters.append(ConversationTemplate.difficulty == difficulty)
        
        if search:
            search_filter = or_(
                ConversationTemplate.title.ilike(f"%{search}%"),
                ConversationTemplate.description.ilike(f"%{search}%")
            )
            filters.append(search_filter)
        
        if tags:
            # Filter templates that have any of the specified tags
            # This requires JSON operations which may vary by database
            tag_filters = []
            for tag in tags:
                tag_filters.append(
                    ConversationTemplate.tags.contains([tag])
                )
            filters.append(or_(*tag_filters))
        
        if filters:
            query = query.filter(and_(*filters))
        
        # Get total count
        total = query.count()
        
        # Apply sorting
        sort_column = getattr(ConversationTemplate, sort_by, ConversationTemplate.created_at)
        if sort_order.lower() == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(sort_column)
        
        # Apply pagination
        templates = query.offset(skip).limit(limit).all()
        
        return templates, total
    
    @staticmethod
    def create_template(
        db: Session,
        template: ConversationTemplateCreate,
        user_id: Optional[int] = None
    ) -> ConversationTemplate:
        """
        Create a new conversation template.
        
        Args:
            db: Database session
            template: Template data
            user_id: ID of user creating the template
            
        Returns:
            Created ConversationTemplate object
            
        Raises:
            HTTPException: If creation fails
        """
        try:
            db_template = ConversationTemplate(
                title=template.title,
                description=template.description,
                category=template.category.value,
                difficulty=template.difficulty.value if template.difficulty else "intermediate",
                system_prompt=template.system_prompt,
                starter_message=template.starter_message,
                suggested_questions=template.suggested_questions or [],
                tags=template.tags or [],
                model_recommendations=template.model_recommendations or [],
                is_public=template.is_public,
                is_active=template.is_active,
                created_by=user_id,
                usage_count=0
            )
            
            db.add(db_template)
            db.commit()
            db.refresh(db_template)
            
            return db_template
            
        except IntegrityError as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to create template: {str(e)}"
            )
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"An error occurred while creating the template: {str(e)}"
            )
    
    @staticmethod
    def update_template(
        db: Session,
        template_id: int,
        template_update: ConversationTemplateUpdate,
        user_id: Optional[int] = None
    ) -> ConversationTemplate:
        """
        Update an existing template.
        
        Args:
            db: Database session
            template_id: Template ID
            template_update: Updated template data
            user_id: ID of user updating the template
            
        Returns:
            Updated ConversationTemplate object
            
        Raises:
            HTTPException: If template not found or update fails
        """
        db_template = ConversationTemplateService.get_template(db, template_id, include_inactive=True)
        
        # Check permissions (optional - implement based on your auth system)
        # if user_id and db_template.created_by != user_id:
        #     raise HTTPException(status_code=403, detail="Not authorized to update this template")
        
        try:
            # Update only provided fields
            update_data = template_update.model_dump(exclude_unset=True)
            
            for field, value in update_data.items():
                if hasattr(db_template, field):
                    # Handle enum values
                    if field in ["category", "difficulty"] and value is not None:
                        setattr(db_template, field, value.value)
                    else:
                        setattr(db_template, field, value)
            
            db.commit()
            db.refresh(db_template)
            
            return db_template
            
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update template: {str(e)}"
            )
    
    @staticmethod
    def delete_template(db: Session, template_id: int, soft_delete: bool = True) -> bool:
        """
        Delete a template (soft or hard delete).
        
        Args:
            db: Database session
            template_id: Template ID
            soft_delete: If True, set is_active=False; if False, delete from database
            
        Returns:
            True if deletion successful
            
        Raises:
            HTTPException: If template not found or deletion fails
        """
        db_template = ConversationTemplateService.get_template(db, template_id, include_inactive=True)
        
        try:
            if soft_delete:
                db_template.is_active = False
                db.commit()
            else:
                db.delete(db_template)
                db.commit()
            
            return True
            
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete template: {str(e)}"
            )
    
    @staticmethod
    def log_template_usage(
        db: Session,
        template_id: int,
        user_id: Optional[int] = None,
        conversation_id: Optional[int] = None,
        model_used: Optional[str] = None
    ) -> None:
        """
        Log template usage and increment usage counter.
        
        Args:
            db: Database session
            template_id: Template ID
            user_id: User ID who used the template
            conversation_id: Conversation ID created from template
            model_used: Model provider used
        """
        try:
            # Create usage log
            usage_log = TemplateUsageLog(
                template_id=template_id,
                user_id=user_id,
                conversation_id=conversation_id,
                model_used=model_used
            )
            db.add(usage_log)
            
            # Increment usage counter
            template = db.query(ConversationTemplate).filter(
                ConversationTemplate.id == template_id
            ).first()
            
            if template:
                template.increment_usage()
            
            db.commit()
            
        except Exception as e:
            db.rollback()
            # Log error but don't raise - usage tracking shouldn't block template use
            print(f"Error logging template usage: {str(e)}")
    
    @staticmethod
    def get_popular_templates(
        db: Session,
        limit: int = 10,
        category: Optional[str] = None
    ) -> List[ConversationTemplate]:
        """
        Get most popular templates by usage count.
        
        Args:
            db: Database session
            limit: Maximum number of templates to return
            category: Optional category filter
            
        Returns:
            List of popular templates
        """
        query = db.query(ConversationTemplate).filter(
            ConversationTemplate.is_active == True,
            ConversationTemplate.is_public == True
        )
        
        if category:
            query = query.filter(ConversationTemplate.category == category)
        
        templates = query.order_by(
            desc(ConversationTemplate.usage_count)
        ).limit(limit).all()
        
        return templates
    
    @staticmethod
    def get_template_stats(db: Session, template_id: int) -> Dict[str, Any]:
        """
        Get usage statistics for a template.
        
        Args:
            db: Database session
            template_id: Template ID
            
        Returns:
            Dictionary with usage statistics
        """
        template = ConversationTemplateService.get_template(db, template_id)
        
        # Get usage logs
        usage_logs = db.query(TemplateUsageLog).filter(
            TemplateUsageLog.template_id == template_id
        ).all()
        
        # Calculate stats
        total_uses = len(usage_logs)
        unique_users = len(set(log.user_id for log in usage_logs if log.user_id))
        
        # Get last used date
        last_used = max((log.used_at for log in usage_logs), default=None)
        
        # Model usage distribution
        model_distribution = {}
        for log in usage_logs:
            if log.model_used:
                model_distribution[log.model_used] = model_distribution.get(log.model_used, 0) + 1
        
        return {
            "template_id": template_id,
            "title": template.title,
            "total_uses": total_uses,
            "unique_users": unique_users,
            "last_used": last_used,
            "model_distribution": model_distribution,
            "created_at": template.created_at,
            "is_public": template.is_public,
            "is_active": template.is_active
        }
    
    @staticmethod
    def bulk_create_templates(
        db: Session,
        templates: List[ConversationTemplateCreate],
        user_id: Optional[int] = None,
        skip_duplicates: bool = True
    ) -> Dict[str, Any]:
        """
        Create multiple templates in bulk.
        
        Args:
            db: Database session
            templates: List of template data
            user_id: ID of user creating templates
            skip_duplicates: Skip templates with duplicate titles
            
        Returns:
            Dictionary with import results
        """
        results = {
            "total_attempted": len(templates),
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "imported_ids": [],
            "errors": []
        }
        
        for template in templates:
            try:
                # Check for duplicates if needed
                if skip_duplicates:
                    existing = db.query(ConversationTemplate).filter(
                        ConversationTemplate.title == template.title
                    ).first()
                    
                    if existing:
                        results["skipped"] += 1
                        continue
                
                # Create template
                db_template = ConversationTemplateService.create_template(db, template, user_id)
                results["successful"] += 1
                results["imported_ids"].append(db_template.id)
                
            except Exception as e:
                results["failed"] += 1
                results["errors"].append(f"Failed to create '{template.title}': {str(e)}")
        
        return results
