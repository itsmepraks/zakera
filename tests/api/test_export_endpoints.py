"""Tests for conversation export endpoints."""
import pytest
import json
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.api.models import Conversation, Message
from src.api.schemas.export import ExportFormat


class TestExportEndpoints:
    """Test suite for export endpoints."""
    
    def test_export_conversation_json(self, client: TestClient, auth_headers: dict, test_conversation: Conversation, test_messages: list):
        """Test exporting conversation as JSON."""
        response = client.post(
            f"/api/v1/conversations/{test_conversation.id}/export",
            json={
                "format": "json",
                "include_metadata": True,
            },
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
    
    def test_export_conversation_markdown(self, client: TestClient, auth_headers: dict, test_conversation: Conversation, test_messages: list):
        """Test exporting conversation as Markdown."""
        response = client.post(
            f"/api/v1/conversations/{test_conversation.id}/export",
            json={
                "format": "markdown",
                "include_metadata": False,
            },
            headers=auth_headers,
        )
        
        assert response.status_code == 200
    
    def test_export_conversation_csv(self, client: TestClient, auth_headers: dict, test_conversation: Conversation, test_messages: list):
        """Test exporting conversation as CSV."""
        response = client.post(
            f"/api/v1/conversations/{test_conversation.id}/export",
            json={
                "format": "csv",
                "include_metadata": True,
            },
            headers=auth_headers,
        )
        
        assert response.status_code == 200
    
    def test_export_unauthorized(self, client: TestClient, test_conversation: Conversation):
        """Test export without authentication."""
        response = client.post(
            f"/api/v1/conversations/{test_conversation.id}/export",
            json={"format": "json"},
        )
        
        assert response.status_code == 401
    
    def test_export_nonexistent_conversation(self, client: TestClient, auth_headers: dict):
        """Test exporting non-existent conversation."""
        response = client.post(
            "/api/v1/conversations/99999/export",
            json={"format": "json"},
            headers=auth_headers,
        )
        
        assert response.status_code == 404
    
    def test_export_with_date_filter(self, client: TestClient, auth_headers: dict, test_conversation: Conversation, test_messages: list):
        """Test export with date filtering."""
        response = client.post(
            f"/api/v1/conversations/{test_conversation.id}/export",
            json={
                "format": "json",
                "date_from": "2024-01-01T00:00:00Z",
            },
            headers=auth_headers,
        )
        
        assert response.status_code == 200
    
    def test_get_export_history(self, client: TestClient, auth_headers: dict):
        """Test retrieving export history."""
        response = client.get(
            "/api/v1/conversations/exports/history",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "exports" in data
        assert "total" in data
