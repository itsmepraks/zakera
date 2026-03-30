"""
Web Search tool for searching the internet.

Provides integration with search engines (Google, Bing, DuckDuckGo)
to retrieve information from the web.
"""

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

import httpx

from src.tools.base import (
    Tool,
    ToolParameter,
    ToolParameterType,
    ToolResult,
    ToolExecutionError,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional dependency probe — resolved once at import time so that the error
# message is shown at call-time, not at import time (keeps startup clean).
# ---------------------------------------------------------------------------
try:
    from duckduckgo_search import AsyncDDGS as _AsyncDDGS  # type: ignore
    _DDGS_ASYNC_AVAILABLE = True
    _DDGS_AVAILABLE = True
except ImportError:
    _AsyncDDGS = None  # type: ignore
    _DDGS_ASYNC_AVAILABLE = False
    try:
        from duckduckgo_search import DDGS as _DDGS  # type: ignore
        _DDGS_AVAILABLE = True
    except ImportError:
        _DDGS = None  # type: ignore
        _DDGS_AVAILABLE = False


class WebSearchTool(Tool):
    """
    Tool for searching the web using search engines.

    Supports multiple search engines:
    - Google Custom Search API
    - Bing Search API
    - DuckDuckGo (via the ``duckduckgo-search`` library, no API key required)

    Configuration:
        Set environment variables:
        - GOOGLE_SEARCH_API_KEY:  Google Custom Search API key
        - GOOGLE_SEARCH_ENGINE_ID: Google Custom Search Engine ID
        - BING_SEARCH_API_KEY:    Bing Search API key

    DuckDuckGo requires the ``duckduckgo-search`` package::

        pip install duckduckgo-search>=6.0.0
    """

    def __init__(self):
        super().__init__()
        self.google_api_key   = os.getenv("GOOGLE_SEARCH_API_KEY")
        self.google_engine_id = os.getenv("GOOGLE_SEARCH_ENGINE_ID")
        self.bing_api_key     = os.getenv("BING_SEARCH_API_KEY")
        self._http_client: Optional[httpx.AsyncClient] = None

    # ------------------------------------------------------------------
    # Tool metadata
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        return (
            "Search the web for information using search engines. "
            "Returns a list of search results with titles, URLs, and snippets."
        )

    @property
    def category(self) -> str:
        return "information"

    @property
    def tags(self) -> List[str]:
        return ["search", "web", "internet", "google", "bing", "duckduckgo", "information"]

    @property
    def rate_limit(self) -> Optional[int]:
        return 10  # 10 searches per minute

    @property
    def timeout(self) -> int:
        return 20  # seconds — raised from 10 to give DDG more breathing room

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="query",
                type=ToolParameterType.STRING,
                description="Search query string",
                required=True,
            ),
            ToolParameter(
                name="num_results",
                type=ToolParameterType.INTEGER,
                description="Number of results to return (max 10)",
                required=False,
                default=5,
                min_value=1,
                max_value=10,
            ),
            ToolParameter(
                name="engine",
                type=ToolParameterType.STRING,
                description="Search engine to use",
                required=False,
                default="duckduckgo",
                enum=["google", "bing", "duckduckgo"],
            ),
            ToolParameter(
                name="safesearch",
                type=ToolParameterType.STRING,
                description=(
                    "Safe-search filtering level (DuckDuckGo only). "
                    "'strict' filters explicit content, 'moderate' is balanced, "
                    "'off' disables filtering."
                ),
                required=False,
                default="moderate",
                enum=["strict", "moderate", "off"],
            ),
            ToolParameter(
                name="region",
                type=ToolParameterType.STRING,
                description=(
                    "Region code for results (DuckDuckGo only). "
                    "Examples: us-en (US English), gb-en (UK English), "
                    "de-de (Germany), fr-fr (France), wt-wt (worldwide)."
                ),
                required=False,
                default="wt-wt",
            ),
        ]

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def initialize(self) -> None:
        """Initialize the shared HTTP client (used by Google and Bing)."""
        await super().initialize()
        self._http_client = httpx.AsyncClient(timeout=self.timeout)

    async def cleanup(self) -> None:
        """Close the shared HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
        await super().cleanup()

    # ------------------------------------------------------------------
    # Google backend
    # ------------------------------------------------------------------

    async def _search_google(
        self,
        query: str,
        num_results: int,
    ) -> List[Dict[str, Any]]:
        """Search using the Google Custom Search API."""
        if not self.google_api_key or not self.google_engine_id:
            raise ToolExecutionError(
                "Google Search API credentials not configured. "
                "Set GOOGLE_SEARCH_API_KEY and GOOGLE_SEARCH_ENGINE_ID."
            )

        url    = "https://www.googleapis.com/customsearch/v1"
        params = {
            "key": self.google_api_key,
            "cx":  self.google_engine_id,
            "q":   query,
            "num": num_results,
        }

        response = await self._http_client.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        results = []
        for item in data.get("items", [])[:num_results]:
            results.append({
                "title":   item.get("title", ""),
                "url":     item.get("link", ""),
                "snippet": item.get("snippet", ""),
                "source":  "google",
            })
        return results

    # ------------------------------------------------------------------
    # Bing backend
    # ------------------------------------------------------------------

    async def _search_bing(
        self,
        query: str,
        num_results: int,
    ) -> List[Dict[str, Any]]:
        """Search using the Bing Web Search API."""
        if not self.bing_api_key:
            raise ToolExecutionError(
                "Bing Search API key not configured. "
                "Set BING_SEARCH_API_KEY environment variable."
            )

        url     = "https://api.bing.microsoft.com/v7.0/search"
        headers = {"Ocp-Apim-Subscription-Key": self.bing_api_key}
        params  = {
            "q":              query,
            "count":          num_results,
            "responseFilter": "Webpages",
        }

        response = await self._http_client.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()

        results = []
        for item in data.get("webPages", {}).get("value", [])[:num_results]:
            results.append({
                "title":   item.get("name", ""),
                "url":     item.get("url", ""),
                "snippet": item.get("snippet", ""),
                "source":  "bing",
            })
        return results

    # ------------------------------------------------------------------
    # DuckDuckGo backend  (real implementation)
    # ------------------------------------------------------------------

    async def _search_duckduckgo(
        self,
        query: str,
        num_results: int,
        safesearch: str = "moderate",
        region: str = "wt-wt",
    ) -> List[Dict[str, Any]]:
        """Search using the ``duckduckgo-search`` library.

        Prefers the async ``AsyncDDGS`` class (available in
        ``duckduckgo-search >= 4.0``).  Falls back to the synchronous
        ``DDGS`` class wrapped in :func:`asyncio.to_thread` when only the
        sync variant is installed.

        Args:
            query:       The search query string.
            num_results: Maximum number of results to return (1–10).
            safesearch:  Content-filter level — ``"strict"``, ``"moderate"``,
                         or ``"off"``.
            region:      DuckDuckGo region code, e.g. ``"us-en"``, ``"gb-en"``,
                         ``"wt-wt"`` (worldwide, default).

        Returns:
            List of result dicts with keys ``title``, ``url``, ``snippet``,
            ``source``.

        Raises:
            ToolExecutionError: If ``duckduckgo-search`` is not installed or
                                if the search returns no usable results.
        """
        if not _DDGS_AVAILABLE:
            raise ToolExecutionError(
                "The 'duckduckgo-search' package is required for DuckDuckGo searches "
                "but is not installed. Run: pip install duckduckgo-search>=6.0.0"
            )

        # Normalise safesearch value to what DDGS expects
        # duckduckgo-search accepts: "on" (strict), "moderate", "off"
        _safesearch_map: Dict[str, str] = {
            "strict":   "on",
            "moderate": "moderate",
            "off":      "off",
        }
        ddgs_safesearch = _safesearch_map.get(safesearch, "moderate")

        try:
            if _DDGS_ASYNC_AVAILABLE:
                # ── Async path (duckduckgo-search >= 4.0) ──────────────────
                raw: List[Dict[str, Any]] = []
                async with _AsyncDDGS() as ddgs:
                    async for result in ddgs.text(
                        query,
                        region=region,
                        safesearch=ddgs_safesearch,
                        max_results=num_results,
                    ):
                        raw.append(result)
                        if len(raw) >= num_results:
                            break
            else:
                # ── Sync-in-thread path (duckduckgo-search < 4.0) ──────────
                def _sync_search() -> List[Dict[str, Any]]:
                    with _DDGS() as ddgs:  # type: ignore[arg-type]
                        return list(
                            ddgs.text(
                                query,
                                region=region,
                                safesearch=ddgs_safesearch,
                                max_results=num_results,
                            )
                        )

                raw = await asyncio.to_thread(_sync_search)

        except Exception as exc:
            # Catch rate-limit / network errors from the DDGS library and
            # surface them as a ToolExecutionError with a helpful message.
            logger.warning("DuckDuckGo search raised an exception: %s", exc)
            raise ToolExecutionError(
                f"DuckDuckGo search failed: {exc}. "
                "This may be a temporary rate-limit. Please retry in a moment."
            ) from exc

        if not raw:
            logger.warning(
                "DuckDuckGo returned no results for query=%r "
                "region=%r safesearch=%r",
                query, region, safesearch,
            )
            # Return a graceful empty list rather than raising; callers can
            # decide how to handle zero results.
            return []

        results: List[Dict[str, Any]] = []
        for item in raw[:num_results]:
            results.append({
                # duckduckgo-search uses "title", "href", "body" as keys
                "title":   item.get("title") or "",
                "url":     item.get("href")  or item.get("url", ""),
                "snippet": item.get("body")  or item.get("snippet", ""),
                "source":  "duckduckgo",
            })

        logger.debug(
            "DuckDuckGo returned %d results for query=%r",
            len(results), query,
        )
        return results

    # ------------------------------------------------------------------
    # Public execute()
    # ------------------------------------------------------------------

    async def execute(
        self,
        query: str,
        num_results: int = 5,
        engine: str = "duckduckgo",
        safesearch: str = "moderate",
        region: str = "wt-wt",
        **kwargs: Any,
    ) -> ToolResult:
        """Execute a web search and return structured results.

        Args:
            query:       The search query.
            num_results: How many results to return (1–10).
            engine:      Which search engine to use
                         (``"google"``, ``"bing"``, or ``"duckduckgo"``).
            safesearch:  Safe-search level for DuckDuckGo
                         (``"strict"``, ``"moderate"``, ``"off"``).
            region:      Region code for DuckDuckGo results
                         (e.g. ``"us-en"``, ``"gb-en"``, ``"wt-wt"``).
            **kwargs:    Ignored; accepted for forward-compatibility.

        Returns:
            :class:`~src.tools.base.ToolResult` containing a list of result
            dicts with keys ``title``, ``url``, ``snippet``, ``source``.
        """
        try:
            if engine == "google":
                results = await self._search_google(query, num_results)
            elif engine == "bing":
                results = await self._search_bing(query, num_results)
            elif engine == "duckduckgo":
                results = await self._search_duckduckgo(
                    query,
                    num_results,
                    safesearch=safesearch,
                    region=region,
                )
            else:
                return ToolResult.error_result(
                    f"Unsupported search engine: '{engine}'. "
                    "Choose from: google, bing, duckduckgo."
                )

            return ToolResult.success_result(
                data={
                    "query":   query,
                    "results": results,
                    "count":   len(results),
                },
                metadata={
                    "engine":         engine,
                    "num_requested":  num_results,
                    "num_returned":   len(results),
                    "safesearch":     safesearch if engine == "duckduckgo" else None,
                    "region":         region     if engine == "duckduckgo" else None,
                },
            )

        except ToolExecutionError as exc:
            return ToolResult.error_result(str(exc))
        except httpx.HTTPStatusError as exc:
            return ToolResult.error_result(
                f"Search API error: HTTP {exc.response.status_code}"
            )
        except httpx.RequestError as exc:
            return ToolResult.error_result(f"Network error: {exc}")
        except Exception as exc:
            logger.exception("Unexpected error in web search")
            return ToolResult.error_result(f"Search failed: {exc}")
