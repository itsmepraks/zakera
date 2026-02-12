import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from src.model.providers import OpenAIProvider, OpenAIError, Message, ModelResponse


class TestOpenAIProvider:
    """Comprehensive tests for OpenAI provider"""
    
    @pytest.fixture
    def provider(self):
        """Create OpenAI provider instance with test API key"""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            return OpenAIProvider(model_name="gpt-4")
    
    @pytest.fixture
    def sample_messages(self):
        """Sample messages for testing"""
        return [
            Message(role="system", content="You are a helpful assistant."),
            Message(role="user", content="Hello, how are you?")
        ]
    
    def test_initialization(self, provider):
        """Test provider initialization"""
        assert provider.api_key == "test-key"
        assert provider.model_name == "gpt-4"
        assert provider.base_url == "https://api.openai.com/v1"
        assert provider.max_retries == 3
    
    def test_initialization_without_api_key(self):
        """Test that initialization fails without API key"""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="OpenAI API key is required"):
                OpenAIProvider()
    
    def test_get_headers(self, provider):
        """Test header generation"""
        headers = provider._get_headers()
        assert headers["Authorization"] == "Bearer test-key"
        assert headers["Content-Type"] == "application/json"
    
    def test_get_headers_with_organization(self):
        """Test header generation with organization"""
        with patch.dict('os.environ', {
            'OPENAI_API_KEY': 'test-key',
            'OPENAI_ORGANIZATION': 'org-123'
        }):
            provider = OpenAIProvider()
            headers = provider._get_headers()
            assert headers["OpenAI-Organization"] == "org-123"
    
    def test_convert_messages(self, provider, sample_messages):
        """Test message format conversion"""
        converted = provider._convert_messages(sample_messages)
        
        assert len(converted) == 2
        assert converted[0]["role"] == "system"
        assert converted[0]["content"] == "You are a helpful assistant."
        assert converted[1]["role"] == "user"
        assert converted[1]["content"] == "Hello, how are you?"
    
    def test_convert_messages_with_name(self, provider):
        """Test message conversion with name field"""
        messages = [
            Message(role="user", content="Hello", name="Alice")
        ]
        converted = provider._convert_messages(messages)
        
        assert converted[0]["name"] == "Alice"
    
    @pytest.mark.asyncio
    async def test_generate_success(self, provider, sample_messages):
        """Test successful response generation"""
        mock_response = {
            "id": "chatcmpl-123",
            "object": "chat.completion",
            "created": 1677652288,
            "model": "gpt-4",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "I'm doing great, thank you for asking!"
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 20,
                "completion_tokens": 10,
                "total_tokens": 30
            }
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            mock_http_response = AsyncMock()
            mock_http_response.json.return_value = mock_response
            mock_http_response.raise_for_status = Mock()
            
            mock_instance.post.return_value = mock_http_response
            
            response = await provider.generate(sample_messages)
            
            assert isinstance(response, ModelResponse)
            assert response.content == "I'm doing great, thank you for asking!"
            assert response.model == "gpt-4"
            assert response.usage["prompt_tokens"] == 20
            assert response.usage["completion_tokens"] == 10
            assert response.usage["total_tokens"] == 30
            assert response.finish_reason == "stop"
    
    @pytest.mark.asyncio
    async def test_generate_with_parameters(self, provider, sample_messages):
        """Test generation with optional parameters"""
        mock_response = {
            "choices": [{
                "message": {"role": "assistant", "content": "Response"},
                "finish_reason": "stop"
            }],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            "model": "gpt-4"
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            mock_http_response = AsyncMock()
            mock_http_response.json.return_value = mock_response
            mock_http_response.raise_for_status = Mock()
            
            mock_instance.post.return_value = mock_http_response
            
            await provider.generate(
                sample_messages,
                temperature=0.8,
                max_tokens=100,
                top_p=0.9,
                presence_penalty=0.5
            )
            
            # Verify the request was made with correct parameters
            call_kwargs = mock_instance.post.call_args[1]
            payload = call_kwargs["json"]
            
            assert payload["temperature"] == 0.8
            assert payload["max_tokens"] == 100
            assert payload["top_p"] == 0.9
            assert payload["presence_penalty"] == 0.5
    
    @pytest.mark.asyncio
    async def test_generate_with_function_calling(self, provider, sample_messages):
        """Test generation with function calling"""
        mock_response = {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "function_call": {
                        "name": "get_weather",
                        "arguments": '{"location": "Boston"}'
                    }
                },
                "finish_reason": "function_call"
            }],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            "model": "gpt-4"
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            mock_http_response = AsyncMock()
            mock_http_response.json.return_value = mock_response
            mock_http_response.raise_for_status = Mock()
            
            mock_instance.post.return_value = mock_http_response
            
            response = await provider.generate(sample_messages)
            
            # Function call should be serialized as JSON in content
            assert "get_weather" in response.content
            assert response.finish_reason == "function_call"
    
    @pytest.mark.asyncio
    async def test_generate_error_handling(self, provider, sample_messages):
        """Test error handling in generate"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            # Simulate HTTP error
            mock_http_response = AsyncMock()
            mock_http_response.status_code = 401
            mock_http_response.text = "Invalid API key"
            mock_http_response.raise_for_status.side_effect = Exception("HTTP Error")
            
            mock_instance.post.return_value = mock_http_response
            
            with pytest.raises(OpenAIError):
                await provider.generate(sample_messages)
    
    @pytest.mark.asyncio
    async def test_generate_retry_logic(self, provider, sample_messages):
        """Test retry logic with exponential backoff"""
        provider.max_retries = 2
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            # First call fails with 500, second succeeds
            mock_http_response_fail = AsyncMock()
            mock_http_response_fail.status_code = 500
            mock_http_response_fail.text = "Server error"
            
            from httpx import HTTPStatusError, Response, Request
            error = HTTPStatusError(
                "Server error",
                request=Mock(spec=Request),
                response=mock_http_response_fail
            )
            
            mock_http_response_success = AsyncMock()
            mock_http_response_success.json.return_value = {
                "choices": [{"message": {"content": "Success"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 5, "completion_tokens": 5, "total_tokens": 10},
                "model": "gpt-4"
            }
            mock_http_response_success.raise_for_status = Mock()
            
            mock_instance.post.side_effect = [error, mock_http_response_success]
            
            with patch('asyncio.sleep') as mock_sleep:
                response = await provider.generate(sample_messages)
                
                assert response.content == "Success"
                # Verify sleep was called for backoff
                mock_sleep.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_stream_generate(self, provider, sample_messages):
        """Test streaming generation"""
        # Mock SSE stream data
        stream_data = [
            'data: {"choices": [{"delta": {"content": "Hello"}}]}\n',
            'data: {"choices": [{"delta": {"content": " world"}}]}\n',
            'data: {"choices": [{"delta": {"content": "!"}}]}\n',
            'data: [DONE]\n'
        ]
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            # Create async iterator for stream
            async def mock_aiter_lines():
                for line in stream_data:
                    yield line.strip()
            
            mock_stream_response = AsyncMock()
            mock_stream_response.aiter_lines.return_value = mock_aiter_lines()
            mock_stream_response.raise_for_status = Mock()
            mock_stream_response.__aenter__.return_value = mock_stream_response
            mock_stream_response.__aexit__.return_value = None
            
            mock_instance.stream.return_value = mock_stream_response
            
            chunks = []
            async for chunk in provider.stream_generate(sample_messages):
                chunks.append(chunk)
            
            assert chunks == ["Hello", " world", "!"]
    
    @pytest.mark.asyncio
    async def test_stream_generate_with_function_call(self, provider, sample_messages):
        """Test streaming with function calls"""
        stream_data = [
            'data: {"choices": [{"delta": {"function_call": {"arguments": "{\\"location\\""}}}]}\n',
            'data: {"choices": [{"delta": {"function_call": {"arguments": ": \\"Boston\\"}"}}}]}\n',
            'data: [DONE]\n'
        ]
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            async def mock_aiter_lines():
                for line in stream_data:
                    yield line.strip()
            
            mock_stream_response = AsyncMock()
            mock_stream_response.aiter_lines.return_value = mock_aiter_lines()
            mock_stream_response.raise_for_status = Mock()
            mock_stream_response.__aenter__.return_value = mock_stream_response
            mock_stream_response.__aexit__.return_value = None
            
            mock_instance.stream.return_value = mock_stream_response
            
            chunks = []
            async for chunk in provider.stream_generate(sample_messages):
                chunks.append(chunk)
            
            # Function call arguments should be streamed
            assert len(chunks) > 0
    
    @pytest.mark.asyncio
    async def test_stream_generate_error(self, provider, sample_messages):
        """Test error handling in streaming"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            mock_stream_response = AsyncMock()
            mock_stream_response.raise_for_status.side_effect = Exception("Stream error")
            mock_stream_response.__aenter__.return_value = mock_stream_response
            mock_stream_response.__aexit__.return_value = None
            
            mock_instance.stream.return_value = mock_stream_response
            
            with pytest.raises(OpenAIError):
                async for _ in provider.stream_generate(sample_messages):
                    pass


class TestOpenAIError:
    """Test OpenAI custom error class"""
    
    def test_error_with_status_code(self):
        """Test error with status code"""
        error = OpenAIError("Test error", 401)
        assert error.message == "Test error"
        assert error.status_code == 401
        assert str(error) == "Test error"
    
    def test_error_without_status_code(self):
        """Test error without status code"""
        error = OpenAIError("Test error")
        assert error.message == "Test error"
        assert error.status_code is None
