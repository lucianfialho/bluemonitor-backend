"""Tests for the AI processor service."""
import pytest
import numpy as np
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime

from app.services.ai.processor import AIProcessor, ai_processor

# Test data
TEST_CONTENT = """
O autismo, ou Transtorno do Espectro Autista (TEA), é uma condição neurológica 
que afeta o desenvolvimento e se manifesta principalmente nas áreas de comunicação, 
interação social e comportamento. No Brasil, estima-se que haja cerca de 2 milhões 
de pessoas com autismo. A conscientização sobre o tema tem crescido nos últimos anos, 
mas ainda há muitos desafios a serem superados.
"""

# Fixtures
@pytest.fixture
def mock_models():
    """Mock the AI models."""
    with patch('sentence_transformers.SentenceTransformer') as mock_embedding, \
         patch('transformers.pipeline') as mock_pipeline:
        
        # Mock embedding model
        mock_embedding.return_value.encode.return_value = np.random.rand(384)
        
        # Mock summarization pipeline
        mock_pipeline.return_value = lambda x, **kwargs: [{
            'summary_text': 'Resumo gerado automaticamente sobre autismo.'
        }]
        
        yield mock_embedding, mock_pipeline

# Test AIProcessor class
class TestAIProcessor:
    """Tests for the AIProcessor class."""
    
    @pytest.mark.asyncio
    async def test_load_models(self, mock_models):
        """Test loading AI models."""
        # Arrange
        processor = AIProcessor()
        
        # Act
        await processor.load_models()
        
        # Assert
        assert processor._models_loaded is True
        assert processor.embedding_model is not None
        assert processor.summarizer is not None
    
    @pytest.mark.asyncio
    async def test_generate_embedding(self, mock_models):
        """Test generating text embeddings."""
        # Arrange
        processor = AIProcessor()
        await processor.load_models()
        
        # Act
        embedding = await processor.generate_embedding("Test content")
        
        # Assert
        assert isinstance(embedding, np.ndarray)
        assert embedding.shape == (384,)
    
    @pytest.mark.asyncio
    async def test_summarize_text(self, mock_models):
        """Test summarizing text."""
        # Arrange
        processor = AIProcessor()
        await processor.load_models()
        
        # Act
        summary = await processor.summarize_text(TEST_CONTENT)
        
        # Assert
        assert isinstance(summary, str)
        assert len(summary) > 0
        assert "resumo" in summary.lower() or "autismo" in summary.lower()
    
    @pytest.mark.asyncio
    async def test_extract_keywords(self):
        """Test extracting keywords from text."""
        # Arrange
        processor = AIProcessor()
        
        # Act
        keywords = await processor.extract_keywords(TEST_CONTENT, top_n=3)
        
        # Assert
        assert isinstance(keywords, list)
        assert len(keywords) == 3
        assert all(isinstance(kw, str) for kw in keywords)
    
    @pytest.mark.asyncio
    async def test_calculate_similarity(self):
        """Test calculating similarity between texts."""
        # Arrange
        processor = AIProcessor()
        text1 = "Autismo é um transtorno do desenvolvimento"
        text2 = "O autismo afeta a comunicação e interação social"
        
        # Act
        similarity = await processor.calculate_similarity(text1, text2)
        
        # Assert
        assert isinstance(similarity, float)
        assert 0 <= similarity <= 1  # Similarity should be between 0 and 1

# Test the singleton instance
class TestAIProcessorSingleton:
    """Tests for the AI processor singleton instance."""
    
    @pytest.mark.asyncio
    async def test_singleton_instance(self, mock_models):
        """Test that the same instance is returned."""
        # Act
        instance1 = ai_processor
        instance2 = ai_processor
        
        # Assert
        assert instance1 is instance2
        assert isinstance(instance1, AIProcessor)
        assert isinstance(instance2, AIProcessor)

# Test the process_news_content helper function
class TestProcessNewsContent:
    """Tests for the process_news_content helper function."""
    
    @pytest.mark.asyncio
    async def test_process_news_content(self, mock_models):
        """Test processing news content."""
        # Arrange
        from app.services.ai.processor import process_news_content
        
        # Act
        result = await process_news_content(TEST_CONTENT)
        
        # Assert
        assert isinstance(result, dict)
        assert 'embedding' in result
        assert 'summary' in result
        assert 'keywords' in result
        assert isinstance(result['embedding'], np.ndarray)
        assert isinstance(result['summary'], str)
        assert isinstance(result['keywords'], list)
        assert len(result['keywords']) > 0
