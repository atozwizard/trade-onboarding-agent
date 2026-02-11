"""
Configuration management using .env file
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from .env file"""

    # Upstage API
    upstage_api_key: str = ""

    # LangSmith
    langsmith_api_key: str = ""
    langsmith_project: str = "trade-onboarding-agent"
    langsmith_tracing: bool = True

    # Database (optional)
    database_url: str = ""
    redis_url: str = ""

    # Application
    environment: str = "development"
    debug: bool = True

    # CORS
    cors_origins: list = ["http://localhost:8501", "http://localhost:3000"]

    # Vector Database
    vector_db_dir: str = "backend/vectorstore"
    collection_name: str = "trade_coaching_knowledge"
    auto_ingest_on_startup: bool = True  # 서버 시작 시 자동 임베딩 여부

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
