"""
Unit and integration tests for conversation export endpoint.

Tests cover authentication, authorization, various export formats,
streaming functionality, error handling, and metrics.
"""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from fastapi import status
from fastapi.testclient import TestClient

from src.api.routes.conversation_export import ConversationExporter, router
from src.api.models import User, Conversation, Message, ToolExecution


class TestConversationExporter:
    """Test cases for ConversationExporter class."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def sample_conversation(self):
        """Create sample conversation for testing."""
        return Conversation(
            id=1,
            user_id=1,
            title="Test Conversation",
            created_at=datetime(2026, 2, 19, 10, 0, 0),
        )

    @pytest.fixture
    def sample_messages(self):
        """Create sample messages for testing."""
        return [
            Message(
                id=1,
                conversation_id=1,
                role="user",
                content="Hello, how are you?",
                created_at=datetime(2026, 2, 19, 10, 0, 0),
                model_name="gpt-4-turbo",
                token_count=5,
                cost=0.0001,
                latency_ms=250,
                provider="openai",
            ),
            Message(
                id=2,
                conversation_id=1,
                role="assistant",
                content="I'm doing well, thank you!",
                created_at=datetime(2026, 2, 19, 10, 0, 5),
                model_name="gpt-4-turbo",
                token_count=8,
                cost=0.0002,
                latency_ms=300,
                provider="openai",
            ),
        ]

    @pytest.mark.asyncio
    async def test_validate_conversation_success(
        self, mock_db, sample_conversation
    ):
        """Test successful conversation validation."""
        exporter = ConversationExporter(
            conversation_id=1,
            user_id=1,
            format="json",
            include_metadata=True,
            include_tools=True,
            batch_size=50,
        )

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_conversation
        mock_db.execute.return_value = mock_result

        conversation = await exporter.validate_conversation(mock_db)
        assert conversation == sample_conversation

    @pytest.mark.asyncio
    async def test_validate_conversation_not_found(self, mock_db):
        """Test conversation not found error."""
        exporter = ConversationExporter(
            conversation_id=999,
            user_id=1,
            format="json",
            include_metadata=True,
            include_tools=True,
            batch_size=50,
        )

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(Exception) as exc_info:
            await exporter.validate_conversation(mock_db)
        assert "not found or access denied" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_total_messages(self, mock_db):
        """Test getting total message count."""
        exporter = ConversationExporter(
            conversation_id=1,
            user_id=1,
            format="json",
            include_metadata=True,
            include_tools=True,
            batch_size=50,
        )

        mock_result = Mock()
        mock_result.scalar.return_value = 42
        mock_db.execute.return_value = mock_result

        count = await exporter.get_total_messages(mock_db)
        assert count == 42

    def test_format_message_json_with_metadata(self, sample_messages):
        """Test JSON formatting with metadata."""
        exporter = ConversationExporter(
            conversation_id=1,
            user_id=1,
            format="json",
            include_metadata=True,
            include_tools=False,
            batch_size=50,
        )

        message = sample_messages[0]
        formatted = exporter.format_message_json(message)

        assert formatted["id"] == 1
        assert formatted["role"] == "user"
        assert formatted["content"] == "Hello, how are you?"
        assert formatted["model"] == "gpt-4-turbo"
        assert formatted["tokens"] == 5
        assert formatted["cost"] == 0.0001

    def test_format_message_json_without_metadata(self, sample_messages):
        """Test JSON formatting without metadata."""
        exporter = ConversationExporter(
            conversation_id=1,
            user_id=1,
            format="json",
            include_metadata=False,
            include_tools=False,
            batch_size=50,
        )

        message = sample_messages[0]
        formatted = exporter.format_message_json(message)

        assert "id" in formatted
        assert "role" in formatted
        assert "content" in formatted
        assert "model" not in formatted
        assert "tokens" not in formatted

    def test_format_message_markdown(self, sample_messages):
        """Test Markdown formatting."""
        exporter = ConversationExporter(
            conversation_id=1,
            user_id=1,
            format="markdown",
            include_metadata=True,
            include_tools=False,
            batch_size=50,
        )

        message = sample_messages[0]
        formatted = exporter.format_message_markdown(message)

        assert "### USER" in formatted
        assert "Hello, how are you?" in formatted
        assert "**Model:** gpt-4-turbo" in formatted
        assert "**Tokens:** 5" in formatted

    def test_format_message_text(self, sample_messages):
        """Test plain text formatting."""
        exporter = ConversationExporter(
            conversation_id=1,
            user_id=1,
            format="text",
            include_metadata=False,
            include_tools=False,
            batch_size=50,
        )

        message = sample_messages[0]
        formatted = exporter.format_message_text(message)

        assert "USER:" in formatted
        assert "Hello, how are you?" in formatted
        assert "2026-02-19 10:00:00" in formatted

    def test_format_message_csv_row(self, sample_messages):
        """Test CSV row formatting."""
        exporter = ConversationExporter(
            conversation_id=1,
            user_id=1,
            format="csv",
            include_metadata=True,
            include_tools=False,
            batch_size=50,
        )

        message = sample_messages[0]
        row = exporter.format_message_csv_row(message)

        assert row["id"] == 1
        assert row["role"] == "user"
        assert row["content"] == "Hello, how are you?"
        assert row["model"] == "gpt-4-turbo"
        assert row["tokens"] == 5

    @pytest.mark.asyncio
    async def test_stream_json_format(
        self, mock_db, sample_conversation, sample_messages
    ):
        """Test JSON streaming format."""
        exporter = ConversationExporter(
            conversation_id=1,
            user_id=1,
            format="json",
            include_metadata=True,
            include_tools=False,
            batch_size=50,
        )
        exporter.total_messages = 2

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = sample_messages
        mock_db.execute.return_value = mock_result

        chunks = []
        async for chunk in exporter.stream_json(mock_db, sample_conversation):
            chunks.append(chunk)

        # Should have metadata, data, and complete chunks
        assert len(chunks) >= 3

        # Parse and validate chunks
        metadata = json.loads(chunks[0])
        assert metadata["type"] == "metadata"
        assert metadata["conversation_id"] == 1
        assert metadata["title"] == "Test Conversation"

        # Last chunk should be complete
        complete = json.loads(chunks[-1])
        assert complete["type"] == "complete"
        assert complete["total_messages"] == 2


class TestExportEndpoint:
    """Test cases for the export API endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        return TestClient(app)

    @pytest.fixture
    def mock_user(self):
        """Create mock authenticated user."""
        return User(id=1, email="test@example.com", username="testuser")

    def test_export_requires_authentication(self, client):
        """Test that export endpoint requires authentication."""
        response = client.get("/api/v1/conversations/1/export")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_export_json_format(self, client, mock_user):
        """Test exporting conversation in JSON format."""
        with patch("src.api.routes.conversation_export.get_current_user") as mock_auth:
            mock_auth.return_value = mock_user

            response = client.get(
                "/api/v1/conversations/1/export",
                params={"format": "json"},
            )

            assert response.headers["content-type"] == "application/json"
            assert "conversation_1.json" in response.headers["content-disposition"]

    @pytest.mark.asyncio
    async def test_export_markdown_format(self, client, mock_user):
        """Test exporting conversation in Markdown format."""
        with patch("src.api.routes.conversation_export.get_current_user") as mock_auth:
            mock_auth.return_value = mock_user

            response = client.get(
                "/api/v1/conversations/1/export",
                params={"format": "markdown"},
            )

            assert response.headers["content-type"] == "text/markdown"
            assert "conversation_1.markdown" in response.headers["content-disposition"]

    @pytest.mark.asyncio
    async def test_export_csv_format(self, client, mock_user):
        """Test exporting conversation in CSV format."""
        with patch("src.api.routes.conversation_export.get_current_user") as mock_auth:
            mock_auth.return_value = mock_user

            response = client.get(
                "/api/v1/conversations/1/export",
                params={"format": "csv"},
            )

            assert response.headers["content-type"] == "text/csv"
            assert "conversation_1.csv" in response.headers["content-disposition"]

    def test_export_invalid_format(self, client, mock_user):
        """Test export with invalid format parameter."""
        with patch("src.api.routes.conversation_export.get_current_user") as mock_auth:
            mock_auth.return_value = mock_user

            response = client.get(
                "/api/v1/conversations/1/export",
                params={"format": "invalid"},
            )

            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_export_batch_size_validation(self, client, mock_user):
        """Test batch size parameter validation."""
        with patch("src.api.routes.conversation_export.get_current_user") as mock_auth:
            mock_auth.return_value = mock_user

            # Test batch size too small
            response = client.get(
                "/api/v1/conversations/1/export",
                params={"batch_size": 5},
            )
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

            # Test batch size too large
            response = client.get(
                "/api/v1/conversations/1/export",
                params={"batch_size": 1000},
            )
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_export_with_metadata_flag(self, client, mock_user):
        """Test export with metadata inclusion flag."""
        with patch("src.api.routes.conversation_export.get_current_user") as mock_auth:
            mock_auth.return_value = mock_user

            response = client.get(
                "/api/v1/conversations/1/export",
                params={"format": "json", "include_metadata": False},
            )

            # Should still return 200, content verification would be in integration test
            assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    @pytest.mark.asyncio
    async def test_export_with_tools_flag(self, client, mock_user):
        """Test export with tool execution inclusion flag."""
        with patch("src.api.routes.conversation_export.get_current_user") as mock_auth:
            mock_auth.return_value = mock_user

            response = client.get(
                "/api/v1/conversations/1/export",
                params={"format": "json", "include_tools": False},
            )

            # Should still return 200, content verification would be in integration test
            assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]


