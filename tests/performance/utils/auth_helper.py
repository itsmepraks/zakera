"""Authentication Helper for Performance Tests

Handles:
- API key authentication
- JWT token generation
- Session management
- Token refresh
"""

import os
import time
import jwt
import requests
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)


class AuthHelper:
    """Helper for authentication in load tests"""
    
    def __init__(self):
        self.base_url = os.getenv('BASE_URL', 'http://localhost:8000')
        self.api_key = os.getenv('API_KEY')
        self.jwt_secret = os.getenv('JWT_SECRET')
        self.jwt_algorithm = os.getenv('JWT_ALGORITHM', 'HS256')
        self.tokens_cache = {}
    
    def get_api_key(self) -> Optional[str]:
        """Get API key from environment"""
        return self.api_key
    
    def generate_jwt_token(self, user_id: str, expiration: int = 3600) -> str:
        """Generate JWT token for testing
        
        Args:
            user_id: User identifier
            expiration: Token expiration in seconds
        
        Returns:
            JWT token string
        """
        if not self.jwt_secret:
            raise ValueError("JWT_SECRET not configured")
        
        payload = {
            'user_id': user_id,
            'exp': int(time.time()) + expiration,
            'iat': int(time.time())
        }
        
        token = jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
        return token
    
    def login(self, email: str, password: str) -> Optional[Dict]:
        """Perform login and get authentication token
        
        Args:
            email: User email
            password: User password
        
        Returns:
            Dict with access_token and user info, or None on failure
        """
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/auth/login",
                json={'email': email, 'password': password},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                # Cache token
                self.tokens_cache[email] = data.get('access_token')
                return data
            else:
                logger.error(f"Login failed: {response.status_code}")
                return None
        
        except Exception as e:
            logger.error(f"Login error: {e}")
            return None
    
    def get_cached_token(self, email: str) -> Optional[str]:
        """Get cached token for user
        
        Args:
            email: User email
        
        Returns:
            Cached token or None
        """
        return self.tokens_cache.get(email)
    
    def create_test_user(self, email: Optional[str] = None) -> Optional[Dict]:
        """Create a test user account
        
        Args:
            email: User email (generated if not provided)
        
        Returns:
            User data dict or None on failure
        """
        if not email:
            import uuid
            email = f"test_{uuid.uuid4().hex[:8]}@perftest.local"
        
        password = "TestPass123!"
        
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/auth/register",
                json={
                    'email': email,
                    'password': password,
                    'name': 'Performance Test User'
                },
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                data['password'] = password  # Include for login
                return data
            else:
                logger.warning(f"User creation failed: {response.status_code}")
                return None
        
        except Exception as e:
            logger.error(f"User creation error: {e}")
            return None
    
    def verify_token(self, token: str) -> bool:
        """Verify if token is valid
        
        Args:
            token: JWT token to verify
        
        Returns:
            True if valid, False otherwise
        """
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/user/me",
                headers={'Authorization': f'Bearer {token}'},
                timeout=10
            )
            return response.status_code == 200
        
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            return False
    
    def get_auth_headers(self, token: Optional[str] = None) -> Dict[str, str]:
        """Get authorization headers
        
        Args:
            token: Authentication token (uses API key if not provided)
        
        Returns:
            Headers dict
        """
        token = token or self.api_key
        
        if token:
            return {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
        else:
            return {'Content-Type': 'application/json'}
    
    def refresh_token(self, refresh_token: str) -> Optional[str]:
        """Refresh an expired token
        
        Args:
            refresh_token: Refresh token
        
        Returns:
            New access token or None
        """
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/auth/refresh",
                json={'refresh_token': refresh_token},
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json().get('access_token')
            else:
                return None
        
        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            return None
