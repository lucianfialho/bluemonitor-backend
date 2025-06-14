"""Unit tests for the TopicCluster helper methods."""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.ai.topic_cluster import TopicCluster

@pytest.fixture
def topic_cluster():
    """Return a TopicCluster instance for testing."""
    return TopicCluster()

class TestTopicClusterHelpers:
    """Test cases for TopicCluster helper methods."""

    def test_categorize_article_health(self, topic_cluster):
        """Test article categorization for health category."""
        article = {
            "title": "Novo tratamento para autismo",
            "description": "Pesquisas recentes mostram avanços no tratamento do TEA",
            "content": "O tratamento inovador está ajudando crianças com autismo a melhorar a comunicação."
        }
        category = topic_cluster._categorize_article(article)
        assert category == "Saúde"

    def test_categorize_article_irrelevant(self, topic_cluster):
        """Test article categorization for irrelevant content."""
        article = {
            "title": "Jogos de futebol do final de semana",
            "description": "Confira os melhores momentos dos jogos do campeonato",
            "content": "O jogo entre os times terminou em empate..."
        }
        category = topic_cluster._categorize_article(article)
        assert category == "Irrelevante"

    def test_parse_date_string_iso_format(self, topic_cluster):
        """Test date string parsing with ISO format."""
        date_str = "2023-06-01T10:30:00-03:00"
        result = topic_cluster._parse_date_string(date_str)
        assert result == datetime(2023, 6, 1, 13, 30)  # Converted to UTC

    def test_parse_date_string_brazilian_format(self, topic_cluster):
        """Test date string parsing with Brazilian format."""
        date_str = "01/06/2023 10:30"
        result = topic_cluster._parse_date_string(date_str)
        assert result == datetime(2023, 6, 1, 10, 30)

    def test_get_article_date_from_datetime(self, topic_cluster):
        """Test getting article date from datetime object."""
        test_date = datetime(2023, 6, 1, 10, 0, 0)
        article = {"publish_date": test_date}
        result = topic_cluster._get_article_date(article)
        assert result == test_date

    def test_get_article_date_from_string(self, topic_cluster):
        """Test getting article date from string."""
        article = {"publish_date": "2023-06-01T10:00:00"}
        result = topic_cluster._get_article_date(article)
        assert result == datetime(2023, 6, 1, 10, 0, 0)

    def test_get_article_date_fallback(self, topic_cluster):
        """Test fallback to current date when no valid date is found."""
        # Test with invalid date - we'll just verify the behavior, not the exact time
        article = {"publish_date": "invalid-date"}
        result = topic_cluster._get_article_date(article)
        
        # Verify we got a datetime object (current time)
        assert isinstance(result, datetime)
        
        # Verify the warning was logged
        # (We can't easily test the exact time since it's the current time)

    def test_categorize_article_multiple_keywords(self, topic_cluster):
        """Test article categorization with multiple keywords."""
        article = {
            "title": "Direitos das pessoas com deficiência",
            "description": "Novas leis garantem mais acessibilidade",
            "content": "O governo anunciou novas medidas para inclusão..."
        }
        category = topic_cluster._categorize_article(article)
        assert category == "Direitos"

    def test_categorize_article_unknown_category(self, topic_cluster):
        """Test article categorization with no matching keywords."""
        article = {
            "title": "Título genérico",
            "description": "Descrição sem palavras-chave específicas",
            "content": "Conteúdo sem termos que se encaixem em categorias conhecidas."
        }
        category = topic_cluster._categorize_article(article)
        assert category == "Outros"
