"""
Configuration management using .env file
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from .env file"""
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    # Upstage API
    upstage_api_key: str = ""

    # LangSmith
    langsmith_api_key: str = ""
    langsmith_project: str = "trade-onboarding-agent"
    langsmith_tracing: bool = True

    # Database (optional)
    database_url: str = ""

    # Redis Session Store
    redis_url: str = ""  # Example: "redis://localhost:6379/0"
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""
    redis_db: int = 0
    redis_ssl: bool = False
    session_ttl: int = 3600  # Session TTL in seconds (1 hour)
    use_redis_session: bool = False  # True for production, False for development

    # Application
    environment: str = "development"
    debug: bool = True

    # CORS
    cors_origins: list = ["http://localhost:8501", "http://localhost:3000"]

    # Vector Database
    vector_db_dir: str = "backend/vectorstore"
    collection_name: str = "trade_coaching_knowledge"
    auto_ingest_on_startup: bool = True  # 서버 시작 시 자동 임베딩 여부

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
