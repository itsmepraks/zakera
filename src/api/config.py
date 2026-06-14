from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Any, List


class Settings(BaseSettings):
    # API Configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    DEBUG: bool = True

    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    CORS_ORIGINS: str = ""

    # AI Model Configuration
    MODEL_PROVIDER: str = "openai"  # openai, anthropic, local
    MODEL_NAME: str = "gpt-4-turbo-preview"
    DEFAULT_MODEL: str = ""
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

    # Database
    DATABASE_URL: str = "sqlite:///./data/zakera.db"

    # Security
    SECRET_KEY: str = "change-me-in-production"
    JWT_SECRET_KEY: str = ""
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Conversation Settings
    MAX_CONVERSATION_HISTORY: int = 50
    MAX_TOKENS: int = 4000
    TEMPERATURE: float = 0.7

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def _parse_origins(cls, value: Any) -> List[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    def model_post_init(self, __context: Any) -> None:
        if self.CORS_ORIGINS:
            object.__setattr__(self, "ALLOWED_ORIGINS", self._parse_origins(self.CORS_ORIGINS))
        if self.JWT_SECRET_KEY and self.SECRET_KEY == "change-me-in-production":
            object.__setattr__(self, "SECRET_KEY", self.JWT_SECRET_KEY)
        if self.DEFAULT_MODEL and self.MODEL_NAME == "gpt-4-turbo-preview":
            object.__setattr__(self, "MODEL_NAME", self.DEFAULT_MODEL)


settings = Settings()
