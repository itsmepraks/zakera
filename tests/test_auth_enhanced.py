"""
Comprehensive Tests for Enhanced Authentication System
"""

import pytest
from datetime import datetime, timedelta
from src.security.auth_enhanced import (
    TokenManager, TokenType, MFAManager, APIKeyManager,
    RBACManager, PasswordPolicy, hash_password, verify_password,
    UserRole, Permission, OAuth2Provider
)


class TestPasswordPolicy:
    """Test password policy validation"""
    
    def test_valid_password(self):
        """Test valid password"""
        valid, errors = PasswordPolicy.validate("SecurePass123!")
        assert valid is True
        assert len(errors) == 0
    
    def test_too_short(self):
        """Test password too short"""
        valid, errors = PasswordPolicy.validate("Pass1!")
        assert valid is False
        assert any("at least 8 characters" in err for err in errors)
    
    def test_missing_uppercase(self):
        """Test missing uppercase"""
        valid, errors = PasswordPolicy.validate("password123!")
        assert valid is False
        assert any("uppercase" in err for err in errors)
    
    def test_missing_lowercase(self):
        """Test missing lowercase"""
        valid, errors = PasswordPolicy.validate("PASSWORD123!")
        assert valid is False
        assert any("lowercase" in err for err in errors)
    
    def test_missing_digit(self):
        """Test missing digit"""
        valid, errors = PasswordPolicy.validate("SecurePass!")
        assert valid is False
        assert any("digit" in err for err in errors)
    
    def test_missing_special(self):
        """Test missing special character"""
        valid, errors = PasswordPolicy.validate("SecurePass123")
        assert valid is False
        assert any("special character" in err for err in errors)


class TestPasswordHashing:
    """Test password hashing"""
    
    def test_hash_password(self):
        """Test hashing a password"""
        password = "SecurePass123!"
        hashed = hash_password(password)
        
        assert hashed != password
        assert len(hashed) > 0
        assert hashed.startswith("$2b$")
    
    def test_verify_password(self):
        """Test password verification"""
        password = "SecurePass123!"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True
        assert verify_password("WrongPass123!", hashed) is False
    
    def test_hash_invalid_password(self):
        """Test hashing invalid password raises error"""
        with pytest.raises(ValueError):
            hash_password("weak")


class TestTokenManager:
    """Test token management"""
    
    def test_create_access_token(self):
        """Test creating access token"""
        token = TokenManager.create_token(
            data={"sub": "user123", "username": "test"},
            token_type=TokenType.ACCESS
        )
        
        assert len(token) > 0
        assert isinstance(token, str)
    
    def test_create_refresh_token(self):
        """Test creating refresh token"""
        token = TokenManager.create_token(
            data={"sub": "user123"},
            token_type=TokenType.REFRESH
        )
        
        assert len(token) > 0
    
    def test_decode_token(self):
        """Test decoding token"""
        data = {"sub": "user123", "username": "test"}
        token = TokenManager.create_token(data, TokenType.ACCESS)
        
        decoded = TokenManager.decode_token(token, TokenType.ACCESS)
        
        assert decoded is not None
        assert decoded["sub"] == "user123"
        assert decoded["username"] == "test"
        assert decoded["type"] == TokenType.ACCESS.value
    
    def test_decode_wrong_type(self):
        """Test decoding token with wrong type"""
        token = TokenManager.create_token(
            {"sub": "user123"},
            TokenType.ACCESS
        )
        
        decoded = TokenManager.decode_token(token, TokenType.REFRESH)
        assert decoded is None
    
    def test_create_token_pair(self):
        """Test creating token pair"""
        tokens = TokenManager.create_token_pair(
            user_id="user123",
            username="test",
            role=UserRole.USER
        )
        
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert len(tokens["access_token"]) > 0
        assert len(tokens["refresh_token"]) > 0


class TestMFAManager:
    """Test MFA management"""
    
    def test_generate_secret(self):
        """Test generating MFA secret"""
        secret = MFAManager.generate_secret()
        
        assert len(secret) == 32
        assert secret.isalnum()
    
    def test_get_provisioning_uri(self):
        """Test getting provisioning URI"""
        secret = MFAManager.generate_secret()
        uri = MFAManager.get_provisioning_uri(secret, "test@example.com")
        
        assert uri.startswith("otpauth://totp/")
        assert "test@example.com" in uri
        assert "Zakera" in uri
    
    def test_verify_totp(self):
        """Test TOTP verification"""
        import pyotp
        
        secret = MFAManager.generate_secret()
        totp = pyotp.TOTP(secret)
        token = totp.now()
        
        assert MFAManager.verify_totp(secret, token) is True
        assert MFAManager.verify_totp(secret, "000000") is False
    
    def test_generate_backup_codes(self):
        """Test generating backup codes"""
        codes = MFAManager.generate_backup_codes(10)
        
        assert len(codes) == 10
        assert all(len(code) == 9 for code in codes)  # 8 chars + hyphen
        assert len(set(codes)) == 10  # All unique


