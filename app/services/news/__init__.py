"""News collection and processing services."""
from .collector import news_collector
from .validator import news_validator

__all__ = [
    'news_collector',
    'news_validator',
]
