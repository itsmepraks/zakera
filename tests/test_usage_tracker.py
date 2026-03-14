"""
tests/test_usage_tracker.py
============================
Unit tests for the token usage tracking service.

All tests use a fresh UsageTracker instance to avoid cross-test pollution.
"""

from __future__ import annotations

import asyncio
from datetime import datetime

import pytest

from src.api.services.usage_tracker import UsageRecord, UsageTracker


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tracker() -> UsageTracker:
    """Fresh tracker with a small max_records cap to test eviction."""
    return UsageTracker(max_records=100)


@pytest.fixture
def tiny_tracker() -> UsageTracker:
    """Tracker with max_records=5 to easily test deque eviction."""
    return UsageTracker(max_records=5)


# ---------------------------------------------------------------------------
# Basic recording
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_record_single_entry(tracker: UsageTracker) -> None:
    rec = await tracker.record(
        user_id="user_abc",
        provider="openai",
        model="gpt-4o",
        prompt_tokens=100,
        completion_tokens=50,
    )
    assert isinstance(rec, UsageRecord)
    assert rec.user_id == "user_abc"
    assert rec.total_tokens == 150
    assert rec.estimated_cost_usd > 0

    records = await tracker.get_recent_records(user_id="user_abc")
    assert len(records) == 1
    assert records[0]["model"] == "gpt-4o"


@pytest.mark.asyncio
async def test_record_sets_timestamp_automatically(tracker: UsageTracker) -> None:
    rec = await tracker.record(
        user_id="u1", provider="groq", model="llama3-70b-8192",
        prompt_tokens=10, completion_tokens=10,
    )
    assert isinstance(rec.timestamp, datetime)


@pytest.mark.asyncio
async def test_multiple_providers_aggregated_correctly(tracker: UsageTracker) -> None:
    await tracker.record("user1", "openai", "gpt-4o", 200, 100)
    await tracker.record("user1", "anthropic", "claude-3-haiku-20240307", 300, 150)
    await tracker.record("user1", "openai", "gpt-4o", 100, 50)

    summary = await tracker.get_user_summary("user1")
    assert summary["grand_total"]["call_count"] == 3
    assert summary["grand_total"]["total_tokens"] == 900
    # Two distinct (provider, model) buckets expected
    assert len(summary["by_model"]) == 2


# ---------------------------------------------------------------------------
# Cost estimation
# ---------------------------------------------------------------------------


def test_cost_estimation_openai_gpt4o() -> None:
    cost = UsageTracker.estimate_cost("gpt-4o", 1000, 500)
    # 1000 * 0.005/1000 + 500 * 0.015/1000 = 0.005 + 0.0075 = 0.0125
    assert abs(cost - 0.0125) < 1e-7


def test_cost_estimation_anthropic_claude_opus() -> None:
    cost = UsageTracker.estimate_cost("claude-3-opus-20240229", 1000, 500)
    # 1000 * 0.015/1000 + 500 * 0.075/1000 = 0.015 + 0.0375 = 0.0525
    assert abs(cost - 0.0525) < 1e-7


def test_cost_estimation_unknown_model_returns_zero() -> None:
    cost = UsageTracker.estimate_cost("some-future-model-9000", 1000, 1000)
    assert cost == 0.0


def test_cost_estimation_zero_tokens_returns_zero() -> None:
    assert UsageTracker.estimate_cost("gpt-4o", 0, 0) == 0.0


def test_together_ai_model_cost_lookup() -> None:
    cost = UsageTracker.estimate_cost(
        "meta-llama/Llama-3-70b-chat-hf", 1000, 1000
    )
    # 0.0009 + 0.0009 = 0.0018
    assert abs(cost - 0.0018) < 1e-7


def test_groq_model_cost_lookup() -> None:
    cost = UsageTracker.estimate_cost("llama3-70b-8192", 1000, 1000)
    # 0.00059 + 0.00079 = 0.00138
    assert abs(cost - 0.00138) < 1e-7


def test_xai_grok_model_cost_lookup() -> None:
    cost = UsageTracker.estimate_cost("grok-2", 1000, 1000)
    # 0.002 + 0.010 = 0.012
    assert abs(cost - 0.012) < 1e-7


# ---------------------------------------------------------------------------
# User isolation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_user_summary_isolates_per_user(tracker: UsageTracker) -> None:
    await tracker.record("alice", "openai", "gpt-4o", 100, 50)
    await tracker.record("bob", "groq", "llama3-70b-8192", 200, 100)
    await tracker.record("alice", "openai", "gpt-4o", 50, 25)

    alice_summary = await tracker.get_user_summary("alice")
    bob_summary = await tracker.get_user_summary("bob")

    assert alice_summary["grand_total"]["call_count"] == 2
    assert bob_summary["grand_total"]["call_count"] == 1


@pytest.mark.asyncio
async def test_get_global_summary_includes_all_users(tracker: UsageTracker) -> None:
    await tracker.record("alice", "openai", "gpt-4o", 100, 50)
    await tracker.record("bob", "groq", "llama3-70b-8192", 200, 100)

    global_summary = await tracker.get_global_summary()
    assert global_summary["grand_total"]["call_count"] == 2


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pagination_limit_offset(tracker: UsageTracker) -> None:
    for i in range(10):
        await tracker.record("pager", "openai", "gpt-3.5-turbo", i * 10, i * 5)

    page1 = await tracker.get_recent_records(user_id="pager", limit=4, offset=0)
    page2 = await tracker.get_recent_records(user_id="pager", limit=4, offset=4)

    assert len(page1) == 4
    assert len(page2) == 4
    # They should be different records
    assert page1[0]["prompt_tokens"] != page2[0]["prompt_tokens"]


# ---------------------------------------------------------------------------
# Reset
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reset_user_clears_only_that_user(tracker: UsageTracker) -> None:
    await tracker.record("alice", "openai", "gpt-4o", 100, 50)
    await tracker.record("bob", "openai", "gpt-4o", 200, 100)
    await tracker.record("alice", "openai", "gpt-4o", 50, 25)

    deleted = await tracker.reset_user("alice")
    assert deleted == 2

    alice_records = await tracker.get_recent_records(user_id="alice")
    bob_records = await tracker.get_recent_records(user_id="bob")
    assert len(alice_records) == 0
    assert len(bob_records) == 1


# ---------------------------------------------------------------------------
# Deque eviction
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_max_records_evicts_oldest(tiny_tracker: UsageTracker) -> None:
    for i in range(7):
        await tiny_tracker.record(
            "user_evict", "openai", "gpt-3.5-turbo", i * 10, i * 5
        )

    records = await tiny_tracker.get_recent_records(user_id="user_evict")
    # deque maxlen=5 means only 5 most-recent survive
    assert len(records) == 5


# ---------------------------------------------------------------------------
# Concurrency
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_concurrent_record_calls_thread_safe(tracker: UsageTracker) -> None:
    tasks = [
        tracker.record(f"user_{i % 5}", "groq", "llama3-8b-8192", 10, 10)
        for i in range(50)
    ]
    results = await asyncio.gather(*tasks)
    assert len(results) == 50
    all_records = await tracker.get_recent_records()
    assert len(all_records) == 50


# ---------------------------------------------------------------------------
# Summary structure
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_summary_includes_estimated_cost_usd(tracker: UsageTracker) -> None:
    await tracker.record("costing_user", "openai", "gpt-4o", 500, 250)
    summary = await tracker.get_user_summary("costing_user")
    assert summary["grand_total"]["estimated_cost_usd"] > 0
    assert summary["by_model"][0]["estimated_cost_usd"] > 0
