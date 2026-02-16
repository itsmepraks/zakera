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
        
        print(\"\\n✅ MFA setup initiated\")\n        print(f\"   Secret: {secret}\")\n        print(f\"   QR Code URI: {qr_uri}\")\n        print(f\"\\n   Scan this QR code with Google Authenticator or Authy\")\n        print(f\"\\n   Backup Codes (save these securely):\")\n        for i, code in enumerate(backup_codes, 1):\n            print(f\"   {i}. {code}\")\n        print(\"\\n   ⚠️  Enable MFA via API after scanning QR code\")\n    else:\n        print(\"⚠️  MFA not configured. Recommended for admin accounts!\")\n\n\ndef validate_configuration():\n    \"\"\"Validate security configuration\"\"\"\n    print(\"\\n🔍 Validating configuration...\")\n    \n    import os\n    from dotenv import load_dotenv\n    load_dotenv()\n    \n    issues = []\n    warnings = []\n    \n    # Check SECRET_KEY\n    secret_key = os.getenv(\"SECRET_KEY\")\n    if not secret_key:\n        issues.append(\"SECRET_KEY not set in environment\")\n    elif len(secret_key) < 32:\n        warnings.append(\"SECRET_KEY should be at least 32 characters\")\n    \n    # Check OAuth2 configuration\n    providers = [\"GOOGLE\", \"GITHUB\", \"MICROSOFT\"]\n    oauth_configured = False\n    \n    for provider in providers:\n        client_id = os.getenv(f\"{provider}_CLIENT_ID\")\n        client_secret = os.getenv(f\"{provider}_CLIENT_SECRET\")\n        \n        if client_id and client_secret:\n            oauth_configured = True\n            print(f\"   ✅ {provider} OAuth2 configured\")\n    \n    if not oauth_configured:\n        warnings.append(\"No OAuth2 providers configured\")\n    \n    # Check database\n    database_url = os.getenv(\"DATABASE_URL\")\n    if not database_url:\n        issues.append(\"DATABASE_URL not set\")\n    \n    # Report results\n    if issues:\n        print(\"\\n❌ Configuration Issues:\")\n        for issue in issues:\n            print(f\"   - {issue}\")\n    \n    if warnings:\n        print(\"\\n⚠️  Configuration Warnings:\")\n        for warning in warnings:\n            print(f\"   - {warning}\")\n    \n    if not issues and not warnings:\n        print(\"✅ Configuration valid\")\n    \n    return len(issues) == 0\n\n\ndef generate_env_template():\n    \"\"\"Generate .env.security template\"\"\"\n    print(\"\\n📝 Generating security configuration template...\")\n    \n    template = f\"\"\"# Security Configuration\n# Generated on {datetime.now().isoformat()}\n\n# CRITICAL: Change this in production!\nSECRET_KEY={generate_secret_key(32)}\n\n# Token Configuration\nACCESS_TOKEN_EXPIRE_MINUTES=15\nREFRESH_TOKEN_EXPIRE_DAYS=7\nAPI_KEY_DEFAULT_EXPIRE_DAYS=365\n\n# OAuth2 - Google\nGOOGLE_CLIENT_ID=your-google-client-id\nGOOGLE_CLIENT_SECRET=your-google-client-secret\nGOOGLE_REDIRECT_URI=http://localhost:8000/auth/callback/google\n\n# OAuth2 - GitHub\nGITHUB_CLIENT_ID=your-github-client-id\nGITHUB_CLIENT_SECRET=your-github-client-secret\nGITHUB_REDIRECT_URI=http://localhost:8000/auth/callback/github\n\n# OAuth2 - Microsoft\nMICROSOFT_CLIENT_ID=your-microsoft-client-id\nMICROSOFT_CLIENT_SECRET=your-microsoft-client-secret\nMICROSOFT_REDIRECT_URI=http://localhost:8000/auth/callback/microsoft\n\n# Security\nALLOWED_ORIGINS=[\"http://localhost:3000\", \"http://localhost:8000\"]\nENABLE_HTTPS_ONLY=false  # Set to true in production\nSECURE_COOKIES=false     # Set to true in production\n\n# Rate Limiting\nRATE_LIMIT_PER_MINUTE=60\nRATE_LIMIT_PER_HOUR=1000\nENABLE_RATE_LIMITING=true\n\n# MFA\nMFA_ISSUER_NAME=Zakera\nREQUIRE_MFA_FOR_ADMINS=true\nMFA_BACKUP_CODES_COUNT=10\n\n# Brute Force Protection\nMAX_LOGIN_ATTEMPTS=5\nLOCKOUT_DURATION_MINUTES=15\n\n# IP Filtering (optional)\nIP_WHITELIST=[]  # e.g., [\"10.0.0.0/8\", \"192.168.1.1\"]\nIP_BLACKLIST=[]  # e.g., [\"1.2.3.4\"]\n\n# Bot Detection\nENABLE_BOT_DETECTION=false\nALLOW_GOOD_BOTS=true\n\n# Audit Logging\nENABLE_AUDIT_LOGGING=true\nAUDIT_LOG_RETENTION_DAYS=90\n\"\"\"\n    \n    with open(\".env.security\", \"w\") as f:\n        f.write(template)\n    \n    print(\"✅ Template saved to .env.security\")\n    print(\"   Copy relevant settings to your .env file\")\n\n\ndef main():\n    \"\"\"Main initialization function\"\"\"\n    print(\"=\"*60)\n    print(\"  Zakera Security System Initialization\")\n    print(\"=\"*60)\n    \n    # Create tables\n    create_tables()\n    \n    # Create session\n    from src.api.database import SessionLocal\n    db = SessionLocal()\n    \n    try:\n        # Create admin user\n        admin = create_admin_user(db)\n        \n        # Setup MFA\n        setup_mfa_for_admin(db, admin)\n        \n        # Validate configuration\n        valid = validate_configuration()\n        \n        # Generate template\n        generate_env_template()\n        \n        print(\"\\n\" + \"=\"*60)\n        if valid:\n            print(\"✅ Security system initialized successfully!\")\n        else:\n            print(\"⚠️  Security system initialized with warnings\")\n        print(\"=\"*60)\n        \n        print(\"\\n📚 Next Steps:\")\n        print(\"   1. Review and update .env.security\")\n        print(\"   2. Copy settings to .env\")\n        print(\"   3. Configure OAuth2 providers (optional)\")\n        print(\"   4. Enable MFA for admin account\")\n        print(\"   5. Run: alembic upgrade head\")\n        print(\"   6. Start the application\")\n        print(\"\\n📖 Documentation: docs/AUTHENTICATION_GUIDE.md\")\n        \n    finally:\n        db.close()\n\n\nif __name__ == \"__main__\":\n    try:\n        main()\n    except KeyboardInterrupt:\n        print(\"\\n\\n⚠️  Initialization cancelled\")\n        sys.exit(1)\n    except Exception as e:\n        print(f\"\\n\\n❌ Error: {e}\")\n        import traceback\n        traceback.print_exc()\n        sys.exit(1)
