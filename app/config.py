"""Configuration management using pydantic-settings."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings."""
    
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)
    
    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/summary_db"
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # OpenAI
    openai_api_key: str
    
    # JWT
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Application
    app_name: str = "LangGraph Summary Service"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = "production"
    
    # Rate Limiting
    rate_limit_per_minute: int = 10
    
    # Sentry
    sentry_dsn: Optional[str] = None
    
    # Cache
    cache_ttl: int = 3600
    
    # API Keys
    api_key_length: int = 32


# Global settings instance
settings = Settings()
