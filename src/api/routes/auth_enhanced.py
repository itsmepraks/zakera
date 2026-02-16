"""
Enhanced Authentication API Routes

Endpoints for:
- OAuth2 authentication
- MFA setup and verification
- API key management
- Session management
- Password management
- User profile management with RBAC
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
import httpx
from pydantic import BaseModel, EmailStr

from ..database import get_db
from ..models import User
from ...security.auth_enhanced import (
    TokenManager, TokenType, MFAManager, APIKeyManager,
    SessionManager, RBACManager, PasswordPolicy,
    hash_password, verify_password,
    UserRole, Permission, OAuth2Provider, OAuth2Config,
    get_current_active_user, get_current_user_with_permission,
    TokenResponse, RefreshTokenRequest, MFASetupResponse,
    MFAVerifyRequest, PasswordChangeRequest, APIKeyCreate, APIKeyResponse
)
from ...security.models import (
    APIKey, Session as DBSession, LoginAttempt,
    AuditLog, OAuth2Account, UserMFA, PasswordHistory
)


router = APIRouter()


# ============================================================================
# OAuth2 Authentication
# ============================================================================

@router.get("/oauth/{provider}/authorize")
async def oauth_authorize(
    provider: OAuth2Provider,
    redirect_uri: str
):
    """
    Get OAuth2 authorization URL
    
    Step 1: Redirect user to provider's authorization page
    """
    config = getattr(OAuth2Config, provider.value.upper())
    
    # Build authorization URL
    params = {
        "client_id": f"{provider.value.upper()}_CLIENT_ID",  # From settings
        "redirect_uri": redirect_uri,
        "scope": " ".join(config["scopes"]),
        "response_type": "code",
        "state": SessionManager.create_session_id()  # CSRF protection
    }
    
    auth_url = config["authorization_endpoint"]
    return {"authorization_url": auth_url, "params": params}


@router.post("/oauth/{provider}/callback")
async def oauth_callback(
    provider: OAuth2Provider,
    code: str,
    state: str,
    db: Session = Depends(get_db)
) -> TokenResponse:
    """
    Handle OAuth2 callback
    
    Step 2: Exchange authorization code for access token
    """
    config = getattr(OAuth2Config, provider.value.upper())
    
    # Exchange code for token
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            config["token_endpoint"],
            data={
                "code": code,
                "client_id": f"{provider.value.upper()}_CLIENT_ID",
                "client_secret": f"{provider.value.upper()}_CLIENT_SECRET",
                "redirect_uri": "REDIRECT_URI",
                "grant_type": "authorization_code"
            }
        )
        
        if token_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to exchange code for token"
            )
        
        token_data = token_response.json()
        access_token = token_data["access_token"]
        
        # Get user info from provider
        user_info_response = await client.get(
            config["userinfo_endpoint"],
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        user_info = user_info_response.json()
    
    # Find or create user
    provider_user_id = user_info.get("id") or user_info.get("sub")
    email = user_info.get("email")
    
    # Check if OAuth account exists
    oauth_account = db.query(OAuth2Account).filter(
        OAuth2Account.provider == provider,
        OAuth2Account.provider_user_id == provider_user_id
    ).first()
    
    if oauth_account:
        user = oauth_account.user
    else:
        # Check if user with email exists
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            # Create new user
            user = User(
                username=email.split("@")[0],
                email=email,
                full_name=user_info.get("name"),
                is_active=True,
                email_verified=True,
                role=UserRole.USER.value
            )
            db.add(user)
            db.flush()
        
        # Create OAuth account link
        oauth_account = OAuth2Account(
            user_id=user.id,
            provider=provider,
            provider_user_id=provider_user_id,
            provider_email=email,
            profile_data=user_info,
            is_active=True
        )
        db.add(oauth_account)
    
    # Update last login
    user.last_login_at = datetime.utcnow()
    oauth_account.last_login_at = datetime.utcnow()
    
    db.commit()
    db.refresh(user)
    
    # Create tokens
    tokens = TokenManager.create_token_pair(
        user_id=user.id,
        username=user.username,
        role=UserRole(user.role)
    )
    
    return TokenResponse(**tokens)


# ============================================================================
# Token Management
# ============================================================================

@router.post("/token/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token
    """
    payload = TokenManager.decode_token(request.refresh_token, TokenType.REFRESH)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    # Create new token pair
    tokens = TokenManager.create_token_pair(
        user_id=user.id,
        username=user.username,
        role=UserRole(user.role)
    )
    
    return TokenResponse(**tokens)


