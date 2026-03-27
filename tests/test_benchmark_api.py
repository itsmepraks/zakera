"""
Test suite for the /benchmark API routes.

Covers:
  - POST /benchmark/run (with mocked provider dispatch)
  - GET  /benchmark/history (pagination and tag filtering)
  - GET  /benchmark/history/{run_id} (found & not-found)
  - DELETE /benchmark/history/{run_id}
  - POST /benchmark/compare (diff stats)
  - Validation: duplicate providers, missing fields
  - Overlap coefficient helper
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI

from src.api.routes.benchmark import (
    router,
    ProviderResult,
    _benchmark_history,
    _overlap_coefficient,
)


# ---------------------------------------------------------------------------
# Test app setup
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clear_history():
    """Ensure benchmark history is clean between tests."""
    _benchmark_history.clear()
    yield
    _benchmark_history.clear()


@pytest.fixture
def app():
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_provider_result(provider_id="openai", model="gpt-4o", status="success",
                          content="Paris is the capital of France.",
                          latency_ms=320.5, input_tokens=25, output_tokens=15) -> ProviderResult:
    return ProviderResult(
        provider_id=provider_id,
        model=model,
        status=status,
        content=content,
        latency_ms=latency_ms,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=input_tokens + output_tokens,
        finish_reason="stop",
    )


BASE_RUN_PAYLOAD = {
    "prompt": "What is the capital of France?",
    "providers": [
        {"provider_id": "openai", "model": "gpt-4o"},
        {"provider_id": "anthropic", "model": "claude-3-5-sonnet-20241022"},
    ],
}


# ---------------------------------------------------------------------------
# POST /benchmark/run
# ---------------------------------------------------------------------------


class TestRunBenchmark:
    def test_run_returns_results_for_all_providers(self, client):
        openai_result = _make_provider_result("openai", "gpt-4o")
        anthropic_result = _make_provider_result("anthropic", "claude-3-5-sonnet-20241022",
                                                  latency_ms=410.0)

        results_map = {
            "openai:gpt-4o": openai_result,
            "anthropic:claude-3-5-sonnet-20241022": anthropic_result,
        }

        async def mock_call_provider(config, prompt, system_prompt):
            key = f"{config.provider_id}:{config.model}"
            return results_map[key]

        with patch("src.api.routes.benchmark._call_provider", new=mock_call_provider):
            resp = client.post("/api/v1/benchmark/run", json=BASE_RUN_PAYLOAD)

        assert resp.status_code == 200
        body = resp.json()
        assert body["prompt"] == "What is the capital of France?"
        assert len(body["results"]) == 2
        assert body["run_id"] != ""
        assert body["total_duration_ms"] >= 0

    def test_run_stores_in_history(self, client):
        result = _make_provider_result()

        async def mock_call(config, prompt, system_prompt):
            return _make_provider_result(provider_id=config.provider_id, model=config.model)

        with patch("src.api.routes.benchmark._call_provider", new=mock_call):
            resp = client.post("/api/v1/benchmark/run", json=BASE_RUN_PAYLOAD)

        run_id = resp.json()["run_id"]
        assert run_id in _benchmark_history

    def test_run_with_system_prompt(self, client):
        async def mock_call(config, prompt, system_prompt):
            return _make_provider_result(provider_id=config.provider_id, model=config.model)

        payload = {**BASE_RUN_PAYLOAD, "system_prompt": "You are a geography expert."}
        with patch("src.api.routes.benchmark._call_provider", new=mock_call):
            resp = client.post("/api/v1/benchmark/run", json=payload)

        assert resp.status_code == 200
        assert resp.json()["system_prompt"] == "You are a geography expert."

    def test_run_with_tags(self, client):
        async def mock_call(config, prompt, system_prompt):
            return _make_provider_result(provider_id=config.provider_id, model=config.model)

        payload = {**BASE_RUN_PAYLOAD, "tags": ["geography", "test"]}
        with patch("src.api.routes.benchmark._call_provider", new=mock_call):
            resp = client.post("/api/v1/benchmark/run", json=payload)

        assert resp.json()["tags"] == ["geography", "test"]

    def test_run_duplicate_providers_rejected(self, client):
        payload = {
            "prompt": "Hello",
            "providers": [
                {"provider_id": "openai", "model": "gpt-4o"},
                {"provider_id": "openai", "model": "gpt-4o"},  # duplicate
            ],
        }
        resp = client.post("/api/v1/benchmark/run", json=payload)
        assert resp.status_code == 422

    def test_run_single_provider_rejected(self, client):
        payload = {
            "prompt": "Hello",
            "providers": [{"provider_id": "openai", "model": "gpt-4o"}],
        }
        resp = client.post("/api/v1/benchmark/run", json=payload)
        assert resp.status_code == 422

    def test_run_provider_error_included_in_results(self, client):
        async def mock_call(config, prompt, system_prompt):
            if config.provider_id == "anthropic":
                raise RuntimeError("Authentication failed")
            return _make_provider_result(provider_id=config.provider_id, model=config.model)

        with patch("src.api.routes.benchmark._call_provider", new=mock_call):
            resp = client.post("/api/v1/benchmark/run", json=BASE_RUN_PAYLOAD)

        assert resp.status_code == 200
        results = resp.json()["results"]
        error_results = [r for r in results if r["status"] == "error"]
        assert len(error_results) == 1
        assert "Authentication failed" in error_results[0]["error_message"]


# ---------------------------------------------------------------------------
# GET /benchmark/history
# ---------------------------------------------------------------------------


class TestBenchmarkHistory:
    def _seed_run(self, run_id: str, tags=None, created_at="2026-03-26T10:00:00+00:00"):
        _benchmark_history[run_id] = {
            "run_id": run_id,
            "prompt": "Test prompt for run " + run_id,
            "system_prompt": None,
            "tags": tags or [],
            "results": [
                {"provider_id": "openai", "model": "gpt-4o", "status": "success",
                 "content": "Answer", "latency_ms": 200.0, "input_tokens": 10,
                 "output_tokens": 5, "total_tokens": 15, "finish_reason": "stop",
                 "error_message": None},
            ],
            "created_at": created_at,
            "total_duration_ms": 200.0,
        }

    def test_history_empty_returns_list(self, client):
        resp = client.get("/api/v1/benchmark/history")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_history_returns_seeded_runs(self, client):
        self._seed_run("run-1")
        self._seed_run("run-2")
        resp = client.get("/api/v1/benchmark/history")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_history_pagination(self, client):
        for i in range(5):
            self._seed_run(f"run-{i}")
        resp = client.get("/api/v1/benchmark/history?page=1&per_page=3")
        assert resp.status_code == 200
        assert len(resp.json()) == 3

    def test_history_page_2(self, client):
        for i in range(5):
            self._seed_run(f"run-{i}")
        resp = client.get("/api/v1/benchmark/history?page=2&per_page=3")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_history_tag_filter(self, client):
        self._seed_run("run-a", tags=["production"])
        self._seed_run("run-b", tags=["dev"])
        resp = client.get("/api/v1/benchmark/history?tag=production")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["run_id"] == "run-a"

    def test_history_prompt_preview_truncated(self, client):
        long_prompt = "A" * 200
        _benchmark_history["run-long"] = {
            "run_id": "run-long",
            "prompt": long_prompt,
            "system_prompt": None,
            "tags": [],
            "results": [],
            "created_at": "2026-03-26T10:00:00+00:00",
            "total_duration_ms": 0.0,
        }
        resp = client.get("/api/v1/benchmark/history")
        item = resp.json()[0]
        assert len(item["prompt_preview"]) <= 83  # 80 + "..."
        assert item["prompt_preview"].endswith("...")


# ---------------------------------------------------------------------------
# GET /benchmark/history/{run_id}
# ---------------------------------------------------------------------------


class TestGetBenchmarkRun:
    def test_get_existing_run(self, client):
        _benchmark_history["run-xyz"] = {
            "run_id": "run-xyz",
            "prompt": "Hello world",
            "system_prompt": None,
            "tags": [],
            "results": [],
            "created_at": "2026-03-26T10:00:00+00:00",
            "total_duration_ms": 150.0,
        }
        resp = client.get("/api/v1/benchmark/history/run-xyz")
        assert resp.status_code == 200
        assert resp.json()["run_id"] == "run-xyz"

    def test_get_nonexistent_run_returns_404(self, client):
        resp = client.get("/api/v1/benchmark/history/nonexistent-id")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /benchmark/history/{run_id}
# ---------------------------------------------------------------------------


class TestDeleteBenchmarkRun:
    def test_delete_existing_run(self, client):
        _benchmark_history["to-delete"] = {"run_id": "to-delete", "prompt": "x",
                                             "system_prompt": None, "tags": [],
                                             "results": [], "created_at": "",
                                             "total_duration_ms": 0.0}
        resp = client.delete("/api/v1/benchmark/history/to-delete")
        assert resp.status_code == 200
        assert resp.json()["status"] == "deleted"
        assert "to-delete" not in _benchmark_history

    def test_delete_nonexistent_run_returns_404(self, client):
        resp = client.delete("/api/v1/benchmark/history/does-not-exist")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /benchmark/compare
# ---------------------------------------------------------------------------


class TestCompareBenchmark:
    def _seed_run_with_two_providers(self) -> str:
        run_id = "compare-run-1"
        _benchmark_history[run_id] = {
            "run_id": run_id,
            "prompt": "Capital of France?",
            "system_prompt": None,
            "tags": [],
            "results": [
                {
                    "provider_id": "openai",
                    "model": "gpt-4o",
                    "status": "success",
                    "content": "Paris is the capital of France.",
                    "latency_ms": 300.0,
                    "input_tokens": 20,
                    "output_tokens": 10,
                    "total_tokens": 30,
                    "finish_reason": "stop",
                    "error_message": None,
                },
                {
                    "provider_id": "anthropic",
                    "model": "claude-3-5-sonnet-20241022",
                    "status": "success",
                    "content": "The capital of France is Paris.",
                    "latency_ms": 450.0,
                    "input_tokens": 22,
                    "output_tokens": 12,
                    "total_tokens": 34,
                    "finish_reason": "end_turn",
                    "error_message": None,
                },
            ],
            "created_at": "2026-03-26T10:00:00+00:00",
            "total_duration_ms": 450.0,
        }
        return run_id

    def test_compare_returns_diff_stats(self, client):
        run_id = self._seed_run_with_two_providers()
        payload = {
            "run_id": run_id,
            "provider_a": "openai:gpt-4o",
            "provider_b": "anthropic:claude-3-5-sonnet-20241022",
        }
        resp = client.post("/api/v1/benchmark/compare", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["latency_delta_ms"] == pytest.approx(-150.0, abs=1.0)
        assert data["token_delta"] == -4  # 30 - 34
        assert data["content_similarity"] > 0.5  # both mention Paris / France
        assert data["faster_provider"] == "openai:gpt-4o"
        assert data["more_concise_provider"] == "openai:gpt-4o"

    def test_compare_includes_content(self, client):
        run_id = self._seed_run_with_two_providers()
        payload = {
            "run_id": run_id,
            "provider_a": "openai:gpt-4o",
            "provider_b": "anthropic:claude-3-5-sonnet-20241022",
        }
        resp = client.post("/api/v1/benchmark/compare", json=payload)
        data = resp.json()
        assert data["content_a"] == "Paris is the capital of France."
        assert data["content_b"] == "The capital of France is Paris."

    def test_compare_run_not_found(self, client):
        payload = {"run_id": "ghost-run", "provider_a": "openai:gpt-4o",
                   "provider_b": "anthropic:claude"}
        resp = client.post("/api/v1/benchmark/compare", json=payload)
        assert resp.status_code == 404

    def test_compare_provider_not_in_run(self, client):
        run_id = self._seed_run_with_two_providers()
        payload = {"run_id": run_id, "provider_a": "openai:gpt-4o",
                   "provider_b": "cohere:command-r-plus"}
        resp = client.post("/api/v1/benchmark/compare", json=payload)
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Overlap coefficient helper
# ---------------------------------------------------------------------------


class TestOverlapCoefficient:
    def test_identical_texts(self):
        score = _overlap_coefficient("hello world", "hello world")
        assert score == pytest.approx(1.0)

    def test_no_overlap(self):
        score = _overlap_coefficient("cat dog", "fish bird")
        assert score == pytest.approx(0.0)

    def test_partial_overlap(self):
        score = _overlap_coefficient("the cat sat", "the cat ran")
        # intersection: {the, cat} = 2, min(3,3)=3
        assert score == pytest.approx(2 / 3, abs=0.01)

    def test_empty_string_a(self):
        assert _overlap_coefficient("", "hello") == 0.0

    def test_empty_string_b(self):
        assert _overlap_coefficient("hello", "") == 0.0

    def test_both_empty(self):
        assert _overlap_coefficient("", "") == 0.0

    def test_case_insensitive(self):
        score = _overlap_coefficient("PARIS", "paris")
        assert score == pytest.approx(1.0)
