"""API v1 endpoints package."""

from .health import router as health_router
from .topics import router as topics_router
from .news import router as news_router

__all__ = ["health_router", "topics_router", "news_router"]
