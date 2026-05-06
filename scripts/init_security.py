#!/usr/bin/env python3
"""
Security System Initialization Script

This script helps initialize the security system:
- Creates database tables
- Creates initial admin user
- Validates configuration
- Generates secrets
"""

import sys
import secrets
import string
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from src.api.database import engine, Base
from src.api.models import User
from src.security.models import APIKey, UserMFA, AuditLog
from src.security.auth_enhanced import (
    hash_password, UserRole, TokenManager,
    APIKeyManager, MFAManager
)
import uuid


def generate_secret_key(length: int = 32) -> str:
    """Generate a secure SECRET_KEY"""
    alphabet = string.ascii_letters + string.digits + string.punctuation
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def create_tables():
    """Create all database tables"""
    print("📦 Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tables created successfully")


def create_admin_user(db: Session) -> User:
    """Create initial admin user"""
    print("\n👤 Creating initial admin user...")
    
    # Check if admin exists
    existing_admin = db.query(User).filter(User.role == UserRole.SUPER_ADMIN.value).first()
    if existing_admin:
        print(f"⚠️  Admin user already exists: {existing_admin.username}")
        return existing_admin
    
    # Get admin details
    print("\nEnter admin user details:")
    username = input("Username [admin]: ").strip() or "admin"
    email = input("Email [admin@zakera.local]: ").strip() or "admin@zakera.local"
    
    # Get password
    import getpass
    while True:
        password = getpass.getpass("Password (min 8 chars, complex): ")
        confirm = getpass.getpass("Confirm password: ")
        
        if password != confirm:
            print("❌ Passwords don't match. Try again.")
            continue
        
        try:
            hashed = hash_password(password)
            break
        except ValueError as e:
            print(f"❌ {e}")
            continue
    
    # Create admin user
    admin = User(
        id=str(uuid.uuid4()),
        username=username,
        email=email,
        hashed_password=hashed,
        full_name="System Administrator",
        is_active=True,
        email_verified=True,
        role=UserRole.SUPER_ADMIN.value
    )
    
    db.add(admin)
    db.commit()
    db.refresh(admin)
    
    print(f"✅ Admin user created: {username}")
    print(f"   Email: {email}")
    print(f"   Role: {admin.role}")
    
    # Log in audit
    audit_log = AuditLog(
        id=str(uuid.uuid4()),
        user_id=admin.id,
        username=admin.username,
        action="admin.created",
        resource_type="user",
        resource_id=admin.id,
        status="success",
        description="Initial admin user created",
        severity="info"
    )
    db.add(audit_log)
    db.commit()
    
    return admin


def setup_mfa_for_admin(db: Session, admin: User):
    """Optionally setup MFA for admin"""
    print("\n🔐 Multi-Factor Authentication Setup")
    setup_mfa = input("Setup MFA for admin user? [y/N]: ").strip().lower()
    
    if setup_mfa == 'y':
        # Generate MFA secret
        secret = MFAManager.generate_secret()
        qr_uri = MFAManager.get_provisioning_uri(secret, admin.email)
        backup_codes = MFAManager.generate_backup_codes(10)
        
        # Create MFA record
        user_mfa = UserMFA(
            id=str(uuid.uuid4()),
            user_id=admin.id,
            secret=secret,
            backup_codes=backup_codes,
            is_enabled=False
        )
        db.add(user_mfa)
        db.commit()
        
        print("\n✅ MFA setup initiated")
        print(f"   Secret: {secret}")
        print(f"   QR Code URI: {qr_uri}")
        print(f"\n   Scan this QR code with Google Authenticator or Authy")
        print(f"\n   Backup Codes (save these securely):")
        for i, code in enumerate(backup_codes, 1):
            print(f"   {i}. {code}")
        print("\n   ⚠️  Enable MFA via API after scanning QR code")
    else:
        print("⚠️  MFA not configured. Recommended for admin accounts!")