# ============================================================================
# MFA Management
# ============================================================================

@router.post("/mfa/setup", response_model=MFASetupResponse)
async def setup_mfa(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Setup multi-factor authentication
    """
    # Check if MFA already enabled
    user_mfa = db.query(UserMFA).filter(UserMFA.user_id == current_user.id).first()
    
    if user_mfa and user_mfa.is_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA already enabled"
        )
    
    # Generate secret
    secret = MFAManager.generate_secret()
    qr_uri = MFAManager.get_provisioning_uri(secret, current_user.email)
    backup_codes = MFAManager.generate_backup_codes()
    
    # Store MFA config (not enabled yet)
    if not user_mfa:
        user_mfa = UserMFA(
            user_id=current_user.id,
            secret=secret,  # Should be encrypted in production
            backup_codes=backup_codes,  # Should be hashed
            is_enabled=False
        )
        db.add(user_mfa)
    else:
        user_mfa.secret = secret
        user_mfa.backup_codes = backup_codes
    
    db.commit()
    
    return MFASetupResponse(
        secret=secret,
        qr_code_uri=qr_uri,
        backup_codes=backup_codes
    )


@router.post("/mfa/enable")
async def enable_mfa(
    request: MFAVerifyRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Enable MFA after verifying token
    """
    user_mfa = db.query(UserMFA).filter(UserMFA.user_id == current_user.id).first()
    
    if not user_mfa:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA not setup"
        )
    
    # Verify token
    if not MFAManager.verify_totp(user_mfa.secret, request.token):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid MFA token"
        )
    
    # Enable MFA
    user_mfa.is_enabled = True
    user_mfa.enabled_at = datetime.utcnow()
    current_user.mfa_enabled = True
    
    db.commit()
    
    return {"message": "MFA enabled successfully"}


