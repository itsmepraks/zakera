#!/usr/bin/env python3
"""
Seed default conversation templates into the database.

This script loads and imports the predefined conversation templates
for initial setup or testing purposes.

Usage:
    python scripts/seed_templates.py [--force]
    
Options:
    --force    Force re-import even if templates already exist
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
from sqlalchemy.orm import Session

from src.api.database import SessionLocal, engine, Base
from src.api.data.default_templates import get_default_templates, DEFAULT_TEMPLATES
from src.api.services.conversation_template_service import ConversationTemplateService
from src.api.models.conversation_template import ConversationTemplate


def create_tables():
    """Create database tables if they don't exist."""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✓ Tables created successfully")


def count_existing_templates(db: Session) -> int:
    """Count existing templates in the database."""
    return db.query(ConversationTemplate).count()


def seed_templates(db: Session, force: bool = False) -> dict:
    """
    Seed default templates into the database.
    
    Args:
        db: Database session
        force: If True, import even if templates exist
        
    Returns:
        Dictionary with import statistics
    """
    existing_count = count_existing_templates(db)
    
    if existing_count > 0 and not force:
        print(f"⚠️  Database already contains {existing_count} templates.")
        print("   Use --force to re-import templates anyway.")
        return {
            "status": "skipped",
            "existing_count": existing_count,
            "imported": 0
        }
    
    print(f"\n📦 Importing {len(DEFAULT_TEMPLATES)} default templates...")
    
    templates = get_default_templates()
    
    results = ConversationTemplateService.bulk_create_templates(
        db=db,
        templates=templates,
        user_id=None,  # System-created templates
        skip_duplicates=True
    )
    
    return results


def print_results(results: dict):
    """Print import results in a formatted way."""
    print("\n" + "="*60)
    print("IMPORT RESULTS")
    print("="*60)
    
    if results.get("status") == "skipped":
        print(f"Status: Skipped (use --force to override)")
        print(f"Existing templates: {results['existing_count']}")
        return
    
    print(f"Total attempted: {results['total_attempted']}")
    print(f"✓ Successful: {results['successful']}")
    print(f"✗ Failed: {results['failed']}")
    print(f"⊘ Skipped (duplicates): {results['skipped']}")
    
    if results['imported_ids']:
        print(f"\nImported template IDs: {', '.join(map(str, results['imported_ids']))}")
    
    if results['errors']:
        print("\nErrors encountered:")
        for error in results['errors']:
            print(f"  • {error}")
    
    print("="*60)


def list_templates(db: Session):
    """List all templates in the database."""
    templates = db.query(ConversationTemplate).order_by(
        ConversationTemplate.category, ConversationTemplate.title
    ).all()
    
    if not templates:
        print("No templates found in database.")
        return
    
    print(f"\n📋 Found {len(templates)} templates:\n")
    
    current_category = None
    for template in templates:
        if template.category != current_category:
            current_category = template.category
            print(f"\n{current_category.upper().replace('_', ' ')}:")
        
        status = "✓" if template.is_active else "✗"
        visibility = "🌐" if template.is_public else "🔒"
        
        print(f"  {status} {visibility} [{template.id}] {template.title}")
        print(f"      Difficulty: {template.difficulty} | Uses: {template.usage_count}")
        print(f"      Tags: {', '.join(template.tags[:5]) if template.tags else 'none'}")


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Seed default conversation templates into the database"
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force import even if templates already exist'
    )
    parser.add_argument(
        '--list',
        action='store_true',
        help='List existing templates and exit'
    )
    parser.add_argument(
        '--create-tables',
        action='store_true',
        help='Create database tables before seeding'
    )
    
    args = parser.parse_args()
    
    print("="*60)
    print("CONVERSATION TEMPLATES - SEED SCRIPT")
    print("="*60)
    
    # Create tables if requested
    if args.create_tables:
        create_tables()
        print()
    
    # Get database session
    db = SessionLocal()
    
    try:
        # List mode
        if args.list:
            list_templates(db)
            return
        
        # Seed templates
        results = seed_templates(db, force=args.force)
        print_results(results)
        
        # Show summary
        if results.get('status') != 'skipped' and results['successful'] > 0:
            print(f"\n✨ Successfully imported {results['successful']} templates!")
            print("\nYou can now:")
            print("  • View templates: GET /api/v1/conversation-templates")
            print("  • Create conversations using templates")
            print("  • List templates: python scripts/seed_templates.py --list")
    
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    finally:
        db.close()


if __name__ == "__main__":
    main()
