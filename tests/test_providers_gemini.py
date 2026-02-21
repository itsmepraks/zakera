"""Tests for Gemini model provider."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import sys

# Mock google.generativeai before importing provider
sys.modules['google'] = Mock()
sys.modules['google.generativeai'] = Mock()
sys.modules['google.generativeai.types'] = Mock()

from src.model.providers_gemini import GeminiProvider


class TestGeminiProvider:
    """Test suite for Gemini provider."""

    @pytest.fixture
    def mock_genai(self):
        """Mock the google.generativeai module."""
        with patch('src.model.providers_gemini.genai') as mock:
            # Mock model response
            mock_response = Mock()
            mock_response.text = "This is a test response"
            mock_response.usage_metadata = Mock(
                prompt_token_count=10,
                candidates_token_count=20
            )
            mock_response.candidates = [Mock(
                safety_ratings=[]
            )]
            
            mock_model = Mock()
            mock_model.generate_content.return_value = mock_response
            mock_model.count_tokens.return_value = Mock(total_tokens=10)
            
            mock_chat = Mock()
            mock_chat.send_message.return_value = mock_response
            mock_model.start_chat.return_value = mock_chat
            
            mock.GenerativeModel.return_value = mock_model
            
            yield mock

    @pytest.fixture
    def provider(self, mock_genai):
        """Create a Gemini provider instance."""
        with patch('src.model.providers_gemini.GEMINI_AVAILABLE', True):
            return GeminiProvider(api_key="test-key", model="gemini-1.5-pro")

    def test_initialization(self, provider):
        """Test provider initialization."""
        assert provider.model == "gemini-1.5-pro"
        assert provider.temperature == 0.7
        assert provider.api_key == "test-key"

    @pytest.mark.asyncio
    async def test_generate(self, provider, mock_genai):
        """Test basic text generation."""
        response = await provider.generate("Hello, world!")
        
        assert response.content == "This is a test response"
        assert response.provider == "gemini"
        assert response.model == "gemini-1.5-pro"
        assert response.prompt_tokens == 10
        assert response.completion_tokens == 20
        assert response.cost > 0

    @pytest.mark.asyncio
    async def test_generate_with_system_prompt(self, provider, mock_genai):
        """Test generation with system prompt."""
        response = await provider.generate(
            prompt="What is 2+2?",
            system_prompt="You are a helpful math tutor."
        )
        
        assert response.content is not None
        assert response.provider == "gemini"

    @pytest.mark.asyncio
    async def test_generate_with_conversation_history(self, provider, mock_genai):
        """Test generation with conversation context."""
        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        
        response = await provider.generate(
            prompt="How are you?",
            conversation_history=history
        )
        
        assert response.content is not None

    @pytest.mark.asyncio
    async def test_generate_stream(self, provider, mock_genai):
        """Test streaming response generation."""
        chunks = []
        async for chunk in provider.generate_stream("Tell me a story"):
            chunks.append(chunk)
        
        assert len(chunks) > 0
        assert all(c.provider == "gemini" for c in chunks)

    def test_calculate_cost(self, provider):
        """Test cost calculation."""
        cost = provider._calculate_cost(1000, 2000)
        
        # gemini-1.5-pro: $0.00125/1K input + $0.005/1K output
        expected = (1000/1000 * 0.00125) + (2000/1000 * 0.005)
        assert abs(cost - expected) < 0.0001

    @pytest.mark.asyncio
    async def test_count_tokens(self, provider, mock_genai):
        """Test token counting."""
        count = await provider.count_tokens("Hello, world!")
        assert count > 0

    @pytest.mark.asyncio
    async def test_validate_model(self, provider, mock_genai):
        """Test model validation."""
        is_valid = await provider.validate_model()
        assert is_valid is True

    def test_get_available_models(self):
        """Test getting list of available models."""
        models = GeminiProvider.get_available_models()
        
        assert "gemini-1.5-pro" in models
        assert "gemini-1.5-flash" in models
        assert "gemini-1.0-pro" in models

    def test_get_context_window(self, provider):
        """Test getting context window size."""
        context_size = provider.get_context_window()
        assert context_size == 2_000_000  # Gemini 1.5 Pro

    @pytest.mark.asyncio
    async def test_error_handling(self, provider, mock_genai):
        """Test error handling during generation."""
        # Mock an error
        mock_genai.GenerativeModel.return_value.start_chat.side_effect = Exception("API Error")
        
        with pytest.raises(Exception):
            await provider.generate("This should fail")

    def test_pricing_data(self, provider):
        """Test that pricing data is complete."""
        for model in GeminiProvider.SUPPORTED_MODELS:
            assert model in GeminiProvider.PRICING
            assert "input" in GeminiProvider.PRICING[model]
            assert "output" in GeminiProvider.PRICING[model]
