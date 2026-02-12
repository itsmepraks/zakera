import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from src.model.providers import GeminiProvider, Message, ModelResponse


class TestGeminiProvider:
    """Test suite for Google Gemini provider implementation"""
    
    @pytest.fixture
    def provider(self):
        """Create a GeminiProvider instance for testing"""
        return GeminiProvider(api_key="test_key", model_name="gemini-pro")
    
    def test_initialization(self, provider):
        """Test that the provider initializes correctly"""
        assert provider.api_key == "test_key"
        assert provider.model_name == "gemini-pro"
        assert provider.base_url == "https://generativelanguage.googleapis.com/v1beta"
    
    def test_invalid_model_name(self):
        """Test that invalid model names raise an error"""
        with pytest.raises(ValueError, match="Invalid model name"):
            GeminiProvider(api_key="test_key", model_name="invalid-model")
    
    def test_valid_model_names(self):
        """Test that all valid model names are accepted"""
        valid_models = ["gemini-pro", "gemini-pro-vision", "gemini-1.5-pro", "gemini-1.5-flash"]
        for model in valid_models:
            provider = GeminiProvider(api_key="test_key", model_name=model)
            assert provider.model_name == model
    
    def test_message_conversion(self, provider):
        """Test message format conversion to Gemini format"""
        messages = [
            Message(role="user", content="Hello"),
            Message(role="assistant", content="Hi there!"),
            Message(role="user", content="How are you?")
        ]
        
        gemini_messages = provider._convert_messages_to_gemini_format(messages)
        
        assert len(gemini_messages) == 3
        assert gemini_messages[0]["role"] == "user"
        assert gemini_messages[0]["parts"][0]["text"] == "Hello"
        assert gemini_messages[1]["role"] == "model"  # assistant -> model
        assert gemini_messages[1]["parts"][0]["text"] == "Hi there!"
        assert gemini_messages[2]["role"] == "user"
    
    @pytest.mark.asyncio
    async def test_generate_success(self, provider):
        """Test successful response generation"""
        messages = [Message(role="user", content="What is AI?")]
        
        mock_response = {
            "candidates": [{
                "content": {
                    "parts": [{"text": "AI stands for Artificial Intelligence."}]
                },
                "finishReason": "STOP"
            }],
            "usageMetadata": {
                "promptTokenCount": 10,
                "candidatesTokenCount": 8,
                "totalTokenCount": 18
            }
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response_obj = Mock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status = Mock()
            
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response_obj
            )
            
            result = await provider.generate(messages, temperature=0.8, max_tokens=1024)
            
            assert isinstance(result, ModelResponse)
            assert result.content == "AI stands for Artificial Intelligence."
            assert result.model == "gemini-pro"
            assert result.usage["prompt_tokens"] == 10
            assert result.usage["completion_tokens"] == 8
            assert result.usage["total_tokens"] == 18
            assert result.finish_reason == "stop"
    
    @pytest.mark.asyncio
    async def test_generate_no_api_key(self):
        """Test that generation fails without API key"""
        provider = GeminiProvider(api_key=None, model_name="gemini-pro")
        messages = [Message(role="user", content="Hello")]
        
        with pytest.raises(ValueError, match="Google API key is required"):
            await provider.generate(messages)
    
    @pytest.mark.asyncio
    async def test_generate_empty_candidates(self, provider):
        """Test handling of empty candidates in response"""
        messages = [Message(role="user", content="Test")]
        
        mock_response = {"candidates": []}
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response_obj = Mock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status = Mock()
            
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response_obj
            )
            
            with pytest.raises(ValueError, match="No response candidates returned"):
                await provider.generate(messages)
    
    @pytest.mark.asyncio
    async def test_stream_generate_success(self, provider):
        """Test successful streaming response generation"""
        messages = [Message(role="user", content="Count to 3")]
        
        # Simulate SSE stream data
        stream_lines = [
            "data: {\"candidates\":[{\"content\":{\"parts\":[{\"text\":\"One\"}]}}]}",
            "data: {\"candidates\":[{\"content\":{\"parts\":[{\"text\":\" two\"}]}}]}",
            "data: {\"candidates\":[{\"content\":{\"parts\":[{\"text\":\" three\"}]}}]}",
        ]
        
        async def mock_aiter_lines():
            for line in stream_lines:
                yield line
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.raise_for_status = Mock()
            mock_response.aiter_lines = mock_aiter_lines
            
            mock_stream_context = AsyncMock()
            mock_stream_context.__aenter__.return_value = mock_response
            
            mock_client.return_value.__aenter__.return_value.stream = Mock(
                return_value=mock_stream_context
            )
            
            chunks = []
            async for chunk in provider.stream_generate(messages):
                chunks.append(chunk)
            
            assert len(chunks) == 3
            assert chunks[0] == "One"
            assert chunks[1] == " two"
            assert chunks[2] == " three"
    
    @pytest.mark.asyncio
    async def test_stream_generate_no_api_key(self):
        """Test that streaming fails without API key"""
        provider = GeminiProvider(api_key=None, model_name="gemini-pro")
        messages = [Message(role="user", content="Hello")]
        
        with pytest.raises(ValueError, match="Google API key is required"):
            async for _ in provider.stream_generate(messages):
                pass
    
    @pytest.mark.asyncio
    async def test_generate_with_custom_parameters(self, provider):
        """Test generation with custom temperature and other parameters"""
        messages = [Message(role="user", content="Be creative")]
        
        mock_response = {
            "candidates": [{
                "content": {"parts": [{"text": "Creative response"}]},
                "finishReason": "STOP"
            }],
            "usageMetadata": {"totalTokenCount": 10}
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_post = AsyncMock()
            mock_response_obj = Mock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status = Mock()
            mock_post.return_value = mock_response_obj
            
            mock_client.return_value.__aenter__.return_value.post = mock_post
            
            await provider.generate(
                messages,
                temperature=0.9,
                top_p=0.98,
                top_k=50,
                max_tokens=4096
            )
            
            # Verify the API was called with correct parameters
            call_args = mock_post.call_args
            payload = call_args[1]['json']
            
            assert payload['generationConfig']['temperature'] == 0.9
            assert payload['generationConfig']['topP'] == 0.98
            assert payload['generationConfig']['topK'] == 50
            assert payload['generationConfig']['maxOutputTokens'] == 4096
    
    def test_provider_from_environment(self):
        """Test provider initialization from environment variables"""
        with patch.dict('os.environ', {'GOOGLE_API_KEY': 'env_key'}):
            provider = GeminiProvider(model_name="gemini-pro")
            assert provider.api_key == 'env_key'
