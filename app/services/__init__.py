"""Service layer for business logic and external integrations."""
from .news.collector import news_collector

__all__ = [
    'news_collector',
]
