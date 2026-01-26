"""Application configuration settings."""
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    app_name: str = "Coach ShowMeGains"
    debug: bool = True
    
    # Database
    database_url: str = "postgresql+asyncpg://gainsly:gainslypass@localhost:5433/gainslydb"
    
    # Ollama LLM settings
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gemma3:4b"
    ollama_timeout: float = 1100.0  # seconds (18+ minutes for local LLM generation)
    
    # Ollama embedding settings
    ollama_embedding_model: str = "nomic-embed-text"
    ollama_embedding_timeout: float = 60.0
    
    # LLM Provider (for future cloud providers)
    llm_provider: Literal["ollama", "openai", "anthropic"] = "ollama"
    
    # Default user settings (for MVP without auth)
    default_user_id: int = 1
    
    # e1RM formula options
    default_e1rm_formula: Literal["epley", "brzycki", "lombardi", "oconner"] = "epley"
    
    # Recovery settings
    soreness_decay_hours: int = 10  # Hours for 1 point of soreness decay
    
    admin_api_token: str | None = "gainsly-admin-123"
    # also in .env file in the fronend folder

    # JWT Authentication settings
    secret_key: str = "your-secret-key-change-in-production-use-environment-variable"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