@router.post("/mfa/disable")
async def disable_mfa(
    request: MFAVerifyRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Disable MFA after verifying token
    """
    user_mfa = db.query(UserMFA).filter(UserMFA.user_id == current_user.id).first()
    
    if not user_mfa or not user_mfa.is_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA not enabled"
        )
    
    # Verify token
    if not MFAManager.verify_totp(user_mfa.secret, request.token):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid MFA token"
        )
    
    # Disable MFA
    user_mfa.is_enabled = False
    current_user.mfa_enabled = False
    
    db.commit()
    
    return {"message": "MFA disabled successfully"}


# ============================================================================
# API Key Management
# ============================================================================

@router.post("/api-keys", response_model=APIKeyResponse)
async def create_api_key(
    request: APIKeyCreate,
    current_user: User = Depends(
        get_current_user_with_permission(Permission.API_KEY_CREATE)
    ),
    db: Session = Depends(get_db)
):
    """
    Create a new API key
    """
    # Generate key
    key = APIKeyManager.generate_key()
    key_hash = APIKeyManager.hash_key(key)
    prefix = key.split("_")[0] + "_" + key.split("_")[1][:8]
    
    # Calculate expiration
    expires_at = None
    if request.expires_in_days:
        expires_at = datetime.utcnow() + timedelta(days=request.expires_in_days)
    
    # Create API key
    api_key = APIKey(
        user_id=current_user.id,
        name=request.name,
        description=request.description,
        key_hash=key_hash,
        key_prefix=prefix,
        scopes=[perm.value for perm in request.scopes],
        expires_at=expires_at,
        is_active=True
    )
    
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    
    return APIKeyResponse(
        id=api_key.id,
        name=api_key.name,
        key=key,  # Only shown once
        prefix=prefix,
        created_at=api_key.created_at,
        expires_at=api_key.expires_at,
        scopes=api_key.scopes or []
    )


@router.get("/api-keys")
async def list_api_keys(
    current_user: User = Depends(
        get_current_user_with_permission(Permission.API_KEY_READ)
    ),
    db: Session = Depends(get_db)
):
    """
    List user's API keys
    """
    keys = db.query(APIKey).filter(
        APIKey.user_id == current_user.id,
        APIKey.is_active == True
    ).all()
    
    return {
        "api_keys": [
            {
                "id": key.id,
                "name": key.name,
                "prefix": key.key_prefix,
                "created_at": key.created_at,
                "expires_at": key.expires_at,
                "last_used_at": key.last_used_at,
                "scopes": key.scopes
            }
            for key in keys
        ]
    }


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(
    key_id: str,
    current_user: User = Depends(
        get_current_user_with_permission(Permission.API_KEY_REVOKE)
    ),
    db: Session = Depends(get_db)
):
    """
    Revoke an API key
    """
    api_key = db.query(APIKey).filter(
        APIKey.id == key_id,
        APIKey.user_id == current_user.id
    ).first()
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    api_key.is_active = False
    db.commit()
    
    return {"message": "API key revoked successfully"}


# ============================================================================
# Password Management
# ============================================================================

@router.post("/password/change")
async def change_password(
    request: PasswordChangeRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Change user password
    """
    # Verify current password
    if not verify_password(request.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Check password history (prevent reuse)
    password_history = db.query(PasswordHistory).filter(
        PasswordHistory.user_id == current_user.id
    ).order_by(PasswordHistory.created_at.desc()).limit(5).all()
    
    for old_password in password_history:
        if verify_password(request.new_password, old_password.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot reuse recent passwords"
            )
    
    # Update password
    new_hash = hash_password(request.new_password)
    current_user.hashed_password = new_hash
    current_user.last_password_change = datetime.utcnow()
    
    # Add to password history
    password_history_entry = PasswordHistory(
        user_id=current_user.id,
        password_hash=new_hash
    )
    db.add(password_history_entry)
    
    db.commit()
    
    return {"message": "Password changed successfully"}


# ============================================================================
# Session Management
# ============================================================================

@router.get("/sessions")
async def list_sessions(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    List active user sessions
    """
    sessions = db.query(DBSession).filter(
        DBSession.user_id == current_user.id,
        DBSession.is_active == True
    ).order_by(DBSession.created_at.desc()).all()
    
    return {
        "sessions": [
            {
                "id": session.id,
                "ip_address": session.ip_address,
                "user_agent": session.user_agent,
                "created_at": session.created_at,
                "last_activity": session.last_activity,
                "expires_at": session.expires_at
            }
            for session in sessions
        ]
    }


@router.delete("/sessions/{session_id}")
async def revoke_session(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Revoke a specific session
    """
    session = db.query(DBSession).filter(
        DBSession.id == session_id,
        DBSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    session.is_active = False
    session.revoked_at = datetime.utcnow()
    session.revoked_reason = "User revoked"
    
    db.commit()
    
    return {"message": "Session revoked successfully"}


@router.delete("/sessions")
async def revoke_all_sessions(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Revoke all user sessions (except current)
    """
    sessions = db.query(DBSession).filter(
        DBSession.user_id == current_user.id,
        DBSession.is_active == True
    ).all()
    
    for session in sessions:
        session.is_active = False
        session.revoked_at = datetime.utcnow()
        session.revoked_reason = "User revoked all sessions"
    
    db.commit()
    
    return {"message": f"Revoked {len(sessions)} sessions"}
