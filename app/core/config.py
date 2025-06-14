"""
Application configuration settings.

This module defines all the configuration settings for the BlueMonitor application.
It uses Pydantic's BaseSettings to load settings from environment variables with
fallback to default values.

Environment variables should be defined in the .env file in the root directory.

Example .env file:
    APP_NAME="BlueMonitor Backend"
    ENVIRONMENT=development
    DEBUG=True
    SECRET_KEY=your-secret-key
    MONGODB_URL=mongodb://localhost:27017
    SERPAPI_KEY=your-serpapi-key
"""

from functools import lru_cache
from pathlib import Path
from typing import Any, List, Optional, Union

from pydantic import AnyHttpUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings.
    
    This class defines all configuration settings for the application.
    Settings are loaded from environment variables with fallback to default values.
    """
    
    # Pydantic model configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )
    
    # ===== Application Settings =====
    APP_NAME: str = "BlueMonitor Backend"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    SECRET_KEY: str = Field(..., description="Secret key for cryptographic operations")
    API_V1_STR: str = "/api/v1"
    
    # ===== Server Settings =====
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []
    
    # ===== Database Settings =====
    MONGODB_URL: str = Field(..., description="MongoDB connection string")
    MONGODB_DB_NAME: str = "bluemonitor"
    MONGODB_MAX_POOL_SIZE: int = 100
    MONGODB_MIN_POOL_SIZE: int = 5
    MONGODB_MAX_IDLE_TIME_MS: int = 30000
    
    # ===== External Services =====
    # SerpAPI Configuration
    SERPAPI_KEY: str = Field(..., description="API key for SerpAPI service")
    SERPAPI_ENDPOINT: str = "https://google.serper.dev/news"
    SERPAPI_TIMEOUT: int = 30  # seconds
    
    # ===== News Collection =====
    NEWS_QUERY_INTERVAL_MINUTES: int = 120
    MAX_NEWS_ARTICLES_PER_QUERY: int = 25
    NEWS_MAX_RETRIES: int = 3
    NEWS_RETRY_DELAY: int = 5  # seconds
    
    # ===== AI Models =====
    SENTENCE_TRANSFORMER_MODEL: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    SENTIMENT_MODEL: str = "cardiffnlp/twitter-xlm-roberta-base-sentiment"
    SUMMARIZATION_MODEL: str = "facebook/bart-large-cnn"
    HF_HOME: str = "./models"  # Directory for storing Hugging Face models
    
    # ===== Redis & Caching =====
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    REDIS_SSL: bool = False
    REDIS_TIMEOUT: int = 5  # seconds
    CACHE_TTL: int = 300  # 5 minutes
    
    # ===== Task Management =====
    TASK_CLEANUP_INTERVAL: int = 3600  # seconds (1 hour)
    TASK_RETENTION_DAYS: int = 7  # days to keep completed/failed tasks
    TASK_MAX_RETRIES: int = 3
    
    # ===== Security =====
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    SECURITY_BCRYPT_ROUNDS: int = 10
    
    # ===== Logging =====
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # ===== Helper Methods =====
    @classmethod
    def get_base_dir(cls) -> Path:
        """Get the base directory of the project."""
        return Path(__file__).resolve().parent.parent.parent
    
    @classmethod
    def get_env_path(cls) -> Path:
        """Get the path to the .env file."""
        return cls.get_base_dir() / ".env"
    
    @classmethod
    def get_models_dir(cls) -> Path:
        """Get the directory for storing model files."""
        return cls.get_base_dir() / "models"
    
    @classmethod
    def get_logs_dir(cls) -> Path:
        """Get the directory for log files."""
        return cls.get_base_dir() / "logs"
    
    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(
        cls, v: Union[str, List[str]]
    ) -> Union[List[str], str]:
        """Parse CORS origins from environment."""
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    @field_validator("MONGODB_URL", mode="before")
    @classmethod
    def validate_mongodb_url(cls, v: str) -> str:
        """Validate MongoDB URL format."""
        if not v:
            raise ValueError("MONGODB_URL is required")
        if not v.startswith(('mongodb://', 'mongodb+srv://')):
            raise ValueError("MONGODB_URL must start with 'mongodb://' or 'mongodb+srv://'")
        return v
    
    @property
    def is_production(self) -> bool:
        """Check if the application is running in production."""
        return self.ENVIRONMENT.lower() == "production"

    @property
    def is_development(self) -> bool:
        """Check if the application is running in development."""
        return self.ENVIRONMENT.lower() == "development"

    @property
    def is_testing(self) -> bool:
        """Check if the application is running in test mode."""
        return self.ENVIRONMENT.lower() == "test"
    
    @property
    def mongodb_connection_params(self) -> dict:
        """Get MongoDB connection parameters."""
        return {
            "host": self.MONGODB_URL,
            "maxPoolSize": self.MONGODB_MAX_POOL_SIZE,
            "minPoolSize": self.MONGODB_MIN_POOL_SIZE,
            "maxIdleTimeMS": self.MONGODB_MAX_IDLE_TIME_MS,
            "appname": self.APP_NAME,
        }
    
    @property
    def redis_connection_params(self) -> dict:
        """Get Redis connection parameters."""
        return {
            "host": self.REDIS_HOST,
            "port": self.REDIS_PORT,
            "db": self.REDIS_DB,
            "password": self.REDIS_PASSWORD,
            "ssl": self.REDIS_SSL,
            "socket_timeout": self.REDIS_TIMEOUT,
            "decode_responses": True,
        }


@lru_cache()
def get_settings() -> Settings:
    """
    Get application settings.
    
    This function is cached to prevent reloading the .env file on every request.
    It also ensures that the required directories exist and have the correct permissions.
    """
    import logging
    import os
    from pathlib import Path
    
    # Configure basic logging for the settings loading process
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    logger = logging.getLogger(__name__)
    
    # Get the path to the .env file
    env_path = Settings.get_env_path()
    
    # Log environment information
    logger.info(f"Loading settings from {env_path}")
    logger.debug(f"Current working directory: {os.getcwd()}")
    logger.debug(f"Environment: {os.environ.get('ENVIRONMENT', 'Not set')}")
    
    # Ensure required directories exist
    required_dirs = [
        Settings.get_models_dir(),
        Settings.get_logs_dir(),
    ]
    
    for directory in required_dirs:
        try:
            directory.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Ensured directory exists: {directory}")
        except Exception as e:
            logger.warning(f"Failed to create directory {directory}: {e}")
    
    # Load settings
    try:
        settings = Settings()
        
        # Log non-sensitive configuration
        logger.info(f"Loaded settings for {settings.APP_NAME}")
        logger.debug(f"Environment: {settings.ENVIRONMENT}")
        logger.debug(f"Debug mode: {settings.DEBUG}")
        logger.debug(f"MongoDB database: {settings.MONGODB_DB_NAME}")
        logger.debug(f"Redis host: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
        
        return settings
        
    except Exception as e:
        logger.critical(f"Failed to load settings: {e}", exc_info=True)
        raise


# Create a settings instance to be imported by other modules
settings = get_settings()