def validate_configuration():
    """Validate security configuration"""
    print("\n🔍 Validating configuration...")
    
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    issues = []
    warnings = []
    
    # Check SECRET_KEY
    secret_key = os.getenv("SECRET_KEY")
    if not secret_key:
        issues.append("SECRET_KEY not set in environment")
    elif len(secret_key) < 32:
        warnings.append("SECRET_KEY should be at least 32 characters")
    
    # Check OAuth2 configuration
    providers = ["GOOGLE", "GITHUB", "MICROSOFT"]
    oauth_configured = False
    
    for provider in providers:
        client_id = os.getenv(f"{provider}_CLIENT_ID")
        client_secret = os.getenv(f"{provider}_CLIENT_SECRET")
        
        if client_id and client_secret:
            oauth_configured = True
            print(f"   ✅ {provider} OAuth2 configured")
    
    if not oauth_configured:
        warnings.append("No OAuth2 providers configured")
    
    # Check database
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        issues.append("DATABASE_URL not set")
    
    # Report results
    if issues:
        print("\n❌ Configuration Issues:")
        for issue in issues:
            print(f"   - {issue}")
    
    if warnings:
        print("\n⚠️  Configuration Warnings:")
        for warning in warnings:
            print(f"   - {warning}")
    
    if not issues and not warnings:
        print("✅ Configuration valid")
    
    return len(issues) == 0


def generate_env_template():
    """Generate .env.security template"""
    print("\n📝 Generating security configuration template...")
    
    template = f"""# Security Configuration
# Generated on {datetime.now().isoformat()}

# CRITICAL: Change this in production!
SECRET_KEY={generate_secret_key(32)}

# Token Configuration
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
API_KEY_DEFAULT_EXPIRE_DAYS=365

# OAuth2 - Google
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/callback/google

# OAuth2 - GitHub
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret
GITHUB_REDIRECT_URI=http://localhost:8000/auth/callback/github

# OAuth2 - Microsoft
MICROSOFT_CLIENT_ID=your-microsoft-client-id
MICROSOFT_CLIENT_SECRET=your-microsoft-client-secret
MICROSOFT_REDIRECT_URI=http://localhost:8000/auth/callback/microsoft

# Security
ALLOWED_ORIGINS=["http://localhost:3000", "http://localhost:8000"]
ENABLE_HTTPS_ONLY=false  # Set to true in production
SECURE_COOKIES=false     # Set to true in production

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000
ENABLE_RATE_LIMITING=true

# MFA
MFA_ISSUER_NAME=Zakera
REQUIRE_MFA_FOR_ADMINS=true
MFA_BACKUP_CODES_COUNT=10

# Brute Force Protection
MAX_LOGIN_ATTEMPTS=5
LOCKOUT_DURATION_MINUTES=15

# IP Filtering (optional)
IP_WHITELIST=[]  # e.g., ["10.0.0.0/8", "192.168.1.1"]
IP_BLACKLIST=[]  # e.g., ["1.2.3.4"]

# Bot Detection
ENABLE_BOT_DETECTION=false
ALLOW_GOOD_BOTS=true

# Audit Logging
ENABLE_AUDIT_LOGGING=true
AUDIT_LOG_RETENTION_DAYS=90
"""
    
    with open(".env.security", "w") as f:
        f.write(template)
    
    print("✅ Template saved to .env.security")
    print("   Copy relevant settings to your .env file")


def main():
    """Main initialization function"""
    print("="*60)
    print("  Zakera Security System Initialization")
    print("="*60)
    
    # Create tables
    create_tables()
    
    # Create session
    from src.api.database import SessionLocal
    db = SessionLocal()
    
    try:
        # Create admin user
        admin = create_admin_user(db)
        
        # Setup MFA
        setup_mfa_for_admin(db, admin)
        
        # Validate configuration
        valid = validate_configuration()
        
        # Generate template
        generate_env_template()
        
        print("\n" + "="*60)
        if valid:
            print("✅ Security system initialized successfully!")
        else:
            print("⚠️  Security system initialized with warnings")
        print("="*60)
        
        print("\n📚 Next Steps:")
        print("   1. Review and update .env.security")
        print("   2. Copy settings to .env")
        print("   3. Configure OAuth2 providers (optional)")
        print("   4. Enable MFA for admin account")
        print("   5. Run: alembic upgrade head")
        print("   6. Start the application")
        print("\n📖 Documentation: docs/AUTHENTICATION_GUIDE.md")
        
    finally:
        db.close()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Initialization cancelled")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
