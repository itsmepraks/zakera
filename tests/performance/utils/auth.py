"""Authentication helper for performance tests."""

import time
from typing import Optional

from locust.clients import HttpSession

from ..config import config


class AuthHelper:
    """Helper class for managing authentication in load tests."""
    
    def __init__(self, client: HttpSession):
        self.client = client
        self.token: Optional[str] = None
        self.token_expiry: float = 0
    
    def login(self, username: str = "test_user", password: str = "test_pass") -> str:
        """Login and get access token.
        
        Args:
            username: Username for authentication
            password: Password for authentication
            
        Returns:
            Access token
        """
        # Check if token is still valid
        if self.token and time.time() < self.token_expiry:
            return self.token
        
        # Login to get new token
        response = self.client.post(
            config.ENDPOINTS["auth"],
            json={
                "username": username,
                "password": password
            },
            catch_response=True
        )
        
        if response.status_code == 200:
            data = response.json()
            self.token = data.get("access_token") or config.API_KEY
            # Token expires in 1 hour
            self.token_expiry = time.time() + 3600
            return self.token
        else:
            # Fallback to configured API key
            self.token = config.API_KEY
            return self.token
    
    def get_headers(self) -> dict:
        """Get authentication headers.
        
        Returns:
            Headers dict with authorization
        """
        token = self.login()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    def refresh_token(self) -> str:
        """Force token refresh.
        
        Returns:
            New access token
        """
        self.token = None
        self.token_expiry = 0
        return self.login()
