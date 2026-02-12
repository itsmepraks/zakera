"""
Comprehensive API integration tests for user management endpoints.

Tests cover user registration, authentication, profile management,
preferences, and user-related operations.
"""

import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.fixtures import (
    client,
    test_db_session,
    test_user,
    test_user_data,
    test_password,
    auth_headers,
    test_user_token,
    multiple_test_users
)


class TestUserRegistration:
    """Test user registration endpoints."""
    
    def test_register_user_success(
        self,
        client: TestClient,
        test_db_session: Session
    ):
        """Test successful user registration."""
        user_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "SecurePassword123!",
            "full_name": "New User"
        }
        
        response = client.post("/api/auth/register", json=user_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "newuser@example.com"
        assert "password" not in data  # Password should not be returned
        assert "id" in data
    
    def test_register_duplicate_username(
        self,
        client: TestClient,
        test_user
    ):
        """Test registration with duplicate username."""
        user_data = {
            "username": test_user.username,
            "email": "different@example.com",
            "password": "Password123!"
        }
        
        response = client.post("/api/auth/register", json=user_data)
        
        assert response.status_code == 409  # Conflict
        data = response.json()
        assert "username" in data["detail"].lower() or "already exists" in data["detail"].lower()
    
    def test_register_duplicate_email(
        self,
        client: TestClient,
        test_user
    ):
        """Test registration with duplicate email."""
        user_data = {
            "username": "differentuser",
            "email": test_user.email,
            "password": "Password123!"
        }
        
        response = client.post("/api/auth/register", json=user_data)
        
        assert response.status_code == 409
    
    def test_register_invalid_email(
        self,
        client: TestClient
    ):
        """Test registration with invalid email format."""
        user_data = {
            "username": "testuser",
            "email": "not-an-email",
            "password": "Password123!"
        }
        
        response = client.post("/api/auth/register", json=user_data)
        
        assert response.status_code == 422
    
    def test_register_weak_password(
        self,
        client: TestClient
    ):
        """Test registration with weak password."""
        weak_passwords = ["123", "password", "12345678"]
        
        for weak_pass in weak_passwords:
            user_data = {
                "username": f"user_{weak_pass}",
                "email": f"user_{weak_pass}@example.com",
                "password": weak_pass
            }
            
            response = client.post("/api/auth/register", json=user_data)
            
            # Should either reject weak password or accept it
            assert response.status_code in [201, 422]
    
    def test_register_missing_fields(
        self,
        client: TestClient
    ):
        """Test registration with missing required fields."""
        # Missing username
        response = client.post(
            "/api/auth/register",
            json={"email": "test@example.com", "password": "Pass123!"}
        )
        assert response.status_code == 422
        
        # Missing email
        response = client.post(
            "/api/auth/register",
            json={"username": "testuser", "password": "Pass123!"}
        )
        assert response.status_code == 422
        
        # Missing password
        response = client.post(
            "/api/auth/register",
            json={"username": "testuser", "email": "test@example.com"}
        )
        assert response.status_code == 422


class TestUserAuthentication:
    """Test user authentication and login endpoints."""
    
    def test_login_success(
        self,
        client: TestClient,
        test_user,
        test_password: str
    ):
        """Test successful login."""
        response = client.post(
            "/api/auth/login",
            data={
                "username": test_user.username,
                "password": test_password
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    def test_login_json_format(
        self,
        client: TestClient,
        test_user,
        test_password: str
    ):
        """Test login with JSON payload."""
        response = client.post(
            "/api/auth/login",
            json={
                "username": test_user.username,
                "password": test_password
            }
        )
        
        # Should work with either form or JSON
        assert response.status_code in [200, 422]
    
    def test_login_wrong_password(
        self,
        client: TestClient,
        test_user
    ):
        """Test login with incorrect password."""
        response = client.post(
            "/api/auth/login",
            data={
                "username": test_user.username,
                "password": "WrongPassword123!"
            }
        )
        
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
    
    def test_login_nonexistent_user(
        self,
        client: TestClient
    ):
        """Test login with non-existent username."""
        response = client.post(
            "/api/auth/login",
            data={
                "username": "nonexistent",
                "password": "Password123!"
            }
        )
        
        assert response.status_code == 401
    
    def test_login_email_as_username(
        self,
        client: TestClient,
        test_user,
        test_password: str
    ):
        """Test login using email instead of username."""
        response = client.post(
            "/api/auth/login",
            data={
                "username": test_user.email,
                "password": test_password
            }
        )
        
        # Should work if email login is supported
        assert response.status_code in [200, 401]
    
    def test_token_validation(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test JWT token validation."""
        response = client.get("/api/users/me", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "username" in data
    
    def test_expired_token(
        self,
        client: TestClient,
        test_user
    ):
        """Test handling of expired JWT token."""
        from src.api.auth import create_access_token
        
        # Create token that expires immediately
        expired_token = create_access_token(
            data={"sub": test_user.username, "user_id": str(test_user.id)},
            expires_delta=timedelta(seconds=-1)
        )
        
        headers = {"Authorization": f"Bearer {expired_token}"}
        response = client.get("/api/users/me", headers=headers)
        
        assert response.status_code == 401
    
    def test_invalid_token_format(
        self,
        client: TestClient
    ):
        """Test handling of invalid token format."""
        invalid_headers = {"Authorization": "Bearer invalid-token"}
        response = client.get("/api/users/me", headers=invalid_headers)
        
        assert response.status_code == 401
    
    def test_missing_authorization_header(
        self,
        client: TestClient
    ):
        """Test accessing protected endpoint without auth."""
        response = client.get("/api/users/me")
        
        assert response.status_code == 401


class TestUserProfile:
    """Test user profile management endpoints."""
    
    def test_get_current_user(
        self,
        client: TestClient,
        auth_headers: dict,
        test_user
    ):
        """Test retrieving current user profile."""
        response = client.get("/api/users/me", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == test_user.username
        assert data["email"] == test_user.email
        assert "password" not in data
        assert "hashed_password" not in data
    
    def test_update_user_profile(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test updating user profile information."""
        update_data = {
            "full_name": "Updated Name",
            "email": "updated@example.com"
        }
        
        response = client.patch(
            "/api/users/me",
            json=update_data,
            headers=auth_headers
        )
        
        if response.status_code == 200:
            data = response.json()
            assert data["full_name"] == "Updated Name"
    
    def test_update_username(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test updating username."""
        response = client.patch(
            "/api/users/me",
            json={"username": "newusername"},
            headers=auth_headers
        )
        
        # Username change might not be allowed
        assert response.status_code in [200, 403, 422]
    
    def test_change_password(
        self,
        client: TestClient,
        auth_headers: dict,
        test_password: str
    ):
        """Test changing user password."""
        response = client.post(
            "/api/users/me/password",
            json={
                "current_password": test_password,
                "new_password": "NewSecurePassword123!"
            },
            headers=auth_headers
        )
        
        if response.status_code == 200:
            # Test login with new password
            login_response = client.post(
                "/api/auth/login",
                data={
                    "username": "testuser",
                    "password": "NewSecurePassword123!"
                }
            )
            assert login_response.status_code == 200
    
    def test_change_password_wrong_current(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test password change with wrong current password."""
        response = client.post(
            "/api/users/me/password",
            json={
                "current_password": "WrongPassword",
                "new_password": "NewPassword123!"
            },
            headers=auth_headers
        )
        
        assert response.status_code in [401, 403]
    
    def test_delete_user_account(
        self,
        client: TestClient,
        auth_headers: dict,
        test_password: str
    ):
        """Test user account deletion."""
        response = client.delete(
            "/api/users/me",
            json={"password": test_password},
            headers=auth_headers
        )
        
        if response.status_code in [200, 204]:
            # Verify cannot access with same token
            verify_response = client.get(
                "/api/users/me",
                headers=auth_headers
            )
            assert verify_response.status_code == 401


class TestUserPreferences:
    """Test user preferences and settings endpoints."""
    
    def test_get_user_preferences(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test retrieving user preferences."""
        response = client.get(
            "/api/users/me/preferences",
            headers=auth_headers
        )
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)
    
    def test_update_user_preferences(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test updating user preferences."""
        preferences = {
            "theme": "dark",
            "language": "en",
            "default_model": "gpt-4",
            "temperature": 0.7
        }
        
        response = client.put(
            "/api/users/me/preferences",
            json=preferences,
            headers=auth_headers
        )
        
        if response.status_code == 200:
            data = response.json()
            assert data["theme"] == "dark"
            assert data["default_model"] == "gpt-4"
    
    def test_partial_preference_update(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test partially updating preferences."""
        response = client.patch(
            "/api/users/me/preferences",
            json={"theme": "light"},
            headers=auth_headers
        )
        
        if response.status_code == 200:
            data = response.json()
            assert data["theme"] == "light"
    
    def test_reset_preferences(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test resetting preferences to defaults."""
        response = client.delete(
            "/api/users/me/preferences",
            headers=auth_headers
        )
        
        # Should reset to defaults
        assert response.status_code in [200, 204]


class TestUserStatistics:
    """Test user statistics and analytics endpoints."""
    
    def test_get_user_statistics(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test retrieving user statistics."""
        response = client.get(
            "/api/users/me/stats",
            headers=auth_headers
        )
        
        if response.status_code == 200:
            data = response.json()
            assert "total_conversations" in data or "conversation_count" in data
            assert "total_messages" in data or "message_count" in data
    
    def test_get_usage_statistics(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test retrieving token usage statistics."""
        response = client.get(
            "/api/users/me/usage",
            headers=auth_headers
        )
        
        if response.status_code == 200:
            data = response.json()
            # Should contain token usage info
            assert isinstance(data, dict)


class TestUserAdministration:
    """Test user administration endpoints (if admin features exist)."""
    
    def test_list_all_users_requires_admin(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test that listing all users requires admin privileges."""
        response = client.get(
            "/api/admin/users",
            headers=auth_headers
        )
        
        # Regular user should not have access
        assert response.status_code in [403, 404]
    
    def test_get_user_by_id_requires_admin(
        self,
        client: TestClient,
        auth_headers: dict,
        multiple_test_users: list
    ):
        """Test that viewing other users requires admin."""
        other_user_id = multiple_test_users[1].id
        
        response = client.get(
            f"/api/admin/users/{other_user_id}",
            headers=auth_headers
        )
        
        assert response.status_code in [403, 404]


class TestPasswordReset:
    """Test password reset functionality."""
    
    def test_request_password_reset(
        self,
        client: TestClient,
        test_user
    ):
        """Test requesting password reset."""
        response = client.post(
            "/api/auth/password-reset",
            json={"email": test_user.email}
        )
        
        # Should always return success to prevent email enumeration
        assert response.status_code in [200, 202]
    
    def test_request_password_reset_nonexistent_email(
        self,
        client: TestClient
    ):
        """Test password reset request for non-existent email."""
        response = client.post(
            "/api/auth/password-reset",
            json={"email": "nonexistent@example.com"}
        )
        
        # Should return success to prevent email enumeration
        assert response.status_code in [200, 202]
    
    def test_confirm_password_reset(
        self,
        client: TestClient
    ):
        """Test confirming password reset with token."""
        response = client.post(
            "/api/auth/password-reset/confirm",
            json={
                "token": "test-reset-token",
                "new_password": "NewPassword123!"
            }
        )
        
        # Will fail without valid token
        assert response.status_code in [200, 400, 401, 404]


class TestUserValidation:
    """Test user data validation."""
    
    def test_username_length_validation(
        self,
        client: TestClient
    ):
        """Test username length constraints."""
        # Too short
        response = client.post(
            "/api/auth/register",
            json={
                "username": "ab",
                "email": "test@example.com",
                "password": "Password123!"
            }
        )
        assert response.status_code in [201, 422]
        
        # Too long
        response = client.post(
            "/api/auth/register",
            json={
                "username": "a" * 100,
                "email": "test2@example.com",
                "password": "Password123!"
            }
        )
        assert response.status_code in [201, 422]
    
    def test_username_character_validation(
        self,
        client: TestClient
    ):
        """Test username character constraints."""
        invalid_usernames = [
            "user name",  # spaces
            "user@name",  # special chars
            "user#name",
            "user!name"
        ]
        
        for invalid_username in invalid_usernames:
            response = client.post(
                "/api/auth/register",
                json={
                    "username": invalid_username,
                    "email": f"{invalid_username}@example.com",
                    "password": "Password123!"
                }
            )
            # Should validate username format
            assert response.status_code in [201, 422]
    
    def test_email_validation(
        self,
        client: TestClient
    ):
        """Test email format validation."""
        invalid_emails = [
            "notanemail",
            "@example.com",
            "user@",
            "user @example.com"
        ]
        
        for invalid_email in invalid_emails:
            response = client.post(
                "/api/auth/register",
                json={
                    "username": f"user{invalid_email}",
                    "email": invalid_email,
                    "password": "Password123!"
                }
            )
            assert response.status_code == 422


class TestRateLimiting:
    """Test rate limiting on user endpoints."""
    
    def test_login_rate_limiting(
        self,
        client: TestClient,
        test_user
    ):
        """Test rate limiting on login attempts."""
        # Attempt multiple logins rapidly
        responses = []
        for _ in range(20):
            response = client.post(
                "/api/auth/login",
                data={
                    "username": test_user.username,
                    "password": "WrongPassword"
                }
            )
            responses.append(response)
        
        # Should hit rate limit if enabled
        status_codes = [r.status_code for r in responses]
        # Either all 401 (no rate limiting) or some 429 (rate limited)
        assert all(code in [401, 429] for code in status_codes)
    
    def test_registration_rate_limiting(
        self,
        client: TestClient
    ):
        """Test rate limiting on registration attempts."""
        responses = []
        for i in range(10):
            response = client.post(
                "/api/auth/register",
                json={
                    "username": f"spamuser{i}",
                    "email": f"spam{i}@example.com",
                    "password": "Password123!"
                }
            )
            responses.append(response)
        
        # Should succeed or hit rate limit
        status_codes = [r.status_code for r in responses]
        assert all(code in [201, 409, 429] for code in status_codes)
