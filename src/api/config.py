from pydantic_settings import BaseSettings
from typing import List
import os
from pathlib import Path

class Settings(BaseSettings):
    # API Configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    DEBUG: bool = True
    
    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    
    # AI Model Configuration
    MODEL_PROVIDER: str = "openai"  # openai, anthropic, local, deepseek
    MODEL_NAME: str = "gpt-4-turbo-preview"
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_API_BASE: str = "https://api.deepseek.com/v1"
    
    # Database
    DATABASE_URL: str = "sqlite:///./data/zakera.db"
    
    # Security
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    # Conversation Settings
    MAX_CONVERSATION_HISTORY: int = 50
    MAX_TOKENS: int = 4000
    TEMPERATURE: float = 0.7
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    
    class Config:
        env_file = "config/.env"
        case_sensitive = True

settings = Settings()
