"""
Web Search tool for searching the internet.

Provides integration with search engines (Google, Bing, DuckDuckGo)
to retrieve information from the web.
"""

import os
import logging
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


class WebSearchTool(Tool):
    """
    Tool for searching the web using search engines.
    
    Supports multiple search engines:
    - Google Custom Search API
    - Bing Search API
    - DuckDuckGo (no API key required)
    
    Configuration:
        Set environment variables:
        - GOOGLE_SEARCH_API_KEY: Google Custom Search API key
        - GOOGLE_SEARCH_ENGINE_ID: Google Custom Search Engine ID
        - BING_SEARCH_API_KEY: Bing Search API key
    """
    
    def __init__(self):
        super().__init__()
        self.google_api_key = os.getenv("GOOGLE_SEARCH_API_KEY")
        self.google_engine_id = os.getenv("GOOGLE_SEARCH_ENGINE_ID")
        self.bing_api_key = os.getenv("BING_SEARCH_API_KEY")
        self._http_client: Optional[httpx.AsyncClient] = None
    
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
        return ["search", "web", "internet", "google", "bing", "information"]
    
    @property
    def rate_limit(self) -> Optional[int]:
        return 10  # 10 searches per minute
    
    @property
    def timeout(self) -> int:
        return 10  # 10 seconds
    
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
        ]
    
    async def initialize(self) -> None:
        """Initialize HTTP client."""
        await super().initialize()
        self._http_client = httpx.AsyncClient(timeout=self.timeout)
    
    async def cleanup(self) -> None:
        """Cleanup HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
        await super().cleanup()
    
    async def _search_google(
        self,
        query: str,
        num_results: int
    ) -> List[Dict[str, Any]]:
        """Search using Google Custom Search API."""
        if not self.google_api_key or not self.google_engine_id:
            raise ToolExecutionError(
                "Google Search API credentials not configured. "
                "Set GOOGLE_SEARCH_API_KEY and GOOGLE_SEARCH_ENGINE_ID."
            )
        
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "key": self.google_api_key,
            "cx": self.google_engine_id,
            "q": query,
            "num": num_results,
        }
        
        response = await self._http_client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        results = []
        for item in data.get("items", [])[:num_results]:
            results.append({
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "snippet": item.get("snippet", ""),
                "source": "google",
            })
        
        return results
    
    async def _search_bing(
        self,
        query: str,
        num_results: int
    ) -> List[Dict[str, Any]]:
        """Search using Bing Search API."""
        if not self.bing_api_key:
            raise ToolExecutionError(
                "Bing Search API key not configured. "
                "Set BING_SEARCH_API_KEY environment variable."
            )
        
        url = "https://api.bing.microsoft.com/v7.0/search"
        headers = {"Ocp-Apim-Subscription-Key": self.bing_api_key}
        params = {
            "q": query,
            "count": num_results,
            "responseFilter": "Webpages",
        }
        
        response = await self._http_client.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        
        results = []
        for item in data.get("webPages", {}).get("value", [])[:num_results]:
            results.append({
                "title": item.get("name", ""),
                "url": item.get("url", ""),
                "snippet": item.get("snippet", ""),
                "source": "bing",
            })
        
        return results
    
    async def _search_duckduckgo(
        self,
        query: str,
        num_results: int
    ) -> List[Dict[str, Any]]:
        """
        Search using DuckDuckGo (HTML scraping fallback).
        
        Note: This is a simplified implementation. For production,
        consider using a proper DuckDuckGo API wrapper.
        """
        url = "https://html.duckduckgo.com/html/"
        params = {"q": query}
        
        try:
            response = await self._http_client.post(url, data=params)
            response.raise_for_status()
            
            # For now, return a placeholder
            # In production, parse HTML response
            return [{
                "title": f"Search result for: {query}",
                "url": f"https://duckduckgo.com/?q={quote_plus(query)}",
                "snippet": "DuckDuckGo search results. Note: HTML parsing not fully implemented.",
                "source": "duckduckgo",
            }]
            
        except Exception as e:
            logger.warning(f"DuckDuckGo search failed: {e}")
            # Return search URL as fallback
            return [{
                "title": f"Search: {query}",
                "url": f"https://duckduckgo.com/?q={quote_plus(query)}",
                "snippet": "Search on DuckDuckGo",
                "source": "duckduckgo",
            }]
    
    async def execute(
        self,
        query: str,
        num_results: int = 5,
        engine: str = "duckduckgo",
        **kwargs
    ) -> ToolResult:
        """
        Execute web search.
        
        Args:
            query: Search query
            num_results: Number of results to return
            engine: Search engine to use
            
        Returns:
            ToolResult with search results
        """
        try:
            # Select search engine
            if engine == "google":
                results = await self._search_google(query, num_results)
            elif engine == "bing":
                results = await self._search_bing(query, num_results)
            elif engine == "duckduckgo":
                results = await self._search_duckduckgo(query, num_results)
            else:
                return ToolResult.error_result(f"Unsupported search engine: {engine}")
            
            return ToolResult.success_result(
                data={
                    "query": query,
                    "results": results,
                    "count": len(results),
                },
                metadata={
                    "engine": engine,
                    "num_requested": num_results,
                    "num_returned": len(results),
                }
            )
            
        except ToolExecutionError as e:
            return ToolResult.error_result(str(e))
        except httpx.HTTPStatusError as e:
            return ToolResult.error_result(
                f"Search API error: HTTP {e.response.status_code}"
            )
        except httpx.RequestError as e:
            return ToolResult.error_result(f"Network error: {str(e)}")
        except Exception as e:
            logger.exception("Unexpected error in web search")
            return ToolResult.error_result(f"Search failed: {str(e)}")
