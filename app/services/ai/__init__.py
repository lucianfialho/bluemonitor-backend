"""AI and machine learning services."""
from .processor import ai_processor, process_news_content
from .topic_cluster import topic_cluster
from .navigation import navigation_system      # ADICIONAR
from .fact_extraction import fact_extraction_system  # ADICIONAR

__all__ = [
    'ai_processor',
    'process_news_content',
    'topic_cluster',
    'navigation_system',                       # ADICIONAR
    'fact_extraction_system',                  # ADICIONAR
]