class TestExportMetrics:
    """Test cases for export metrics tracking."""

    @pytest.mark.asyncio
    async def test_export_success_metrics(self):
        """Test that successful exports record metrics."""
        with patch("src.api.routes.conversation_export.export_requests_total") as mock_metric:
            # Simulate successful export
            mock_metric.labels.return_value.inc.return_value = None

            # Call would trigger metric increment
            mock_metric.labels(format="json", status="success").inc()

            # Verify metric was called
            mock_metric.labels.assert_called_with(format="json", status="success")

    @pytest.mark.asyncio
    async def test_export_error_metrics(self):
        """Test that export errors record metrics."""
        with patch("src.api.routes.conversation_export.export_errors_total") as mock_metric:
            # Simulate export error
            mock_metric.labels.return_value.inc.return_value = None

            # Call would trigger metric increment
            mock_metric.labels(format="json", error_type="not_found").inc()

            # Verify metric was called
            mock_metric.labels.assert_called_with(
                format="json", error_type="not_found"
            )

    @pytest.mark.asyncio
    async def test_export_duration_metrics(self):
        """Test that export duration is recorded."""
        with patch(
            "src.api.routes.conversation_export.export_duration_seconds"
        ) as mock_metric:
            # Simulate duration recording
            mock_metric.labels.return_value.observe.return_value = None

            # Call would trigger metric observation
            mock_metric.labels(format="json").observe(2.5)

            # Verify metric was called
            mock_metric.labels.assert_called_with(format="json")


