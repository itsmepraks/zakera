"""
Tests for src/model/providers_ollama_local.py

All HTTP calls are mocked via unittest.mock so no running Ollama instance
is needed.  Uses pytest-asyncio for async test execution.
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.model.providers_ollama_local import (
    ChatResponse,
    HealthStatus,
    ModelPullError,
    OllamaConnectionError,
    OllamaLocalProvider,
    OllamaModelInfo,
    StructuredOutputError,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_response(status: int = 200, json_body: dict | None = None, text: str = ""):
    """Return a mock httpx.Response."""
    resp = MagicMock()
    resp.status_code = status
    resp.text = text or json.dumps(json_body or {})
    resp.json = MagicMock(return_value=json_body or {})
    return resp


def _chat_json(content="Hello!", model="llama3", prompt_tokens=10, eval_count=20):
    return {
        "model": model,
        "message": {"role": "assistant", "content": content},
        "prompt_eval_count": prompt_tokens,
        "eval_count": eval_count,
        "done": True,
        "done_reason": "stop",
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def provider():
    return OllamaLocalProvider(model="llama3", base_url="http://localhost:11434")


# ---------------------------------------------------------------------------
# generate() tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_returns_content_on_200(provider):
    mock_resp = _make_response(200, _chat_json(content="Hi there!"))
    with patch.object(provider, "_with_retry", new=AsyncMock(return_value=mock_resp)):
        result = await provider.generate([{"role": "user", "content": "Hello"}])
    assert isinstance(result, ChatResponse)
    assert result.content == "Hi there!"
    assert result.model == "llama3"


@pytest.mark.asyncio
async def test_generate_maps_system_message_correctly(provider):
    """system role message must be forwarded verbatim in the messages list."""
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hi"},
    ]
    mock_resp = _make_response(200, _chat_json())
    captured = {}

    async def fake_retry(factory):
        # Inspect what payload the factory would send
        client_mock = MagicMock()
        client_mock.post = AsyncMock(return_value=mock_resp)
        return mock_resp

    with patch.object(provider, "_with_retry", new=AsyncMock(return_value=mock_resp)):
        payload = provider._build_payload(messages, stream=False)
        captured["messages"] = payload["messages"]
        result = await provider.generate(messages)
    assert captured["messages"][0]["role"] == "system"
    assert result.content == "Hello!"


@pytest.mark.asyncio
async def test_generate_passes_temperature_to_options(provider):
    payload = provider._build_payload(
        [{"role": "user", "content": "hi"}],
        stream=False,
        extra_options={"temperature": 0.7, "top_p": 0.9},
    )
    assert payload["options"]["temperature"] == 0.7
    assert payload["options"]["top_p"] == 0.9


@pytest.mark.asyncio
async def test_generate_raises_on_connection_error(provider):
    import httpx

    with patch.object(
        provider,
        "_with_retry",
        new=AsyncMock(side_effect=OllamaConnectionError("down")),
    ):
        with pytest.raises(OllamaConnectionError):
            await provider.generate([{"role": "user", "content": "hello"}])


@pytest.mark.asyncio
async def test_generate_raises_on_non_200_response(provider):
    mock_resp = _make_response(500, text="Internal Server Error")
    with patch.object(provider, "_with_retry", new=AsyncMock(return_value=mock_resp)):
        with pytest.raises(RuntimeError, match="generate failed"):
            await provider.generate([{"role": "user", "content": "hello"}])


@pytest.mark.asyncio
async def test_generate_total_tokens_is_sum(provider):
    mock_resp = _make_response(
        200, _chat_json(prompt_tokens=15, eval_count=25)
    )
    with patch.object(provider, "_with_retry", new=AsyncMock(return_value=mock_resp)):
        result = await provider.generate([{"role": "user", "content": "hello"}])
    assert result.total_tokens == 40
    assert result.prompt_tokens == 15
    assert result.completion_tokens == 25


# ---------------------------------------------------------------------------
# stream_generate() tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stream_generate_yields_delta_chunks(provider):
    lines = [
        json.dumps({"message": {"content": "Hello"}, "done": False}),
        json.dumps({"message": {"content": " world"}, "done": False}),
        json.dumps({"message": {"content": ""}, "done": True}),
    ]

    async def fake_aiter_lines():
        for line in lines:
            yield line

    mock_stream_resp = MagicMock()
    mock_stream_resp.status_code = 200
    mock_stream_resp.aiter_lines = fake_aiter_lines
    mock_stream_resp.__aenter__ = AsyncMock(return_value=mock_stream_resp)
    mock_stream_resp.__aexit__ = AsyncMock(return_value=False)

    client_mock = MagicMock()
    client_mock.stream = MagicMock(return_value=mock_stream_resp)

    with patch.object(provider, "_get_client", return_value=client_mock):
        chunks = []
        async for chunk in provider.stream_generate(
            [{"role": "user", "content": "hi"}]
        ):
            chunks.append(chunk)

    assert chunks == ["Hello", " world"]


@pytest.mark.asyncio
async def test_stream_generate_raises_on_http_error(provider):
    mock_stream_resp = MagicMock()
    mock_stream_resp.status_code = 503
    mock_stream_resp.aread = AsyncMock(return_value=b"Service Unavailable")
    mock_stream_resp.__aenter__ = AsyncMock(return_value=mock_stream_resp)
    mock_stream_resp.__aexit__ = AsyncMock(return_value=False)

    client_mock = MagicMock()
    client_mock.stream = MagicMock(return_value=mock_stream_resp)

    with patch.object(provider, "_get_client", return_value=client_mock):
        with pytest.raises(RuntimeError, match="stream failed"):
            async for _ in provider.stream_generate(
                [{"role": "user", "content": "hi"}]
            ):
                pass


# ---------------------------------------------------------------------------
# generate_structured() tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_structured_returns_parsed_dict(provider):
    schema = {
        "type": "object",
        "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
        "required": ["name", "age"],
    }
    content = json.dumps({"name": "Alice", "age": 30})
    mock_resp = _make_response(
        200, {"model": "llama3", "message": {"content": content}, "done": True}
    )
    with patch.object(provider, "_with_retry", new=AsyncMock(return_value=mock_resp)):
        result = await provider.generate_structured(
            [{"role": "user", "content": "Give me a user"}], schema=schema
        )
    assert result["name"] == "Alice"
    assert result["age"] == 30


@pytest.mark.asyncio
async def test_generate_structured_raises_on_invalid_json(provider):
    mock_resp = _make_response(
        200,
        {"model": "llama3", "message": {"content": "not valid json {{{"}, "done": True},
    )
    with patch.object(provider, "_with_retry", new=AsyncMock(return_value=mock_resp)):
        with pytest.raises(StructuredOutputError):
            await provider.generate_structured(
                [{"role": "user", "content": "?"}], schema={}
            )


# ---------------------------------------------------------------------------
# list_models() tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_models_returns_model_info_list(provider):
    models_data = {
        "models": [
            {
                "name": "llama3:latest",
                "size": 4_294_967_296,
                "modified_at": "2024-01-01T00:00:00Z",
                "details": {
                    "family": "llama",
                    "parameter_size": "8B",
                    "quantization_level": "Q4_0",
                },
            },
            {
                "name": "mistral:7b",
                "size": 3_800_000_000,
                "modified_at": "2024-02-01T00:00:00Z",
                "details": {
                    "family": "mistral",
                    "parameter_size": "7B",
                    "quantization_level": "Q4_K_M",
                },
            },
        ]
    }
    mock_resp = _make_response(200, models_data)
    client_mock = MagicMock()
    client_mock.get = AsyncMock(return_value=mock_resp)

    with patch.object(provider, "_get_client", return_value=client_mock):
        models = await provider.list_models()

    assert len(models) == 2
    assert models[0].name == "llama3:latest"
    assert models[0].parameter_size == "8B"
    assert models[1].quantization_level == "Q4_K_M"


@pytest.mark.asyncio
async def test_list_models_returns_empty_list_when_none_installed(provider):
    mock_resp = _make_response(200, {"models": []})
    client_mock = MagicMock()
    client_mock.get = AsyncMock(return_value=mock_resp)

    with patch.object(provider, "_get_client", return_value=client_mock):
        models = await provider.list_models()

    assert models == []


# ---------------------------------------------------------------------------
# pull_model() tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pull_model_succeeds(provider):
    progress_lines = [
        json.dumps({"status": "pulling manifest"}),
        json.dumps({"status": "downloading", "completed": 500, "total": 1000}),
        json.dumps({"status": "success"}),
    ]

    async def fake_aiter_lines():
        for line in progress_lines:
            yield line

    mock_stream_resp = MagicMock()
    mock_stream_resp.status_code = 200
    mock_stream_resp.aiter_lines = fake_aiter_lines
    mock_stream_resp.__aenter__ = AsyncMock(return_value=mock_stream_resp)
    mock_stream_resp.__aexit__ = AsyncMock(return_value=False)

    client_mock = MagicMock()
    client_mock.stream = MagicMock(return_value=mock_stream_resp)

    with patch.object(provider, "_get_client", return_value=client_mock):
        await provider.pull_model("llama3")  # Should not raise


@pytest.mark.asyncio
async def test_pull_model_raises_on_404(provider):
    mock_stream_resp = MagicMock()
    mock_stream_resp.status_code = 404
    mock_stream_resp.__aenter__ = AsyncMock(return_value=mock_stream_resp)
    mock_stream_resp.__aexit__ = AsyncMock(return_value=False)

    client_mock = MagicMock()
    client_mock.stream = MagicMock(return_value=mock_stream_resp)

    with patch.object(provider, "_get_client", return_value=client_mock):
        with pytest.raises(ModelPullError, match="not found"):
            await provider.pull_model("nonexistent-model")


# ---------------------------------------------------------------------------
# delete_model() tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_model_calls_correct_endpoint(provider):
    mock_resp = _make_response(200)
    client_mock = MagicMock()
    client_mock.request = AsyncMock(return_value=mock_resp)

    with patch.object(provider, "_get_client", return_value=client_mock):
        await provider.delete_model("llama3")

    client_mock.request.assert_awaited_once_with(
        "DELETE", "/api/delete", json={"name": "llama3"}
    )


# ---------------------------------------------------------------------------
# health_check() tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_check_returns_ok_when_model_installed(provider):
    mock_root_resp = _make_response(200)
    models_resp = _make_response(
        200,
        {"models": [{"name": "llama3:latest", "size": 1, "modified_at": "", "details": {}}]},
    )
    client_mock = MagicMock()
    client_mock.get = AsyncMock(side_effect=[mock_root_resp, models_resp])

    with patch.object(provider, "_get_client", return_value=client_mock):
        # list_models also uses _get_client, so patch it once
        with patch.object(
            provider,
            "list_models",
            new=AsyncMock(
                return_value=[OllamaModelInfo(name="llama3:latest", size_bytes=1)]
            ),
        ):
            status = await provider.health_check()

    assert status == HealthStatus.OK


@pytest.mark.asyncio
async def test_health_check_returns_down_on_connection_error(provider):
    import httpx

    client_mock = MagicMock()
    client_mock.get = AsyncMock(side_effect=httpx.ConnectError("refused"))

    with patch.object(provider, "_get_client", return_value=client_mock):
        status = await provider.health_check()

    assert status == HealthStatus.DOWN


@pytest.mark.asyncio
async def test_health_check_returns_degraded_when_model_missing(provider):
    mock_root_resp = _make_response(200)
    client_mock = MagicMock()
    client_mock.get = AsyncMock(return_value=mock_root_resp)

    with patch.object(provider, "_get_client", return_value=client_mock):
        with patch.object(
            provider,
            "list_models",
            new=AsyncMock(return_value=[]),  # no models installed
        ):
            status = await provider.health_check()

    assert status == HealthStatus.DEGRADED


# ---------------------------------------------------------------------------
# async context manager test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_context_manager_calls_aclose():
    provider = OllamaLocalProvider(model="llama3")
    with patch.object(provider, "aclose", new=AsyncMock()) as mock_aclose:
        async with provider:
            pass
        mock_aclose.assert_awaited_once()
