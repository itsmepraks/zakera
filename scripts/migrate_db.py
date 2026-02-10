#!/usr/bin/env python3
"""Database migration utilities"""

import sys
from pathlib import Path
import argparse
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api.database import engine, Base
from sqlalchemy import inspect, text

def check_migration_status():
    """Check current database schema status"""
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    print("📊 Current Database Status")
    print("=" * 50)
    
    if not tables:
        print("❌ No tables found. Run 'python scripts/init_db.py' to initialize.")
        return
    
    print(f"✅ Found {len(tables)} tables:\n")
    
    for table in tables:
        columns = inspector.get_columns(table)
        indexes = inspector.get_indexes(table)
        foreign_keys = inspector.get_foreign_keys(table)
        
        print(f"📋 {table}")
        print(f"   Columns: {len(columns)}")
        print(f"   Indexes: {len(indexes)}")
        print(f"   Foreign Keys: {len(foreign_keys)}")
        
        # Show column details
        for col in columns:
            nullable = "NULL" if col['nullable'] else "NOT NULL"
            print(f"      - {col['name']}: {col['type']} {nullable}")
        print()

def backup_database():
    """Create a backup of the current database"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"data/backups/zakera_backup_{timestamp}.sql"
    
    # Create backups directory
    Path("data/backups").mkdir(parents=True, exist_ok=True)
    
    print(f"💾 Creating backup: {backup_file}")
    
    # For SQLite, we can copy the file
    import shutil
    from src.api.config import settings
    
    if "sqlite" in settings.DATABASE_URL:
        db_path = settings.DATABASE_URL.replace("sqlite:///", "")
        if Path(db_path).exists():
            shutil.copy2(db_path, backup_file.replace(".sql", ".db"))
            print(f"✅ Backup created successfully!")
        else:
            print("❌ Database file not found")
    else:
        print("⚠️  Backup for non-SQLite databases not implemented yet")

def add_column_if_not_exists(table_name: str, column_name: str, column_type: str):
    """Add a column to a table if it doesn't exist"""
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    
    if column_name not in columns:
        with engine.connect() as conn:
            conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"))
            conn.commit()
        print(f"✅ Added column {column_name} to {table_name}")
    else:
        print(f"ℹ️  Column {column_name} already exists in {table_name}")

def main():
    parser = argparse.ArgumentParser(description="Zakera database migration utilities")
    parser.add_argument(
        "command",
        choices=["status", "backup"],
        help="Migration command to execute"
    )
    args = parser.parse_args()
    
    print("🔄 Zakera Database Migration")
    print("=" * 50)
    print()
    
    if args.command == "status":
        check_migration_status()
    elif args.command == "backup":
        backup_database()

if __name__ == "__main__":
    main()
