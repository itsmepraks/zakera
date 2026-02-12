"""Example plugin that adds a custom tool."""

from typing import Dict, Any
import httpx

from ..base import Plugin, PluginMetadata, PluginHook


class WeatherToolPlugin(Plugin):
    """Plugin that adds weather lookup functionality."""
    
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="weather_tool",
            version="1.0.0",
            description="Adds weather lookup tool",
            author="Zakera Team",
            dependencies=[],
            tags=["tool", "weather", "api"],
            config_schema={
                "required": ["api_key"],
                "properties": {
                    "api_key": {"type": "string"},
                    "api_url": {
                        "type": "string",
                        "default": "https://api.openweathermap.org/data/2.5/weather"
                    },
                    "units": {
                        "type": "string",
                        "enum": ["metric", "imperial"],
                        "default": "metric"
                    }
                }
            }
        )
    
    async def initialize(self) -> None:
        """Initialize the weather tool."""
        await super().initialize()
        
        self.api_key = self.config["api_key"]
        self.api_url = self.config.get(
            "api_url",
            "https://api.openweathermap.org/data/2.5/weather"
        )
        self.units = self.config.get("units", "metric")
        
        self.logger.info("Weather tool plugin initialized")
    
    async def get_weather(self, location: str) -> Dict[str, Any]:
        """Get weather for a location.
        
        Args:
            location: City name or coordinates
            
        Returns:
            Weather data dictionary
        """
        params = {
            "q": location,
            "appid": self.api_key,
            "units": self.units
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.api_url, params=params)
                response.raise_for_status()
                data = response.json()
                
                return {
                    "location": data["name"],
                    "temperature": data["main"]["temp"],
                    "description": data["weather"][0]["description"],
                    "humidity": data["main"]["humidity"],
                    "wind_speed": data["wind"]["speed"],
                    "units": self.units
                }
        except httpx.HTTPError as e:
            self.logger.error(f"Error fetching weather: {e}")
            raise
    
    def get_tool_definition(self) -> Dict[str, Any]:
        """Get OpenAI function definition for this tool.
        
        Returns:
            Function definition for use with OpenAI function calling
        """
        return {
            "name": "get_weather",
            "description": "Get the current weather for a location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city name or location"
                    }
                },
                "required": ["location"]
            }
        }
