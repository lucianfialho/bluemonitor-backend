"""Application configuration settings."""
from functools import lru_cache
from typing import Any, Dict, List, Optional, Union

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True
    )

    # Application
    APP_NAME: str = "BlueMonitor Backend"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    SECRET_KEY: str
    API_V1_STR: str = "/api/v1"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []

    # MongoDB
    MONGODB_URL: str
    MONGODB_DB_NAME: str = "bluemonitor"

    # SerpAPI
    SERPAPI_KEY: str
    SERPAPI_ENDPOINT: str = "https://google.serper.dev/search"

    # News Collection
    NEWS_QUERY_INTERVAL_MINUTES: int = 120
    MAX_NEWS_ARTICLES_PER_QUERY: int = 25

    # AI Models
    SENTENCE_TRANSFORMER_MODEL: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    SUMMARIZATION_MODEL: str = "facebook/bart-large-cnn"
    HF_HOME: str = "./models"  # Directory for storing Hugging Face models

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(
        cls, v: Union[str, List[str]]
    ) -> Union[List[str], str]:
        """Parse CORS origins from environment."""
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    @property
    def is_production(self) -> bool:
        """Check if the application is running in production."""
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        """Check if the application is running in development."""
        return self.ENVIRONMENT == "development"

    @property
    def is_testing(self) -> bool:
        """Check if the application is running in test mode."""
        return self.ENVIRONMENT == "test"


@lru_cache()
def get_settings() -> Settings:
    """
    Get application settings.

    This function is cached to prevent reloading the .env file on every request.
    """
    return Settings()  # type: ignore


# Create a settings instance to be imported by other modules
settings = get_settings()
