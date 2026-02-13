"""
Weather tool for retrieving weather information.

Integrates with weather APIs to provide current conditions,
forecasts, and weather data for locations worldwide.
"""

import os
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

import httpx

from src.tools.base import (
    Tool,
    ToolParameter,
    ToolParameterType,
    ToolResult,
    ToolExecutionError,
)

logger = logging.getLogger(__name__)


class WeatherTool(Tool):
    """
    Tool for getting weather information for locations.
    
    Uses OpenWeatherMap API for weather data.
    
    Configuration:
        Set OPENWEATHER_API_KEY environment variable with your API key.
        Get a free API key at: https://openweathermap.org/api
    
    Features:
    - Current weather conditions
    - Temperature, humidity, wind speed
    - Weather description
    - Support for multiple units (metric, imperial)
    """
    
    def __init__(self):
        super().__init__()
        self.api_key = os.getenv("OPENWEATHER_API_KEY")
        self._http_client: Optional[httpx.AsyncClient] = None
    
    @property
    def name(self) -> str:
        return "weather"
    
    @property
    def description(self) -> str:
        return (
            "Get current weather information for a location. "
            "Returns temperature, conditions, humidity, wind speed, and more."
        )
    
    @property
    def category(self) -> str:
        return "information"
    
    @property
    def tags(self) -> List[str]:
        return ["weather", "temperature", "forecast", "climate", "conditions"]
    
    @property
    def rate_limit(self) -> Optional[int]:
        return 20  # 20 calls per minute
    
    @property
    def timeout(self) -> int:
        return 10
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="location",
                type=ToolParameterType.STRING,
                description="City name or 'city,country' (e.g., 'London', 'Paris,FR')",
                required=True,
            ),
            ToolParameter(
                name="units",
                type=ToolParameterType.STRING,
                description="Unit system for temperature",
                required=False,
                default="metric",
                enum=["metric", "imperial", "standard"],
            ),
        ]
    
    async def initialize(self) -> None:
        """Initialize HTTP client."""
        await super().initialize()
        self._http_client = httpx.AsyncClient(timeout=self.timeout)
        
        if not self.api_key:
            logger.warning(
                "OpenWeatherMap API key not configured. "
                "Set OPENWEATHER_API_KEY environment variable."
            )
    
    async def cleanup(self) -> None:
        """Cleanup HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
        await super().cleanup()
    
    async def execute(
        self,
        location: str,
        units: str = "metric",
        **kwargs
    ) -> ToolResult:
        """
        Get weather information for a location.
        
        Args:
            location: City name or 'city,country'
            units: Unit system (metric, imperial, standard)
            
        Returns:
            ToolResult with weather data
        """
        try:
            if not self.api_key:
                return ToolResult.error_result(
                    "Weather API not configured. Set OPENWEATHER_API_KEY environment variable."
                )
            
            # Call OpenWeatherMap API
            url = "https://api.openweathermap.org/data/2.5/weather"
            params = {
                "q": location,
                "appid": self.api_key,
                "units": units,
            }
            
            response = await self._http_client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Extract relevant information
            main = data.get("main", {})
            weather = data.get("weather", [{}])[0]
            wind = data.get("wind", {})
            
            # Determine temperature unit
            temp_unit = {
                "metric": "°C",
                "imperial": "°F",
                "standard": "K"
            }.get(units, "")
            
            weather_info = {
                "location": data.get("name", location),
                "country": data.get("sys", {}).get("country", ""),
                "temperature": main.get("temp"),
                "feels_like": main.get("feels_like"),
                "temp_min": main.get("temp_min"),
                "temp_max": main.get("temp_max"),
                "temperature_unit": temp_unit,
                "humidity": main.get("humidity"),
                "pressure": main.get("pressure"),
                "description": weather.get("description", ""),
                "conditions": weather.get("main", ""),
                "wind_speed": wind.get("speed"),
                "wind_direction": wind.get("deg"),
                "cloudiness": data.get("clouds", {}).get("all"),
                "visibility": data.get("visibility"),
                "timestamp": datetime.utcfromtimestamp(data.get("dt", 0)).isoformat(),
            }
            
            # Create human-readable summary
            summary = (
                f"{weather_info['location']}: "
                f"{weather_info['temperature']}{temp_unit}, "
                f"{weather_info['description']}. "
                f"Humidity: {weather_info['humidity']}%, "
                f"Wind: {weather_info['wind_speed']} m/s"
            )
            
            return ToolResult.success_result(
                data={
                    "weather": weather_info,
                    "summary": summary,
                },
                metadata={
                    "units": units,
                    "api": "openweathermap",
                    "location_query": location,
                }
            )
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return ToolResult.error_result(f"Location not found: {location}")
            elif e.response.status_code == 401:
                return ToolResult.error_result("Invalid API key")
            else:
                return ToolResult.error_result(
                    f"Weather API error: HTTP {e.response.status_code}"
                )
        except httpx.RequestError as e:
            return ToolResult.error_result(f"Network error: {str(e)}")
        except Exception as e:
            logger.exception("Unexpected error in weather tool")
            return ToolResult.error_result(f"Weather lookup failed: {str(e)}")
