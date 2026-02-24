"""Integration tests for WebSocket real-time messaging."""

import pytest
import asyncio
import json
from typing import List
from fastapi.testclient import TestClient
from fastapi import WebSocket

from src.api.main import app


@pytest.fixture
def test_client():
    """Create test client."""
    return TestClient(app)


class TestWebSocketConnection:
    """Test WebSocket connection management."""

    def test_connect_websocket(self, test_client):
        """Test establishing WebSocket connection."""
        with test_client.websocket_connect("/ws/chat") as websocket:
            # Should connect successfully
            assert websocket is not None

    def test_authentication_required(self, test_client):
        """Test that authentication is required."""
        with pytest.raises(Exception):
            # Should fail without auth token
            with test_client.websocket_connect("/ws/chat") as websocket:
                pass

    def test_connect_with_auth(self, test_client):
        """Test connecting with authentication."""
        # Get auth token
        auth_response = test_client.post(
            "/api/v1/auth/login",
            json={"username": "test", "password": "test"}
        )
        token = auth_response.json()["token"]
        
        # Connect with token
        with test_client.websocket_connect(
            f"/ws/chat?token={token}"
        ) as websocket:
            assert websocket is not None


class TestRealtimeMessaging:
    """Test real-time message exchange."""

    def test_send_receive_message(self, test_client):
        """Test sending and receiving messages."""
        token = self._get_auth_token(test_client)
        
        with test_client.websocket_connect(
            f"/ws/chat?token={token}"
        ) as websocket:
            # Send message
            message = {
                "type": "message",
                "conversation_id": "test_conv",
                "content": "Hello WebSocket!",
                "role": "user"
            }
            websocket.send_json(message)
            
            # Receive response
            response = websocket.receive_json()
            
            assert response["type"] == "message"
            assert "content" in response
            assert response["role"] == "assistant"

    def test_streaming_response(self, test_client):
        """Test streaming response chunks."""
        token = self._get_auth_token(test_client)
        
        with test_client.websocket_connect(
            f"/ws/chat?token={token}"
        ) as websocket:
            # Send message with streaming
            message = {
                "type": "message",
                "conversation_id": "test_conv",
                "content": "Tell me a story",
                "stream": True
            }
            websocket.send_json(message)
            
            # Collect streamed chunks
            chunks = []
            while True:
                response = websocket.receive_json()
                
                if response["type"] == "chunk":
                    chunks.append(response["content"])
                elif response["type"] == "done":
                    break
            
            # Should have received multiple chunks
            assert len(chunks) > 1
            # Chunks should form complete message
            full_message = "".join(chunks)
            assert len(full_message) > 0

    def test_typing_indicator(self, test_client):
        """Test typing indicator."""
        token = self._get_auth_token(test_client)
        
        with test_client.websocket_connect(
            f"/ws/chat?token={token}"
        ) as websocket:
            # Send message
            websocket.send_json({
                "type": "message",
                "conversation_id": "test_conv",
                "content": "Test"
            })
            
            # Should receive typing indicator first
            response = websocket.receive_json()
            assert response["type"] == "typing"
            assert response["is_typing"] is True
            
            # Then actual message
            response = websocket.receive_json()
            assert response["type"] == "message"

    @staticmethod
    def _get_auth_token(client: TestClient) -> str:
        """Helper to get auth token."""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "test", "password": "test"}
        )
        return response.json()["token"]


class TestMultipleConnections:
    """Test handling multiple WebSocket connections."""

    def test_multiple_clients(self, test_client):
        """Test multiple clients connecting simultaneously."""
        token = self._get_auth_token(test_client)
        
        # Connect multiple clients
        connections = []
        for i in range(5):
            ws = test_client.websocket_connect(
                f"/ws/chat?token={token}&client_id=client_{i}"
            )
            connections.append(ws.__enter__())
        
        try:
            # Send message from each client
            for i, ws in enumerate(connections):
                ws.send_json({
                    "type": "message",
                    "content": f"Message from client {i}"
                })
                
                # Should receive response
                response = ws.receive_json()
                assert "content" in response
        
        finally:
            # Close all connections
            for ws in connections:
                ws.__exit__(None, None, None)

    @staticmethod
    def _get_auth_token(client: TestClient) -> str:
        """Helper to get auth token."""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "test", "password": "test"}
        )
        return response.json()["token"]


class TestErrorHandling:
    """Test WebSocket error handling."""

    def test_invalid_message_format(self, test_client):
        """Test handling invalid message format."""
        token = self._get_auth_token(test_client)
        
        with test_client.websocket_connect(
            f"/ws/chat?token={token}"
        ) as websocket:
            # Send invalid message
            websocket.send_text("invalid json")
            
            # Should receive error
            response = websocket.receive_json()
            assert response["type"] == "error"
            assert "message" in response

    def test_connection_timeout(self, test_client):
        """Test connection timeout."""
        token = self._get_auth_token(test_client)
        
        with test_client.websocket_connect(
            f"/ws/chat?token={token}"
        ) as websocket:
            # Send message and wait
            websocket.send_json({
                "type": "message",
                "content": "Test"
            })
            
            # Should receive response within timeout
            import time
            start = time.time()
            response = websocket.receive_json(timeout=30)
            elapsed = time.time() - start
            
            assert elapsed < 30
            assert response is not None

    @staticmethod
    def _get_auth_token(client: TestClient) -> str:
        """Helper to get auth token."""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "test", "password": "test"}
        )
        return response.json()["token"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
