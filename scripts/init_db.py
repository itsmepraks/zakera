#!/usr/bin/env python3
"""Initialize the database with tables and optionally seed data"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api.database import init_db, drop_db, get_db_context, engine
from src.api.models import User, UserPreferences, Conversation, Message
from passlib.context import CryptContext
import argparse

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_demo_user():
    """Create a demo user with sample data"""
    with get_db_context() as db:
        # Check if demo user already exists
        existing_user = db.query(User).filter(User.username == "demo").first()
        if existing_user:
            print("Demo user already exists!")
            return
        
        # Create demo user
        demo_user = User(
            username="demo",
            email="demo@zakera.ai",
            hashed_password=pwd_context.hash("demo123"),
            full_name="Demo User",
            is_active=True
        )
        db.add(demo_user)
        db.flush()  # Get the user ID
        
        # Create user preferences
        preferences = UserPreferences(
            user_id=demo_user.id,
            theme="light",
            language="en",
            model_preference="gpt-4-turbo-preview",
            temperature=7
        )
        db.add(preferences)
        
        # Create a sample conversation
        conversation = Conversation(
            user_id=demo_user.id,
            title="Welcome to Zakera!",
            system_prompt="You are a helpful AI assistant.",
            model_name="gpt-4-turbo-preview"
        )
        db.add(conversation)
        db.flush()  # Get the conversation ID
        
        # Add sample messages
        messages = [
            Message(
                conversation_id=conversation.id,
                role="user",
                content="Hello! What can you help me with?",
                model_name="gpt-4-turbo-preview"
            ),
            Message(
                conversation_id=conversation.id,
                role="assistant",
                content="Hello! I'm Zakera, your AI assistant. I can help you with a wide range of tasks including:\n\n- Answering questions\n- Writing and editing\n- Coding assistance\n- Problem solving\n- Creative brainstorming\n- And much more!\n\nWhat would you like to explore today?",
                model_name="gpt-4-turbo-preview",
                tokens_used=95
            )
        ]
        for msg in messages:
            db.add(msg)
        
        print(f"✅ Created demo user: {demo_user.username} (password: demo123)")
        print(f"✅ Created sample conversation: {conversation.title}")

def main():
    parser = argparse.ArgumentParser(description="Initialize Zakera database")
    parser.add_argument(
        "--drop",
        action="store_true",
        help="Drop all tables before creating (WARNING: deletes all data!)"
    )
    parser.add_argument(
        "--seed",
        action="store_true",
        help="Seed database with demo data"
    )
    args = parser.parse_args()
    
    print("🗄️  Zakera Database Initialization")
    print("=" * 50)
    
    if args.drop:
        print("⚠️  Dropping all tables...")
        response = input("Are you sure? This will delete ALL data! (yes/no): ")
        if response.lower() == "yes":
            drop_db()
            print("✅ All tables dropped")
        else:
            print("❌ Aborted")
            return
    
    print("📦 Creating database tables...")
    init_db()
    print("✅ Database tables created successfully!")
    
    # Verify tables were created
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"\n📋 Created tables: {', '.join(tables)}")
    
    if args.seed:
        print("\n🌱 Seeding database with demo data...")
        create_demo_user()
    
    print("\n✨ Database initialization complete!")
    print("\nNext steps:")
    print("1. Start the API server: uvicorn src.api.main:app --reload")
    print("2. Visit http://localhost:8000/api/docs for API documentation")
    if args.seed:
        print("3. Login with demo user - username: demo, password: demo123")

if __name__ == "__main__":
    main()
