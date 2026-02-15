"""Tests for analytics service."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock

from src.api.analytics import ConversationAnalytics


@pytest.fixture
def analytics():
    return ConversationAnalytics(cache_ttl=0)


@pytest.fixture
def mock_db():
    return AsyncMock()


class TestAnalytics:
    @pytest.mark.asyncio
    async def test_overview_metrics(self, analytics, mock_db):
        mock_db.scalar = AsyncMock(side_effect=[100, 500, 25, 80])
        mock_db.execute = AsyncMock(return_value=Mock(mappings=Mock(return_value=[])))
        
        result = await analytics.get_overview_metrics(mock_db)
        
        assert result['total_conversations'] == 100
        assert result['total_messages'] == 500
