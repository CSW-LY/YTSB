"""Application configuration management."""

from functools import lru_cache
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        protected_namespaces=("settings_",),
    )

    # Application
    app_name: str = "intent-service"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = "development"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_prefix: str = "/api/v1"

    # CORS
    cors_origins: List[str] = Field(default=["http://localhost:3000"])
    cors_allow_credentials: bool = True

    # Database
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "intent_service"
    db_user: str = "postgres"
    db_password: str = "123"
    db_pool_size: int = 20
    db_max_overflow: int = 10

    @property
    def database_url(self) -> str:
        """Get SQLAlchemy database URL."""
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def async_database_url(self) -> str:
        """Get async database URL."""
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
    redis_pool_size: int = 50
    cache_ttl: int = 3600

    @property
    def redis_url(self) -> str:
        """Get Redis URL."""
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"

    # Model
    model_type: str = "bge-m3"
    model_path: str = "D:\\model\\models--BAAI--bge-m3\\snapshots\\5617a9f61b028005a4858fdac845db406aefb181"
    model_device: str = "cpu"
    model_batch_size: int = 32
    model_max_length: int = 512

    # vLLM
    vllm_host: str = "localhost"
    vllm_port: int = 8001
    vllm_model_name: str = "D:\\model\\models--BAAI--bge-m3\\snapshots\\5617a9f61b028005a4858fdac845db406aefb181"

    @property
    def vllm_url(self) -> str:
        """Get vLLM server URL."""
        return f"http://{self.vllm_host}:{self.vllm_port}"

    # LLM Fallback
    llm_api_key: Optional[str] = None
    llm_base_url: Optional[str] = None
    llm_model: Optional[str] = None
    enable_llm_fallback: bool = False

    # Intent Recognition
    default_confidence_threshold: float = 0.7
    min_keyword_match: int = 1
    enable_regex_matching: bool = True
    enable_semantic_matching: bool = True
    enable_keyword_matching: bool = True
    semantic_similarity_threshold: float = 0.55

    # Performance
    enable_cache: bool = True
    cache_prefix: str = "intent:"
    request_timeout: int = 30
    max_batch_size: int = 100

    # Security
    api_key_header: str = "X-API-Key"
    admin_api_key: Optional[str] = None
    api_secret: Optional[str] = None  # For HMAC signature verification

    # Monitoring
    enable_metrics: bool = True
    metrics_port: int = 9090


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
