"""
Benchmark Route for Zakera AI Chat Agent.

Enables side-by-side comparison of multiple AI providers on the same prompt,
returning latency, token usage, and response content for each provider.

Endpoints
---------
POST   /benchmark/run            - Run a benchmark (blocking, waits for all providers)
POST   /benchmark/run/stream     - Streaming benchmark (NDJSON, updates as providers finish)
GET    /benchmark/history        - List past benchmark runs (paginated)
GET    /benchmark/history/{id}   - Get full detail for a single run
DELETE /benchmark/history/{id}   - Delete a run from history
POST   /benchmark/compare        - Compute diff stats between two run results
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/benchmark", tags=["benchmark"])

# ---------------------------------------------------------------------------
# In-memory history store (replace with DB-backed service in production)
# ---------------------------------------------------------------------------

_BENCHMARK_HISTORY_FILE = Path(__file__).resolve().parents[3] / "data" / "benchmark_history.json"


def _load_benchmark_history() -> Dict[str, Dict[str, Any]]:
    """Load persisted benchmark history from disk."""
    if not _BENCHMARK_HISTORY_FILE.exists():
        return {}

    try:
        with _BENCHMARK_HISTORY_FILE.open("r", encoding="utf-8") as handle:
            data = json.load(handle)

        if not isinstance(data, dict):
            return {}

        history: Dict[str, Dict[str, Any]] = {}
        for run_id, run_data in data.items():
            if isinstance(run_data, dict):
                history[str(run_id)] = run_data
        return history
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Failed to load benchmark history from %s: %s",
            _BENCHMARK_HISTORY_FILE,
            exc,
        )
        return {}


def _persist_benchmark_history() -> None:
    """Persist benchmark history to disk."""
    try:
        _BENCHMARK_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp_file = _BENCHMARK_HISTORY_FILE.with_name(f"{_BENCHMARK_HISTORY_FILE.name}.tmp")
        with tmp_file.open("w", encoding="utf-8") as handle:
            json.dump(_benchmark_history, handle, ensure_ascii=False, indent=2, default=str)
        tmp_file.replace(_BENCHMARK_HISTORY_FILE)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Failed to persist benchmark history to %s: %s",
            _BENCHMARK_HISTORY_FILE,
            exc,
        )


_benchmark_history: Dict[str, Dict[str, Any]] = _load_benchmark_history()


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class ProviderConfig(BaseModel):
    """Configuration for a single provider in a benchmark run."""

    provider_id: str = Field(..., description="Provider identifier, e.g. 'openai', 'anthropic', 'cohere'")
    model: str = Field(..., description="Model name, e.g. 'gpt-4o', 'claude-3-5-sonnet-20241022'")
    api_key: Optional[str] = Field(None, description="API key; falls back to server-side env variable if omitted")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1024, ge=1, le=16384)
    timeout_seconds: float = Field(default=30.0, ge=1.0, le=120.0)


class BenchmarkRequest(BaseModel):
    """Request body for a benchmark run."""

    prompt: str = Field(..., min_length=1, max_length=32000, description="The user prompt to evaluate")
    system_prompt: Optional[str] = Field(None, max_length=8000, description="Optional system-level instructions")
    providers: List[ProviderConfig] = Field(..., min_length=2, max_length=8,
                                             description="List of providers to benchmark (2-8)")
    tags: List[str] = Field(default_factory=list, description="Optional labels for this run")

    @field_validator("providers")
    @classmethod
    def unique_provider_models(cls, v: List[ProviderConfig]) -> List[ProviderConfig]:
        seen = set()
        for pc in v:
            key = f"{pc.provider_id}:{pc.model}"
            if key in seen:
                raise ValueError(f"Duplicate provider+model combination: {key}")
            seen.add(key)
        return v


class ProviderResult(BaseModel):
    """Result for a single provider in a benchmark run."""

    provider_id: str
    model: str
    status: str  # 'success' | 'error' | 'timeout'
    content: Optional[str] = None
    error_message: Optional[str] = None
    latency_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    finish_reason: Optional[str] = None


class BenchmarkRunResult(BaseModel):
    """Full result of a benchmark run."""

    run_id: str
    prompt: str
    system_prompt: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    results: List[ProviderResult]
    created_at: str
    total_duration_ms: float

    @property
    def successful_results(self) -> List[ProviderResult]:
        return [r for r in self.results if r.status == "success"]

    @property
    def fastest_provider(self) -> Optional[ProviderResult]:
        successes = self.successful_results
        return min(successes, key=lambda r: r.latency_ms) if successes else None


class BenchmarkHistoryItem(BaseModel):
    """Summary item for benchmark history listing."""

    run_id: str
    prompt_preview: str
    provider_ids: List[str]
    tags: List[str]
    created_at: str
    total_duration_ms: float
    success_count: int
    error_count: int


class CompareRequest(BaseModel):
    """Request body for comparing two provider results."""

    run_id: str
    provider_a: str  # provider_id:model
    provider_b: str  # provider_id:model


class CompareResult(BaseModel):
    """Diff stats between two provider results."""

    provider_a: str
    provider_b: str
    latency_delta_ms: float
    token_delta: int
    content_similarity: float  # overlap coefficient 0.0-1.0
    faster_provider: str
    more_concise_provider: str
    content_a: Optional[str] = None
    content_b: Optional[str] = None


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------


def _store_benchmark_run(run_result: BenchmarkRunResult) -> None:
    """Store a run result in memory and persist it to disk."""
    _benchmark_history[run_result.run_id] = run_result.model_dump()
    _persist_benchmark_history()


def _extract_response_content(response: Any) -> str:
    """Extract response text from provider return values."""
    if response is None:
        return ""

    if isinstance(response, dict):
        if isinstance(response.get("content"), str):
            return response["content"]
        if isinstance(response.get("text"), str):
            return response["text"]
        choices = response.get("choices")
        if choices:
            first_choice = choices[0]
            if isinstance(first_choice, dict):
                message = first_choice.get("message", {})
                if isinstance(message, dict) and isinstance(message.get("content"), str):
                    return message["content"]
                delta = first_choice.get("delta", {})
                if isinstance(delta, dict) and isinstance(delta.get("content"), str):
                    return delta["content"]

    content = getattr(response, "content", None)
    if isinstance(content, str):
        return content

    text = getattr(response, "text", None)
    if isinstance(text, str):
        return text

    return str(response)


def _extract_response_model(response: Any, default_model: str) -> str:
    """Extract the model name from a provider response."""
    if isinstance(response, dict):
        model = response.get("model")
        if isinstance(model, str) and model:
            return model

    model = getattr(response, "model", None)
    if isinstance(model, str) and model:
        return model

    return default_model


def _extract_response_usage(response: Any) -> Dict[str, int]:
    """Extract token usage from a provider response."""
    usage = None
    if isinstance(response, dict):
        usage = response.get("usage")
    else:
        usage = getattr(response, "usage", None)

    def _get_usage_field(name: str) -> int:
        if usage is None:
            return 0
        if isinstance(usage, dict):
            return int(usage.get(name, 0) or 0)
        return int(getattr(usage, name, 0) or 0)

    prompt_tokens = _get_usage_field("prompt_tokens")
    completion_tokens = _get_usage_field("completion_tokens")
    total_tokens = _get_usage_field("total_tokens")

    if total_tokens <= 0:
        total_tokens = prompt_tokens + completion_tokens

    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
    }


def _extract_finish_reason(response: Any) -> Optional[str]:
    """Extract finish reason from a provider response."""
    if isinstance(response, dict):
        finish_reason = response.get("finish_reason") or response.get("stop_reason")
        if isinstance(finish_reason, str):
            return finish_reason

    finish_reason = getattr(response, "finish_reason", None) or getattr(response, "stop_reason", None)
    if isinstance(finish_reason, str):
        return finish_reason

    return None


# ---------------------------------------------------------------------------
# Provider dispatch (stub — wires to real providers via model_manager)
# ---------------------------------------------------------------------------


async def _call_provider(
    config: ProviderConfig,
    prompt: str,
    system_prompt: Optional[str],
) -> ProviderResult:
    """
    Dispatch a chat request to a provider and return a ProviderResult.

    This implementation uses the shared ModelManager provider registry.
    """
    start_ts = time.perf_counter()
    try:
        from src.model import model_manager
        from src.model.providers import Message

        provider = model_manager.get_provider(config.provider_id)
        original_model_name = getattr(provider, "model_name", None)
        original_config_model = getattr(getattr(provider, "config", None), "model", None)

        try:
            if hasattr(provider, "model_name"):
                provider.model_name = config.model
            if hasattr(provider, "config") and hasattr(provider.config, "model"):
                provider.config.model = config.model

            messages: List[Message] = []
            if system_prompt:
                messages.append(Message(role="system", content=system_prompt))
            messages.append(Message(role="user", content=prompt))

            generate_kwargs: Dict[str, Any] = {
                "temperature": config.temperature,
                "max_tokens": config.max_tokens,
                "model": config.model,
            }

            if hasattr(provider, "generate"):
                response = await provider.generate(messages=messages, **generate_kwargs)
            elif hasattr(provider, "chat"):
                response = await provider.chat(messages=messages, **generate_kwargs)
            else:
                raise AttributeError(
                    f"Provider '{config.provider_id}' does not expose a generate/chat method."
                )
        finally:
            if hasattr(provider, "model_name"):
                provider.model_name = original_model_name
            if hasattr(provider, "config") and hasattr(provider.config, "model"):
                provider.config.model = original_config_model

        latency_ms = (time.perf_counter() - start_ts) * 1000
        usage = _extract_response_usage(response)
        return ProviderResult(
            provider_id=config.provider_id,
            model=_extract_response_model(response, config.model),
            status="success",
            content=_extract_response_content(response),
            latency_ms=latency_ms,
            input_tokens=usage["prompt_tokens"],
            output_tokens=usage["completion_tokens"],
            total_tokens=usage["total_tokens"],
            finish_reason=_extract_finish_reason(response),
        )

    except asyncio.TimeoutError:
        latency_ms = (time.perf_counter() - start_ts) * 1000
        return ProviderResult(
            provider_id=config.provider_id,
            model=config.model,
            status="timeout",
            error_message=f"Request timed out after {config.timeout_seconds}s",
            latency_ms=latency_ms,
        )
    except Exception as exc:  # noqa: BLE001
        latency_ms = (time.perf_counter() - start_ts) * 1000
        logger.warning(
            "Provider %s/%s failed: %s",
            config.provider_id,
            config.model,
            exc,
        )
        return ProviderResult(
            provider_id=config.provider_id,
            model=config.model,
            status="error",
            error_message=str(exc),
            latency_ms=latency_ms,
        )


async def _run_providers_concurrently(
    request: BenchmarkRequest,
) -> tuple[List[ProviderResult], float]:
    """Run all providers concurrently and return results + total duration."""
    start = time.perf_counter()

    tasks = [
        asyncio.wait_for(
            _call_provider(pc, request.prompt, request.system_prompt),
            timeout=pc.timeout_seconds,
        )
        for pc in request.providers
    ]

    gathered = await asyncio.gather(*tasks, return_exceptions=True)

    results: List[ProviderResult] = []
    for i, item in enumerate(gathered):
        pc = request.providers[i]
        if isinstance(item, Exception):
            results.append(
                ProviderResult(
                    provider_id=pc.provider_id,
                    model=pc.model,
                    status="error",
                    error_message=str(item),
                    latency_ms=0.0,
                )
            )
        else:
            results.append(item)  # type: ignore[arg-type]

    total_ms = (time.perf_counter() - start) * 1000
    return results, total_ms


# ---------------------------------------------------------------------------
# Content similarity helper
# ---------------------------------------------------------------------------


def _overlap_coefficient(text_a: str, text_b: str) -> float:
    """
    Compute the overlap coefficient between two texts.

    overlap_coefficient = |A ∩ B| / min(|A|, |B|)

    Words are lower-cased and split on whitespace.
    Returns 0.0 if either text is empty.
    """
    if not text_a or not text_b:
        return 0.0
    words_a = set(text_a.lower().split())
    words_b = set(text_b.lower().split())
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    return len(intersection) / min(len(words_a), len(words_b))


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/run", response_model=BenchmarkRunResult, summary="Run a benchmark across providers")
async def run_benchmark(request: BenchmarkRequest) -> BenchmarkRunResult:
    """
    Fire the same prompt at multiple AI providers concurrently.

    Each provider call is independently time-limited. Results include
    response content, latency, token counts, and error information.
    The run is stored in benchmark history for later retrieval.
    """
    results, total_ms = await _run_providers_concurrently(request)

    run_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()

    run_result = BenchmarkRunResult(
        run_id=run_id,
        prompt=request.prompt,
        system_prompt=request.system_prompt,
        tags=request.tags,
        results=results,
        created_at=created_at,
        total_duration_ms=total_ms,
    )

    _store_benchmark_run(run_result)

    logger.info(
        "Benchmark run %s completed in %.0fms (%d providers, %d errors)",
        run_id,
        total_ms,
        len(results),
        sum(1 for r in results if r.status != "success"),
    )

    return run_result


@router.post("/run/stream", summary="Streaming benchmark — NDJSON events as providers complete")
async def run_benchmark_stream(request: BenchmarkRequest) -> StreamingResponse:
    """
    Run a benchmark and stream results progressively as each provider finishes.

    Emits NDJSON (newline-delimited JSON) events:
      - ``{"event": "provider_result", "data": <ProviderResult>}`` for each provider
      - ``{"event": "run_complete", "data": <BenchmarkRunResult>}`` at the end

    This allows the frontend to update the comparison panel incrementally
    rather than waiting for the slowest provider.
    """

    async def generate():
        start = time.perf_counter()
        run_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        all_results: List[ProviderResult] = []

        # Create individual tasks
        pending = {
            asyncio.ensure_future(
                asyncio.wait_for(
                    _call_provider(pc, request.prompt, request.system_prompt),
                    timeout=pc.timeout_seconds,
                )
            ): pc
            for pc in request.providers
        }

        while pending:
            done, _ = await asyncio.wait(pending.keys(), return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                pc = pending.pop(task)
                try:
                    result: ProviderResult = task.result()
                except Exception as exc:
                    result = ProviderResult(
                        provider_id=pc.provider_id,
                        model=pc.model,
                        status="error",
                        error_message=str(exc),
                    )
                all_results.append(result)
                event = {"event": "provider_result", "data": result.model_dump()}
                yield json.dumps(event) + "\n"

        total_ms = (time.perf_counter() - start) * 1000
        run_result = BenchmarkRunResult(
            run_id=run_id,
            prompt=request.prompt,
            system_prompt=request.system_prompt,
            tags=request.tags,
            results=all_results,
            created_at=created_at,
            total_duration_ms=total_ms,
        )
        _store_benchmark_run(run_result)

        final_event = {"event": "run_complete", "data": run_result.model_dump()}
        yield json.dumps(final_event) + "\n"

    return StreamingResponse(
        generate(),
        media_type="application/x-ndjson",
        headers={"X-Content-Type-Options": "nosniff"},
    )


@router.get(
    "/history",
    response_model=List[BenchmarkHistoryItem],
    summary="List past benchmark runs",
)
async def list_benchmark_history(
    page: int = Query(default=1, ge=1, description="Page number"),
    per_page: int = Query(default=20, ge=1, le=100, description="Results per page"),
    tag: Optional[str] = Query(default=None, description="Filter by tag"),
) -> List[BenchmarkHistoryItem]:
    """
    Return a paginated list of past benchmark runs, newest first.

    Optionally filter by tag.
    """
    runs = list(_benchmark_history.values())

    # Filter by tag if provided
    if tag:
        runs = [r for r in runs if tag in r.get("tags", [])]

    # Sort newest-first
    runs.sort(key=lambda r: r.get("created_at", ""), reverse=True)

    # Paginate
    start = (page - 1) * per_page
    end = start + per_page
    page_runs = runs[start:end]

    return [
        BenchmarkHistoryItem(
            run_id=r["run_id"],
            prompt_preview=r["prompt"][:80] + ("..." if len(r["prompt"]) > 80 else ""),
            provider_ids=[res["provider_id"] for res in r.get("results", [])],
            tags=r.get("tags", []),
            created_at=r["created_at"],
            total_duration_ms=r.get("total_duration_ms", 0.0),
            success_count=sum(1 for res in r.get("results", []) if res["status"] == "success"),
            error_count=sum(1 for res in r.get("results", []) if res["status"] != "success"),
        )
        for r in page_runs
    ]


@router.get(
    "/history/{run_id}",
    response_model=BenchmarkRunResult,
    summary="Get full detail for a benchmark run",
)
async def get_benchmark_run(run_id: str) -> BenchmarkRunResult:
    """Return the full result of a single benchmark run by ID."""
    run = _benchmark_history.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Benchmark run '{run_id}' not found.")
    return BenchmarkRunResult(**run)


@router.delete(
    "/history/{run_id}",
    summary="Delete a benchmark run from history",
)
async def delete_benchmark_run(run_id: str) -> Dict[str, str]:
    """Remove a benchmark run from the in-memory history store."""
    if run_id not in _benchmark_history:
        raise HTTPException(status_code=404, detail=f"Benchmark run '{run_id}' not found.")
    del _benchmark_history[run_id]
    _persist_benchmark_history()
    logger.info("Benchmark run %s deleted from history.", run_id)
    return {"status": "deleted", "run_id": run_id}


@router.post(
    "/compare",
    response_model=CompareResult,
    summary="Compare two provider results from a benchmark run",
)
async def compare_providers(request: CompareRequest) -> CompareResult:
    """
    Compute diff stats between two providers from an existing benchmark run.

    ``provider_a`` and ``provider_b`` are ``provider_id:model`` strings,
    e.g. ``"openai:gpt-4o"`` and ``"anthropic:claude-3-5-sonnet-20241022"``.

    Returns latency delta, token delta, and a content similarity score
    (overlap coefficient, range 0.0–1.0).
    """
    run = _benchmark_history.get(request.run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Benchmark run '{request.run_id}' not found.")

    def _find_result(key: str) -> Optional[Dict[str, Any]]:
        provider_id, _, model = key.partition(":")
        for res in run.get("results", []):
            if res["provider_id"] == provider_id and res["model"] == model:
                return res
        return None

    res_a = _find_result(request.provider_a)
    res_b = _find_result(request.provider_b)

    if not res_a:
        raise HTTPException(status_code=404, detail=f"Provider '{request.provider_a}' not found in run.")
    if not res_b:
        raise HTTPException(status_code=404, detail=f"Provider '{request.provider_b}' not found in run.")

    latency_delta = res_a["latency_ms"] - res_b["latency_ms"]
    token_delta = res_a["total_tokens"] - res_b["total_tokens"]
    similarity = _overlap_coefficient(
        res_a.get("content") or "",
        res_b.get("content") or "",
    )

    faster = request.provider_a if latency_delta <= 0 else request.provider_b
    more_concise = request.provider_a if res_a["total_tokens"] <= res_b["total_tokens"] else request.provider_b

    return CompareResult(
        provider_a=request.provider_a,
        provider_b=request.provider_b,
        latency_delta_ms=round(latency_delta, 2),
        token_delta=token_delta,
        content_similarity=round(similarity, 4),
        faster_provider=faster,
        more_concise_provider=more_concise,
        content_a=res_a.get("content"),
        content_b=res_b.get("content"),
    )
