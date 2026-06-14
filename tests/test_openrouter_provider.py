from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.api.routes.chat import _get_provider
from src.model.providers import Message, OpenRouterProvider, ToolDefinition


class FakeCompletions:
    def __init__(self) -> None:
        self.params = None

    async def create(self, **params):
        self.params = params
        return SimpleNamespace(
            model="anthropic/claude-sonnet-4.5",
            usage=SimpleNamespace(
                prompt_tokens=7,
                completion_tokens=5,
                total_tokens=12,
            ),
            choices=[
                SimpleNamespace(
                    finish_reason="stop",
                    message=SimpleNamespace(
                        content="hello via openrouter",
                        tool_calls=None,
                    ),
                )
            ],
        )


class FakeClient:
    def __init__(self) -> None:
        self.completions = FakeCompletions()
        self.chat = SimpleNamespace(completions=self.completions)


def test_openrouter_provider_reads_key_and_headers_from_environment(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    monkeypatch.setenv("OPENROUTER_SITE_URL", "https://zakera.example")
    monkeypatch.setenv("OPENROUTER_APP_NAME", "Zakera Test")

    provider = OpenRouterProvider(model_name="openrouter/auto")

    assert provider.api_key == "sk-or-test"
    assert provider.base_url == "https://openrouter.ai/api/v1"
    assert provider.default_headers == {
        "HTTP-Referer": "https://zakera.example",
        "X-OpenRouter-Title": "Zakera Test",
    }


def test_openrouter_provider_requires_api_key(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    provider = OpenRouterProvider(api_key="", model_name="openrouter/auto")

    with pytest.raises(ValueError, match="OpenRouter API key is required"):
        provider._get_client()


@pytest.mark.asyncio
async def test_openrouter_generate_uses_openai_compatible_payload(monkeypatch):
    fake_client = FakeClient()
    provider = OpenRouterProvider(api_key="sk-or-test", model_name="anthropic/claude-sonnet-4.5")
    monkeypatch.setattr(provider, "_get_client", lambda: fake_client)

    response = await provider.generate(
        [Message(role="user", content="Say hello")],
        tools=[
            ToolDefinition(
                name="calculator",
                description="Do arithmetic",
                parameters={"type": "object", "properties": {}},
            )
        ],
        temperature=0.2,
        max_tokens=64,
    )

    assert response.content == "hello via openrouter"
    assert response.model == "anthropic/claude-sonnet-4.5"
    assert response.usage == {
        "prompt_tokens": 7,
        "completion_tokens": 5,
        "total_tokens": 12,
    }
    assert fake_client.completions.params["model"] == "anthropic/claude-sonnet-4.5"
    assert fake_client.completions.params["messages"] == [{"role": "user", "content": "Say hello"}]
    assert fake_client.completions.params["tools"][0]["function"]["name"] == "calculator"
    assert fake_client.completions.params["tool_choice"] == "auto"


def test_chat_provider_resolution_supports_openrouter_prefix(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")

    provider = _get_provider("openrouter/anthropic/claude-sonnet-4.5")

    assert isinstance(provider, OpenRouterProvider)
    assert provider.model_name == "anthropic/claude-sonnet-4.5"


def test_chat_provider_resolution_supports_openrouter_latest_alias(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")

    provider = _get_provider("~openai/gpt-latest")

    assert isinstance(provider, OpenRouterProvider)
    assert provider.model_name == "~openai/gpt-latest"


def test_chat_provider_resolution_preserves_openrouter_router_slug(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")

    provider = _get_provider("openrouter/auto")

    assert isinstance(provider, OpenRouterProvider)
    assert provider.model_name == "openrouter/auto"