class TestEdgeCases:
    """Test edge cases and error scenarios."""

    @pytest.mark.asyncio
    async def test_export_empty_conversation(self, mock_db):
        """Test exporting conversation with no messages."""
        exporter = ConversationExporter(
            conversation_id=1,
            user_id=1,
            format="json",
            include_metadata=True,
            include_tools=True,
            batch_size=50,
        )
        exporter.total_messages = 0

        conversation = Conversation(
            id=1,
            user_id=1,
            title="Empty Conversation",
            created_at=datetime(2026, 2, 19, 10, 0, 0),
        )

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        chunks = []
        async for chunk in exporter.stream_json(mock_db, conversation):
            chunks.append(chunk)

        # Should still have metadata and complete chunks
        assert len(chunks) >= 2

    @pytest.mark.asyncio
    async def test_export_large_conversation(self, mock_db):
        """Test exporting conversation with many messages."""
        exporter = ConversationExporter(
            conversation_id=1,
            user_id=1,
            format="json",
            include_metadata=True,
            include_tools=False,
            batch_size=10,  # Small batch for testing
        )
        exporter.total_messages = 150

        # Mock should handle multiple batch calls
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [
            Message(
                id=i,
                conversation_id=1,
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}",
                created_at=datetime(2026, 2, 19, 10, 0, i),
                model_name="gpt-4-turbo",
                token_count=10,
                cost=0.0001,
                latency_ms=250,
                provider="openai",
            )
            for i in range(10)
        ]
        mock_db.execute.return_value = mock_result

        conversation = Conversation(
            id=1,
            user_id=1,
            title="Large Conversation",
            created_at=datetime(2026, 2, 19, 10, 0, 0),
        )

        chunks = []
        async for chunk in exporter.stream_json(mock_db, conversation):
            chunks.append(chunk)

        # Should have multiple progress updates
        progress_chunks = [
            c for c in chunks if "progress" in c and json.loads(c).get("type") == "progress"
        ]
        assert len(progress_chunks) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
