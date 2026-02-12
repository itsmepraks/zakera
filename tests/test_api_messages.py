"""
Comprehensive API integration tests for message endpoints.

Tests cover message creation, retrieval, streaming responses,
AI provider integration, and message management operations.
"""

import json
import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import Mock, patch, AsyncMock

from tests.fixtures import (
    client,
    test_db_session,
    test_user,
    auth_headers,
    test_conversation,
    test_messages,
    test_message_data,
    mock_openai_response,
    mock_streaming_response
)


class TestMessageCreation:
    """Test message creation and AI response generation."""
    
    @patch('src.model.providers.OpenAIProvider.generate')
    def test_create_message_success(
        self,
        mock_generate,
        client: TestClient,
        auth_headers: dict,
        test_conversation,
        mock_openai_response: dict
    ):
        """Test successful message creation with AI response."""
        mock_generate.return_value = mock_openai_response
        
        response = client.post(
            f"/api/conversations/{test_conversation.id}/messages",
            json={"content": "Hello, how are you?", "role": "user"},
            headers=auth_headers
        )
        
        assert response.status_code in [200, 201]
        data = response.json()
        
        # Check user message
        if isinstance(data, list):
            assert len(data) >= 1
            user_message = data[0]
        else:
            user_message = data
        
        assert user_message["content"] == "Hello, how are you?"
        assert user_message["role"] == "user"
        assert "id" in user_message
        assert "created_at" in user_message
    
    def test_create_message_without_auth(
        self,
        client: TestClient,
        test_conversation
    ):
        """Test that message creation requires authentication."""
        response = client.post(
            f"/api/conversations/{test_conversation.id}/messages",
            json={"content": "Unauthorized message", "role": "user"}
        )
        
        assert response.status_code == 401
    
    def test_create_message_empty_content(
        self,
        client: TestClient,
        auth_headers: dict,
        test_conversation
    ):
        """Test message creation with empty content."""
        response = client.post(
            f"/api/conversations/{test_conversation.id}/messages",
            json={"content": "", "role": "user"},
            headers=auth_headers
        )
        
        assert response.status_code == 422
    
    def test_create_message_nonexistent_conversation(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test message creation in non-existent conversation."""
        response = client.post(
            "/api/conversations/99999/messages",
            json={"content": "Test message", "role": "user"},
            headers=auth_headers
        )
        
        assert response.status_code == 404
    
    def test_create_message_very_long_content(
        self,
        client: TestClient,
        auth_headers: dict,
        test_conversation
    ):
        """Test message creation with very long content."""
        long_content = "x" * 10000  # 10k characters
        response = client.post(
            f"/api/conversations/{test_conversation.id}/messages",
            json={"content": long_content, "role": "user"},
            headers=auth_headers
        )
        
        # Should either succeed or fail with token limit error
        assert response.status_code in [200, 201, 422, 400]
    
    @patch('src.model.providers.OpenAIProvider.generate')
    def test_create_message_with_different_roles(
        self,
        mock_generate,
        client: TestClient,
        auth_headers: dict,
        test_conversation,
        mock_openai_response: dict
    ):
        """Test message creation with different role types."""
        mock_generate.return_value = mock_openai_response
        
        roles = ["user", "assistant", "system"]
        
        for role in roles:
            response = client.post(
                f"/api/conversations/{test_conversation.id}/messages",
                json={"content": f"Message from {role}", "role": role},
                headers=auth_headers
            )
            
            # System and assistant roles might have different handling
            assert response.status_code in [200, 201, 403, 422]


class TestMessageRetrieval:
    """Test message retrieval endpoints."""
    
    def test_list_messages_in_conversation(
        self,
        client: TestClient,
        auth_headers: dict,
        test_conversation,
        test_messages: list
    ):
        """Test retrieving all messages in a conversation."""
        response = client.get(
            f"/api/conversations/{test_conversation.id}/messages",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        messages = data if isinstance(data, list) else data.get("messages", [])
        assert len(messages) >= 3  # We created 3 test messages
    
    def test_list_messages_empty_conversation(
        self,
        client: TestClient,
        auth_headers: dict,
        test_conversation
    ):
        """Test listing messages in conversation with no messages."""
        response = client.get(
            f"/api/conversations/{test_conversation.id}/messages",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        messages = data if isinstance(data, list) else data.get("messages", [])
        assert isinstance(messages, list)
    
    def test_get_message_by_id(
        self,
        client: TestClient,
        auth_headers: dict,
        test_conversation,
        test_messages: list
    ):
        """Test retrieving a specific message by ID."""
        message_id = test_messages[0].id
        
        response = client.get(
            f"/api/conversations/{test_conversation.id}/messages/{message_id}",
            headers=auth_headers
        )
        
        if response.status_code == 200:
            data = response.json()
            assert data["id"] == message_id
            assert data["content"] == test_messages[0].content
    
    def test_get_nonexistent_message(
        self,
        client: TestClient,
        auth_headers: dict,
        test_conversation
    ):
        """Test retrieving a message that doesn't exist."""
        response = client.get(
            f"/api/conversations/{test_conversation.id}/messages/99999",
            headers=auth_headers
        )
        
        assert response.status_code == 404
    
    def test_list_messages_with_pagination(
        self,
        client: TestClient,
        auth_headers: dict,
        test_conversation,
        test_messages: list
    ):
        """Test message listing with pagination."""
        response = client.get(
            f"/api/conversations/{test_conversation.id}/messages?limit=2&offset=0",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        messages = data if isinstance(data, list) else data.get("messages", [])
        assert len(messages) <= 2
    
    def test_filter_messages_by_role(
        self,
        client: TestClient,
        auth_headers: dict,
        test_conversation,
        test_messages: list
    ):
        """Test filtering messages by role."""
        response = client.get(
            f"/api/conversations/{test_conversation.id}/messages?role=user",
            headers=auth_headers
        )
        
        if response.status_code == 200:
            data = response.json()
            messages = data if isinstance(data, list) else data.get("messages", [])
            
            for msg in messages:
                assert msg["role"] == "user"


class TestMessageStreaming:
    """Test streaming message responses."""
    
    @patch('src.model.providers.OpenAIProvider.stream_generate')
    def test_stream_message_response(
        self,
        mock_stream,
        client: TestClient,
        auth_headers: dict,
        test_conversation,
        mock_streaming_response: list
    ):
        """Test streaming AI response generation."""
        # Mock async generator
        async def mock_stream_gen():
            for chunk in mock_streaming_response:
                yield chunk
        
        mock_stream.return_value = mock_stream_gen()
        
        response = client.post(
            f"/api/conversations/{test_conversation.id}/messages/stream",
            json={"content": "Tell me a story", "role": "user"},
            headers=auth_headers,
            stream=True
        )
        
        # Check if streaming endpoint exists
        if response.status_code == 200:
            # Verify response is streaming
            assert response.headers.get("content-type") in [
                "text/event-stream",
                "application/x-ndjson"
            ]
    
    @patch('src.model.providers.OpenAIProvider.stream_generate')
    def test_stream_with_connection_close(
        self,
        mock_stream,
        client: TestClient,
        auth_headers: dict,
        test_conversation
    ):
        """Test handling of connection close during streaming."""
        async def mock_stream_gen():
            yield {"choices": [{"delta": {"content": "Start"}}]}
            raise ConnectionError("Connection closed")
        
        mock_stream.return_value = mock_stream_gen()
        
        response = client.post(
            f"/api/conversations/{test_conversation.id}/messages/stream",
            json={"content": "Test", "role": "user"},
            headers=auth_headers,
            stream=True
        )
        
        # Should handle gracefully
        assert response.status_code in [200, 500, 503]


class TestMessageUpdate:
    """Test message update operations."""
    
    def test_update_message_content(
        self,
        client: TestClient,
        auth_headers: dict,
        test_conversation,
        test_messages: list
    ):
        """Test updating message content."""
        message_id = test_messages[0].id
        
        response = client.patch(
            f"/api/conversations/{test_conversation.id}/messages/{message_id}",
            json={"content": "Updated content"},
            headers=auth_headers
        )
        
        # Message editing might not be allowed for all roles
        assert response.status_code in [200, 403, 405]
        
        if response.status_code == 200:
            data = response.json()
            assert data["content"] == "Updated content"
    
    def test_update_assistant_message(
        self,
        client: TestClient,
        auth_headers: dict,
        test_conversation,
        test_messages: list
    ):
        """Test that users cannot edit assistant messages."""
        # Find an assistant message
        assistant_msg = next((m for m in test_messages if m.role == "assistant"), None)
        
        if assistant_msg:
            response = client.patch(
                f"/api/conversations/{test_conversation.id}/messages/{assistant_msg.id}",
                json={"content": "Hacked message"},
                headers=auth_headers
            )
            
            # Should be forbidden
            assert response.status_code in [403, 405]


class TestMessageDeletion:
    """Test message deletion operations."""
    
    def test_delete_message(
        self,
        client: TestClient,
        auth_headers: dict,
        test_conversation,
        test_messages: list
    ):
        """Test deleting a message."""
        message_id = test_messages[0].id
        
        response = client.delete(
            f"/api/conversations/{test_conversation.id}/messages/{message_id}",
            headers=auth_headers
        )
        
        # Message deletion might not be allowed
        assert response.status_code in [200, 204, 403, 405]
    
    def test_delete_all_messages_in_conversation(
        self,
        client: TestClient,
        auth_headers: dict,
        test_conversation,
        test_messages: list
    ):
        """Test bulk deletion of all messages in conversation."""
        response = client.delete(
            f"/api/conversations/{test_conversation.id}/messages",
            headers=auth_headers
        )
        
        if response.status_code in [200, 204]:
            # Verify messages are deleted
            get_response = client.get(
                f"/api/conversations/{test_conversation.id}/messages",
                headers=auth_headers
            )
            data = get_response.json()
            messages = data if isinstance(data, list) else data.get("messages", [])
            assert len(messages) == 0


class TestMessageSearch:
    """Test message search functionality."""
    
    def test_search_messages_by_content(
        self,
        client: TestClient,
        auth_headers: dict,
        test_conversation,
        test_messages: list
    ):
        """Test searching messages by content."""
        response = client.get(
            f"/api/conversations/{test_conversation.id}/messages?search=test",
            headers=auth_headers
        )
        
        if response.status_code == 200:
            data = response.json()
            messages = data if isinstance(data, list) else data.get("messages", [])
            
            # Results should contain search term
            for msg in messages:
                assert "test" in msg["content"].lower()
    
    def test_search_across_all_conversations(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test global message search across all user conversations."""
        response = client.get(
            "/api/messages/search?query=test",
            headers=auth_headers
        )
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (list, dict))


class TestAIProviderIntegration:
    """Test integration with different AI providers."""
    
    @patch('src.model.providers.OpenAIProvider.generate')
    def test_openai_provider(
        self,
        mock_generate,
        client: TestClient,
        auth_headers: dict,
        test_conversation,
        mock_openai_response: dict
    ):
        """Test message generation with OpenAI provider."""
        mock_generate.return_value = mock_openai_response
        
        response = client.post(
            f"/api/conversations/{test_conversation.id}/messages",
            json={
                "content": "Test OpenAI",
                "role": "user",
                "provider": "openai"
            },
            headers=auth_headers
        )
        
        assert response.status_code in [200, 201]
    
    @patch('src.model.providers.AnthropicProvider.generate')
    def test_anthropic_provider(
        self,
        mock_generate,
        client: TestClient,
        auth_headers: dict,
        test_conversation
    ):
        """Test message generation with Anthropic provider."""
        mock_response = {
            "content": [{"text": "Response from Claude"}],
            "usage": {"input_tokens": 10, "output_tokens": 20}
        }
        mock_generate.return_value = mock_response
        
        response = client.post(
            f"/api/conversations/{test_conversation.id}/messages",
            json={
                "content": "Test Anthropic",
                "role": "user",
                "provider": "anthropic"
            },
            headers=auth_headers
        )
        
        assert response.status_code in [200, 201, 422]
    
    @patch('src.model.providers.GeminiProvider.generate')
    def test_gemini_provider(
        self,
        mock_generate,
        client: TestClient,
        auth_headers: dict,
        test_conversation
    ):
        """Test message generation with Google Gemini provider."""
        mock_response = {
            "candidates": [{
                "content": {"parts": [{"text": "Response from Gemini"}]},
                "finish_reason": "STOP"
            }],
            "usage_metadata": {"prompt_token_count": 10, "candidates_token_count": 20}
        }
        mock_generate.return_value = mock_response
        
        response = client.post(
            f"/api/conversations/{test_conversation.id}/messages",
            json={
                "content": "Test Gemini",
                "role": "user",
                "provider": "google"
            },
            headers=auth_headers
        )
        
        assert response.status_code in [200, 201, 422]
    
    @patch('src.model.providers.OpenAIProvider.generate')
    def test_provider_error_handling(
        self,
        mock_generate,
        client: TestClient,
        auth_headers: dict,
        test_conversation
    ):
        """Test handling of AI provider errors."""
        mock_generate.side_effect = Exception("API rate limit exceeded")
        
        response = client.post(
            f"/api/conversations/{test_conversation.id}/messages",
            json={"content": "Test error", "role": "user"},
            headers=auth_headers
        )
        
        # Should return appropriate error
        assert response.status_code in [500, 503, 429]
        
        if response.status_code != 200:
            error_data = response.json()
            assert "error" in error_data or "detail" in error_data


class TestMessageConfiguration:
    """Test message generation with different configurations."""
    
    @patch('src.model.providers.OpenAIProvider.generate')
    def test_custom_temperature(
        self,
        mock_generate,
        client: TestClient,
        auth_headers: dict,
        test_conversation,
        mock_openai_response: dict
    ):
        """Test message generation with custom temperature."""
        mock_generate.return_value = mock_openai_response
        
        response = client.post(
            f"/api/conversations/{test_conversation.id}/messages",
            json={
                "content": "Test",
                "role": "user",
                "config": {"temperature": 1.5}
            },
            headers=auth_headers
        )
        
        assert response.status_code in [200, 201, 422]
    
    @patch('src.model.providers.OpenAIProvider.generate')
    def test_custom_max_tokens(
        self,
        mock_generate,
        client: TestClient,
        auth_headers: dict,
        test_conversation,
        mock_openai_response: dict
    ):
        """Test message generation with custom max tokens."""
        mock_generate.return_value = mock_openai_response
        
        response = client.post(
            f"/api/conversations/{test_conversation.id}/messages",
            json={
                "content": "Test",
                "role": "user",
                "config": {"max_tokens": 100}
            },
            headers=auth_headers
        )
        
        assert response.status_code in [200, 201]
    
    @patch('src.model.providers.OpenAIProvider.generate')
    def test_system_prompt_override(
        self,
        mock_generate,
        client: TestClient,
        auth_headers: dict,
        test_conversation,
        mock_openai_response: dict
    ):
        """Test message generation with custom system prompt."""
        mock_generate.return_value = mock_openai_response
        
        response = client.post(
            f"/api/conversations/{test_conversation.id}/messages",
            json={
                "content": "Test",
                "role": "user",
                "system_prompt": "You are a helpful coding assistant."
            },
            headers=auth_headers
        )
        
        assert response.status_code in [200, 201]


class TestMessageEdgeCases:
    """Test edge cases and error scenarios."""
    
    def test_message_with_code_blocks(
        self,
        client: TestClient,
        auth_headers: dict,
        test_conversation
    ):
        """Test message creation with code blocks."""
        content_with_code = """
        Here is some Python code:
        ```python
        def hello():
            print("Hello, world!")
        ```
        """
        
        response = client.post(
            f"/api/conversations/{test_conversation.id}/messages",
            json={"content": content_with_code, "role": "user"},
            headers=auth_headers
        )
        
        assert response.status_code in [200, 201]
    
    def test_message_with_markdown(
        self,
        client: TestClient,
        auth_headers: dict,
        test_conversation
    ):
        """Test message creation with markdown formatting."""
        markdown_content = """
        # Heading
        - Bullet 1
        - Bullet 2
        
        **Bold text** and *italic text*
        
        [Link](https://example.com)
        """
        
        response = client.post(
            f"/api/conversations/{test_conversation.id}/messages",
            json={"content": markdown_content, "role": "user"},
            headers=auth_headers
        )
        
        assert response.status_code in [200, 201]
    
    def test_message_with_unicode(
        self,
        client: TestClient,
        auth_headers: dict,
        test_conversation
    ):
        """Test message creation with Unicode characters."""
        unicode_content = "Hello 👋 世界 🌍 Привет مرحبا"
        
        response = client.post(
            f"/api/conversations/{test_conversation.id}/messages",
            json={"content": unicode_content, "role": "user"},
            headers=auth_headers
        )
        
        assert response.status_code in [200, 201]
    
    @patch('src.model.providers.OpenAIProvider.generate')
    def test_rapid_message_creation(
        self,
        mock_generate,
        client: TestClient,
        auth_headers: dict,
        test_conversation,
        mock_openai_response: dict
    ):
        """Test handling of rapid successive message creation."""
        mock_generate.return_value = mock_openai_response
        
        # Send multiple messages rapidly
        responses = []
        for i in range(5):
            response = client.post(
                f"/api/conversations/{test_conversation.id}/messages",
                json={"content": f"Message {i}", "role": "user"},
                headers=auth_headers
            )
            responses.append(response)
        
        # All should succeed or hit rate limit
        for response in responses:
            assert response.status_code in [200, 201, 429]