class TestAPIKeyManager:
    """Test API key management"""
    
    def test_generate_key(self):
        """Test generating API key"""
        key = APIKeyManager.generate_key()
        
        assert key.startswith("zk_")
        assert len(key) > 10
    
    def test_hash_key(self):
        """Test hashing API key"""
        key = APIKeyManager.generate_key()
        hashed = APIKeyManager.hash_key(key)
        
        assert len(hashed) == 64  # SHA-256 hex
        assert hashed != key
    
    def test_verify_key(self):
        """Test verifying API key"""
        key = APIKeyManager.generate_key()
        hashed = APIKeyManager.hash_key(key)
        
        assert APIKeyManager.verify_key(key, hashed) is True
        assert APIKeyManager.verify_key("wrong_key", hashed) is False


class TestRBACManager:
    """Test RBAC system"""
    
    def test_super_admin_has_all_permissions(self):
        """Test super admin has all permissions"""
        for permission in Permission:
            assert RBACManager.has_permission(UserRole.SUPER_ADMIN, permission)
    
    def test_user_permissions(self):
        """Test user role permissions"""
        # User can read and update themselves
        assert RBACManager.has_permission(UserRole.USER, Permission.USER_READ)
        assert RBACManager.has_permission(UserRole.USER, Permission.USER_UPDATE)
        
        # User cannot delete users
        assert not RBACManager.has_permission(UserRole.USER, Permission.USER_DELETE)
        
        # User cannot access admin functions
        assert not RBACManager.has_permission(UserRole.USER, Permission.ADMIN_ACCESS)
    
    def test_admin_permissions(self):
        """Test admin role permissions"""
        # Admin can manage users
        assert RBACManager.has_permission(UserRole.ADMIN, Permission.USER_READ)
        assert RBACManager.has_permission(UserRole.ADMIN, Permission.USER_UPDATE)
        
        # Admin can access admin panel
        assert RBACManager.has_permission(UserRole.ADMIN, Permission.ADMIN_ACCESS)
        
        # Admin cannot delete users (only super admin)
        assert not RBACManager.has_permission(UserRole.ADMIN, Permission.USER_DELETE)
    
    def test_viewer_permissions(self):
        """Test viewer role permissions"""
        # Viewer can only read
        assert RBACManager.has_permission(UserRole.VIEWER, Permission.USER_READ)
        assert RBACManager.has_permission(UserRole.VIEWER, Permission.CONVERSATION_READ)
        
        # Viewer cannot modify
        assert not RBACManager.has_permission(UserRole.VIEWER, Permission.CONVERSATION_CREATE)
        assert not RBACManager.has_permission(UserRole.VIEWER, Permission.TOOL_EXECUTE)
    
    def test_get_role_permissions(self):
        """Test getting all permissions for a role"""
        perms = RBACManager.get_role_permissions(UserRole.USER)
        
        assert len(perms) > 0
        assert Permission.CONVERSATION_CREATE in perms
        assert Permission.ADMIN_ACCESS not in perms
    
    def test_has_any_permission(self):
        """Test checking any permission"""
        result = RBACManager.has_any_permission(
            UserRole.USER,
            [Permission.ADMIN_ACCESS, Permission.CONVERSATION_CREATE]
        )
        assert result is True  # Has CONVERSATION_CREATE
    
    def test_has_all_permissions(self):
        """Test checking all permissions"""
        result = RBACManager.has_all_permissions(
            UserRole.USER,
            [Permission.USER_READ, Permission.CONVERSATION_CREATE]
        )
        assert result is True
        
        result = RBACManager.has_all_permissions(
            UserRole.USER,
            [Permission.USER_READ, Permission.ADMIN_ACCESS]
        )
        assert result is False


class TestUserRoles:
    """Test user role enumeration"""
    
    def test_role_values(self):
        """Test role values"""
        assert UserRole.SUPER_ADMIN.value == "super_admin"
        assert UserRole.ADMIN.value == "admin"
        assert UserRole.USER.value == "user"
    
    def test_role_from_string(self):
        """Test creating role from string"""
        role = UserRole("admin")
        assert role == UserRole.ADMIN


class TestPermissions:
    """Test permission enumeration"""
    
    def test_permission_values(self):
        """Test permission values"""
        assert Permission.USER_CREATE.value == "user:create"
        assert Permission.CONVERSATION_READ.value == "conversation:read"
        assert Permission.ADMIN_ACCESS.value == "admin:access"
    
    def test_all_permissions_exist(self):
        """Test all expected permissions exist"""
        permissions = list(Permission)
        assert len(permissions) >= 20


class TestOAuth2Provider:
    """Test OAuth2 provider enum"""
    
    def test_provider_values(self):
        """Test provider values"""
        assert OAuth2Provider.GOOGLE.value == "google"
        assert OAuth2Provider.GITHUB.value == "github"
        assert OAuth2Provider.MICROSOFT.value == "microsoft"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
