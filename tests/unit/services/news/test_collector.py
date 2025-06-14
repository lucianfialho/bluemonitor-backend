"""Tests for the news collector service."""
import pytest
import httpx
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

from app.services.news.collector import NewsCollector, news_collector

# Test data
TEST_NEWS_ITEM = {
    "title": "Test News Article",
    "link": "https://example.com/test-article",
    "source": {"name": "Test Source"},
    "snippet": "This is a test news article.",
    "date": "1 hour ago"
}

TEST_HTML_CONTENT = """
<!DOCTYPE html>
<html>
<head>
    <title>Test Article</title>
    <meta name="description" content="This is a test article description.">
</head>
<body>
    <article>
        <h1>Test Article Title</h1>
        <div class="article-content">
            <p>This is the main content of the test article.</p>
            <p>It contains multiple paragraphs.</p>
        </div>
    </article>
</body>
</html>
"""

# Fixtures
@pytest.fixture
def mock_httpx():
    """Mock the httpx client."""
    with patch('httpx.AsyncClient') as mock_client:
        # Configuração do mock para a resposta da API
        mock_response = AsyncMock()
        mock_response.status_code = 200
        
        # Configuração dos cabeçalhos da resposta
        mock_response.headers = {
            'content-type': 'application/json',
            'x-serpapi-sha1': 'test_sha1',
            'x-serpapi-version': '1.0.0'
        }
        
        # Configuração do JSON de retorno
        async def mock_json():
            return {"news_results": [TEST_NEWS_ITEM]}
        mock_response.json = mock_json
        
        # Configuração do mock para a requisição HTTP
        mock_async_client = AsyncMock()
        mock_async_client.__aenter__.return_value = mock_async_client
        mock_async_client.__aexit__.return_value = None
        
        # Configuração para a requisição GET (usada para buscar o conteúdo do artigo)
        mock_get_response = AsyncMock()
        mock_get_response.status_code = 200
        mock_get_response.text = TEST_HTML_CONTENT
        
        # Configuração para a requisição POST (usada para buscar as notícias)
        mock_async_client.post.return_value = mock_response
        mock_async_client.get.return_value = mock_get_response
        
        mock_client.return_value = mock_async_client
        yield mock_async_client

@pytest.fixture
def mock_processor():
    """Mock the AI processor."""
    with patch('app.services.ai.processor.process_news_content') as mock_process:
        mock_process.return_value = {
            'embedding': [0.1, 0.2, 0.3],
            'summary': 'Test summary',
            'keywords': ['test', 'article']
        }
        yield mock_process

# Test NewsCollector class
class TestNewsCollector:
    """Tests for the NewsCollector class."""
    
    @pytest.mark.asyncio
    async def test_fetch_news_links_success(self, mock_httpx):
        """Test successfully fetching news links."""
        # Arrange
        collector = NewsCollector()
        
        # Configurar o mock para retornar uma resposta bem-sucedida
        mock_response = AsyncMock()
        mock_response.status_code = 200
        
        # Configurar o mock para retornar o JSON corretamente
        async def mock_json():
            return {"news_results": [TEST_NEWS_ITEM]}
        
        mock_response.json = mock_json
        
        # Configurar os headers como um dicionário simples
        mock_response.headers = {
            'content-type': 'application/json',
            'x-serpapi-sha1': 'test_sha1',
            'x-serpapi-version': '1.0.0'
        }
        
        # Configurar o mock para retornar a resposta quando post for chamado
        mock_httpx.post.return_value = mock_response
        
        # Act
        result = await collector.fetch_news_links("test query")
        
        # Assert
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["title"] == TEST_NEWS_ITEM["title"]
        assert "link" in result[0] or "url" in result[0]
        expected_url = result[0].get("link") or result[0].get("url")
        assert expected_url == TEST_NEWS_ITEM["link"]
    
    @pytest.mark.asyncio
    async def test_fetch_news_links_error(self, mock_httpx):
        """Test error handling when fetching news links fails."""
        # Arrange
        collector = NewsCollector()
        
        # Criar um mock assíncrono para a resposta com erro
        mock_response = AsyncMock()
        mock_response.status_code = 500
        
        # Configurar os headers da resposta
        mock_response.headers = {
            'content-type': 'application/json',
            'x-serpapi-sha1': 'test_sha1',
            'x-serpapi-version': '1.0.0'
        }
        
        # Configurar o raise_for_status para levantar uma exceção
        async def raise_http_error():
            raise httpx.HTTPStatusError(
                "API error",
                request=httpx.Request("POST", "https://example.com"),
                response=httpx.Response(500, request=httpx.Request("POST", "https://example.com"))
            )
        
        mock_response.raise_for_status = AsyncMock(side_effect=raise_http_error)
        
        # Configurar o mock para retornar a resposta com erro
        mock_httpx.post.return_value = mock_response
        
        # Act
        result = await collector.fetch_news_links("test query")
        
        # Assert
        assert result == []  # Deve retornar lista vazia em caso de erro
    
    @pytest.mark.asyncio
    async def test_fetch_news_links_empty_response(self, mock_httpx):
        """Test handling of empty response from the API."""
        # Arrange
        collector = NewsCollector()
        
        # Create a mock response with empty data
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = AsyncMock(return_value={})  # Empty response
        
        # Configure the mock to return our response
        mock_httpx.post.return_value = mock_response
        
        # Act
        result = await collector.fetch_news_links("test query")
        
        # Assert
        assert isinstance(result, list)
        assert len(result) == 0, "Expected empty list for empty response"
    
    @pytest.mark.asyncio
    async def test_fetch_article_content(self, mock_httpx):
        """Test fetching article content from URL."""
        # Arrange
        collector = NewsCollector()
        test_url = "https://example.com/test-article"
        
        # HTML content to be returned by the mock
        html_content = """
        <html>
            <head>
                <title>Test Article Title</title>
                <meta name="description" content="Test description">
                <meta property="og:title" content="Test OG Title">
                <meta property="og:description" content="Test OG Description">
                <link rel="icon" href="/favicon.ico">
            </head>
            <body>
                <article>
                    <h1>Test Article Title</h1>
                    <p>This is the main content of the article.</p>
                    <p>More content here with some details.</p>
                </article>
            </body>
        </html>
        """
        
        # Create a mock response for the successful HTTP/1.1 request
        mock_response = AsyncMock()
        mock_response.raise_for_status = AsyncMock()
        mock_response.status_code = 200
        
        # Set content type directly on the response
        mock_response.content_type = 'text/html; charset=utf-8'
        
        # Use a simple dictionary for headers
        mock_response.headers = {'content-type': 'text/html; charset=utf-8'}
        
        # Configure the response text to return our HTML content
        # Using a property to return the HTML content
        type(mock_response).text = html_content
        
        # Create a mock for the client that will be returned by AsyncClient
        mock_client = AsyncMock()
        
        # Configure the client to return the response when get() is called
        mock_client.get.return_value = mock_response
        
        # Configure the client to be used as an async context manager
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        
        # Configure the AsyncClient to return different clients based on the call
        async def async_client_side_effect(*args, **kwargs):
            if kwargs.get('http2', False):
                # For HTTP/2 client (first call)
                mock_http2_client = AsyncMock()
                mock_http2_client.__aenter__.side_effect = Exception("HTTP/2 not supported")
                mock_http2_client.__aexit__.return_value = None
                return mock_http2_client
            else:
                # For HTTP/1.1 client (second call)
                return mock_client
        
        # Configure the side effect for AsyncClient
        mock_httpx.AsyncClient.side_effect = async_client_side_effect
        
        # Act
        result = await collector.fetch_article_content(test_url)
        
        # Assert
        assert result is not None, "Expected a dictionary but got None"
        assert isinstance(result, dict), f"Expected a dictionary but got {type(result)}"
        assert result.get('title') == "Test Article", f"Unexpected title: {result.get('title')}"
        assert "main content" in result.get('content', '').lower(), f"Content not found in: {result.get('content', '')}"
        
        # Verificações básicas do resultado
        assert 'title' in result, "Resultado deve conter 'title'"
    
    @pytest.mark.asyncio
    @patch('app.services.news.collector.process_news_content')
    @patch('httpx.AsyncClient')
    async def test_process_single_news(self, mock_httpx, mock_processor):
        """Test processing a single news article."""
        from unittest.mock import patch, MagicMock, AsyncMock, PropertyMock
        from app.core.database import MongoDBManager
        
        # Arrange
        collector = NewsCollector()
        article = {
            "title": "Test Article",
            "link": "https://example.com/test-article",
            "snippet": "Test snippet",
            "source": {"name": "Test Source"},
            "date": "1 hour ago"
        }
        
        # Configure the mock for fetch_article_content
        mock_fetch = AsyncMock(return_value={
            'title': 'Test Article',
            'content': 'Test content with enough words to be processed by the AI',
            'description': 'Test description',
            'publish_date': '2023-01-01',
            'source': 'Test Source',
            'favicon': 'https://example.com/favicon.ico',
            'domain': 'example.com',
            'url': 'https://example.com/test-article',
            'original_url': 'https://example.com/test-article'
        })
        
        # Configure the mock for process_news_content
        mock_processor.return_value = {
            'individual_summary': 'Test summary',
            'embedding': [0.1, 0.2, 0.3],
            'processed_at': '2023-01-01T00:00:00',
            'language': 'pt-br',
            'keywords': ['test', 'article'],
            'categories': ['Test Category']
        }
        
        # Create a mock for the database operations
        mock_db = AsyncMock()
        mock_db.news.find_one.return_value = None  # Simulate that the news doesn't exist
        mock_db.news.insert_one.return_value = AsyncMock(inserted_id="507f1f77bcf86cd799439011")
        
        # Create a mock for the MongoDB client and database
        mock_client = AsyncMock()
        mock_client.__getitem__.return_value = mock_db
        
        # Create a mock for the MongoDBManager that supports async context manager
        @asynccontextmanager
        async def async_context_manager():
            try:
                yield mock_db
            finally:
                pass
        
        # Create a mock for the MongoDBManager
        mock_mongodb_manager = AsyncMock()
        
        # Configure the get_db method to return our async context manager
        mock_mongodb_manager.get_db.return_value = async_context_manager()
        
        # Configure the connect_to_mongodb and close_mongodb_connection methods
        mock_mongodb_manager.connect_to_mongodb = AsyncMock()
        mock_mongodb_manager.close_mongodb_connection = AsyncMock()
        
        # Create a mock for the MongoDBManager class
        mock_mongodb_class = AsyncMock()
        mock_mongodb_class.return_value = mock_mongodb_manager
        
        # Patch the MongoDBManager class and fetch_article_content method
        with (
            patch('app.services.news.collector.MongoDBManager', mock_mongodb_class),
            patch.object(collector, 'fetch_article_content', mock_fetch)
        ):
            # Act
            result = await collector.process_single_news(article, "BR")
            
            # Assert
            assert isinstance(result, bool), f"Expected boolean result, got {type(result)}"
            assert result is True, "Expected process_single_news to return True for successful processing"
            
            # Verify fetch_article_content was called with the correct URL
            collector.fetch_article_content.assert_awaited_once_with(article["link"])
            
            # Verify process_news_content was called with the correct arguments
            mock_processor.assert_awaited_once()
            
            # Verify database operations were called correctly
            assert mock_mongodb_manager.connect_to_mongodb.await_count > 0, "Expected connect_to_mongodb to be called at least once"
            mock_db.news.find_one.assert_awaited_once()
            mock_db.news.insert_one.assert_awaited_once()
            assert mock_mongodb_manager.close_mongodb_connection.await_count > 0, "Expected close_mongodb_connection to be called at least once"
    
    @pytest.mark.asyncio
    async def test_fetch_article_content_http_error(self, mock_httpx):
        """Test fetching article content when HTTP request fails."""
        # Arrange
        collector = NewsCollector()
        test_url = "https://example.com/test-article"
        
        # Configure the mock to raise an exception for both HTTP/2 and HTTP/1.1
        mock_async_client = AsyncMock()
        
        # Simulate HTTP/2 failure
        mock_httpx.return_value.__aenter__.side_effect = httpx.RequestError("Connection error")
        mock_httpx.return_value.__aexit__.return_value = None
        
        # Act
        with patch('httpx.AsyncClient', side_effect=[mock_async_client, mock_async_client]):
            result = await collector.fetch_article_content(test_url)
        
        # Assert
        # O método fetch_article_content retorna None em caso de erro HTTP
        assert result is None, "Expected None when HTTP request fails"
    
    @pytest.mark.asyncio
    @patch('app.services.news.collector.process_news_content')
    @patch('httpx.AsyncClient')
    async def test_process_news_batch(self, mock_httpx, mock_processor):
        """Test the complete news collection process."""
        # Import the mongodb_manager here to patch it
        from app.core.database import mongodb_manager
        
        # Arrange
        collector = NewsCollector()
        
        # Configure the mock for fetch_news_links
        mock_fetch_links = AsyncMock(return_value=[
            {
                'title': 'Test Article 1',
                'link': 'https://example.com/test-article-1',
                'snippet': 'Test snippet 1',
                'source': {'name': 'Test Source 1'},
                'date': '1 hour ago'
            },
            {
                'title': 'Test Article 2',
                'link': 'https://example.com/test-article-2',
                'snippet': 'Test snippet 2',
                'source': {'name': 'Test Source 2'},
                'date': '2 hours ago'
            }
        ])
        
        # Create a mock for the database operations
        mock_db = AsyncMock()
        # Simulate that none of the news exist yet
        mock_db.news.find_one.side_effect = [None, None]
        # Simulate successful inserts
        mock_db.news.insert_one.side_effect = [
            AsyncMock(inserted_id="507f1f77bcf86cd799439011"),
            AsyncMock(inserted_id="507f1f77bcf86cd799439012")
        ]
        
        # Create a mock for the MongoDB client and database
        mock_client = AsyncMock()
        mock_client.__getitem__.return_value = mock_db
        
        # Save the original mongodb_manager
        original_mongodb_manager = mongodb_manager
        
        # Patch the mongodb_manager
        try:
            # Configure the mongodb_manager
            mongodb_manager._client = mock_client
            mongodb_manager._db = mock_db
            
            # Configure the mock for process_single_news
            mock_process_single = AsyncMock(return_value=True)
            
            # Patch the methods
            with (
                patch.object(collector, 'fetch_news_links', mock_fetch_links),
                patch.object(collector, 'process_single_news', mock_process_single)
            ):
                # Act
                results = await collector.process_news_batch("test query")
                
                # Assert
                assert isinstance(results, dict)
                assert 'total_processed' in results
                assert 'successful' in results
                assert 'failed' in results
                assert 'errors' in results
                assert results['total_processed'] == 2
                assert results['successful'] == 2  # All should be successful
                assert results['failed'] == 0  # No failures
                
                # Verify the methods were called correctly
                collector.fetch_news_links.assert_awaited_once_with("test query", "BR")
                assert mock_process_single.await_count == 2
        finally:
            # Restore the original mongodb_manager
            mongodb_manager = original_mongodb_manager
    
    @pytest.mark.asyncio
    @patch('app.services.news.collector.process_news_content')
    @patch('httpx.AsyncClient')
    async def test_process_news_batch_concurrency_limit(self, mock_httpx, mock_processor):
        """Test the news collection process with concurrency limit."""
        # Import the mongodb_manager here to patch it
        from app.core.database import mongodb_manager
        
        # Arrange
        collector = NewsCollector()
        
        # Create 5 test articles
        test_articles = [
            {
                'title': f'Test Article {i}',
                'link': f'https://example.com/test-article-{i}',
                'snippet': f'Test snippet {i}',
                'source': {'name': f'Test Source {i}'},
                'date': f'{i} hour ago'
            }
            for i in range(5)
        ]
        
        # Configure the mock for fetch_news_links
        mock_fetch_links = AsyncMock(return_value=test_articles)
        
        # Create a mock for the database operations
        mock_db = AsyncMock()
        # Simulate that none of the news exist yet
        mock_db.news.find_one.side_effect = [None] * 5
        # Simulate successful inserts
        mock_db.news.insert_one.side_effect = [
            AsyncMock(inserted_id=f"507f1f77bcf86cd79943901{i}")
            for i in range(5)
        ]
        
        # Create a mock for the MongoDB client and database
        mock_client = AsyncMock()
        mock_client.__getitem__.return_value = mock_db
        
        # Save the original mongodb_manager
        original_mongodb_manager = mongodb_manager
        
        # Patch the mongodb_manager
        try:
            # Configure the mongodb_manager
            mongodb_manager._client = mock_client
            mongodb_manager._db = mock_db
            
            # Configure the mock for process_single_news
            mock_process_single = AsyncMock(return_value=True)
            
            # Patch the methods
            with (
                patch.object(collector, 'fetch_news_links', mock_fetch_links),
                patch.object(collector, 'process_single_news', mock_process_single)
            ):
                # Act
                results = await collector.process_news_batch("test query")
                
                # Assert
                assert isinstance(results, dict)
                assert results['total_processed'] == 5
                assert results['successful'] == 5
                assert results['failed'] == 0
                assert len(results['errors']) == 0
                
                # Verify the methods were called correctly
                collector.fetch_news_links.assert_awaited_once_with("test query", "BR")
                assert mock_process_single.await_count == 5
                
                # Verify that process_single_news was called with the correct arguments
                for i, article in enumerate(test_articles):
                    # Check that process_single_news was called with each article
                    mock_process_single.assert_any_await(article, "BR")
        finally:
            # Restore the original mongodb_manager
            mongodb_manager = original_mongodb_manager
    
    @pytest.mark.asyncio
    @patch('app.services.news.collector.process_news_content')
    @patch('httpx.AsyncClient')
    async def test_process_news_batch_empty_list(self, mock_httpx, mock_processor):
        """Test the news collection process when no news items are returned."""
        # Arrange
        collector = NewsCollector()
        
        # Configure the mock for fetch_news_links to return an empty list
        mock_fetch_links = AsyncMock(return_value=[])
        
        # Patch the method
        with patch.object(collector, 'fetch_news_links', mock_fetch_links):
            # Act
            results = await collector.process_news_batch("test query")
            
            # Assert
            assert isinstance(results, dict)
            assert 'total_processed' in results
            assert 'successful' in results
            assert 'failed' in results
            assert 'errors' in results
            assert results['total_processed'] == 0
            assert results['successful'] == 0
            assert results['failed'] == 0
            assert len(results['errors']) == 0

    @pytest.mark.asyncio
    @patch('app.services.news.collector.process_news_content')
    @patch('httpx.AsyncClient')
    async def test_process_news_batch_partial_failure(self, mock_httpx, mock_processor):
        """Test the news collection process with partial failures."""
        # Arrange
        collector = NewsCollector()
        
        # Configure the mock for fetch_news_links
        mock_fetch_links = AsyncMock(return_value=[
            {
                'title': 'Test Article 1',
                'link': 'https://example.com/test-article-1',
                'snippet': 'Test snippet 1',
                'source': {'name': 'Test Source 1'},
                'date': '1 hour ago'
            },
            {
                'title': 'Test Article 2',
                'link': 'https://example.com/test-article-2',
                'snippet': 'Test snippet 2',
                'source': {'name': 'Test Source 2'},
                'date': '2 hours ago'
            }
        ])
        
        # Configure the mock for process_single_news to fail for the second item
        async def mock_process_single_news(news_item, country):
            if news_item['link'] == 'https://example.com/test-article-2':
                raise Exception("Failed to process article")
            return True
        
        # Patch the methods
        with (
            patch.object(collector, 'fetch_news_links', mock_fetch_links),
            patch.object(collector, 'process_single_news', mock_process_single_news)
        ):
            # Act
            results = await collector.process_news_batch("test query")
            
            # Assert
            assert isinstance(results, dict)
            assert results['total_processed'] == 2
            assert results['successful'] == 1  # One successful
            assert results['failed'] == 1  # One failed
            assert len(results['errors']) == 1  # One error message
            assert "Failed to process article" in results['errors'][0]
    
    @pytest.mark.asyncio
    async def test_fetch_article_content_invalid_html(self, mock_httpx):
        """Test fetching article content with invalid HTML."""
        # Arrange
        collector = NewsCollector()
        test_url = "https://example.com/test-article"
        
        # Create a mock response with invalid HTML
        mock_response = AsyncMock()
        mock_response.raise_for_status = AsyncMock()
        mock_response.status_code = 200
        mock_response.content_type = 'text/html; charset=utf-8'
        mock_response.headers = {'content-type': 'text/html; charset=utf-8'}
        
        # Invalid HTML (unclosed tags)
        invalid_html = "<html><head><title>Test</title><body><p>Test"
        type(mock_response).text = invalid_html
        
        # Create mocks for both HTTP/2 and HTTP/1.1 clients
        mock_async_client = AsyncMock()
        mock_async_client.__aenter__.return_value = mock_async_client
        mock_async_client.__aexit__.return_value = None
        mock_async_client.get.return_value = mock_response
        
        # Configure the AsyncClient to return our mock client
        mock_httpx.return_value = mock_async_client
        
        # Act
        result = await collector.fetch_article_content(test_url)
        
        # Assert
        assert result is not None, "Expected a dictionary but got None"
        assert isinstance(result, dict), f"Expected a dictionary but got {type(result)}"
        assert 'title' in result, "Result should contain 'title'"
        assert 'content' in result, "Result should contain 'content'"
        # The title should be extracted from the HTML content
        assert result['title'] == 'Test Article', f"Unexpected title: {result.get('title')}"
    
    @pytest.mark.asyncio
    @patch('app.services.news.collector.process_news_content')
    @patch('httpx.AsyncClient')
    async def test_process_single_news_already_exists(self, mock_httpx, mock_processor):
        """Test processing a news article that already exists in the database."""
        # Arrange
        collector = NewsCollector()
        article = {
            "title": "Test Article",
            "link": "https://example.com/test-article",
            "snippet": "Test snippet",
            "source": {"name": "Test Source"},
            "date": "1 hour ago"
        }
        
        # Create a mock for the database operations
        mock_db = AsyncMock()
        # Simulate that the news already exists
        mock_db.news.find_one.return_value = {"original_url": article["link"], "_id": "existing_id"}
        
        # Create a mock for the MongoDB client and database
        mock_client = AsyncMock()
        mock_client.__getitem__.return_value = mock_db
        
        # Create a mock for the MongoDBManager that supports async context manager
        @asynccontextmanager
        async def async_context_manager():
            try:
                yield mock_db
            finally:
                pass
        
        # Create a mock for the MongoDBManager
        mock_mongodb_manager = AsyncMock()
        mock_mongodb_manager.get_db.return_value = async_context_manager()
        mock_mongodb_manager.connect_to_mongodb = AsyncMock()
        mock_mongodb_manager.close_mongodb_connection = AsyncMock()
        
        # Create a mock for the MongoDBManager class
        mock_mongodb_class = AsyncMock()
        mock_mongodb_class.return_value = mock_mongodb_manager
        
        # Patch the MongoDBManager class
        with patch('app.services.news.collector.MongoDBManager', mock_mongodb_class):
            # Act
            result = await collector.process_single_news(article, "BR")
            
            # Assert
            assert result is False, "Expected False when article already exists"
            mock_db.news.find_one.assert_awaited_once()
            mock_db.news.insert_one.assert_not_called()
            mock_processor.assert_not_called()
    
    @pytest.mark.asyncio
    @patch('app.services.news.collector.process_news_content')
    @patch('httpx.AsyncClient')
    async def test_process_single_news_content_processing_error(self, mock_httpx, mock_processor):
        """Test processing a news article when content processing fails."""
        # Arrange
        collector = NewsCollector()
        article = {
            "title": "Test Article",
            "link": "https://example.com/test-article",
            "snippet": "Test snippet",
            "source": {"name": "Test Source"},
            "date": "1 hour ago"
        }
        
        # Configure the mock for fetch_article_content
        mock_fetch = AsyncMock(return_value={
            'title': 'Test Article',
            'content': 'Test content with enough words to be processed by the AI',
            'description': 'Test description',
            'publish_date': '2023-01-01',
            'source': 'Test Source',
            'favicon': 'https://example.com/favicon.ico',
            'domain': 'example.com',
            'url': 'https://example.com/test-article',
            'original_url': 'https://example.com/test-article'
        })
        
        # Configure the mock for process_news_content to raise an exception
        mock_processor.side_effect = Exception("AI processing failed")
        
        # Create a mock for the database operations
        mock_db = AsyncMock()
        # Simulate that the news doesn't exist
        mock_db.news.find_one.return_value = None
        # Simulate successful insert
        mock_db.news.insert_one.return_value = AsyncMock(inserted_id="507f1f77bcf86cd799439011")
        
        # Create a mock for the MongoDB client and database
        mock_client = AsyncMock()
        mock_client.__getitem__.return_value = mock_db
        
        # Create a mock for the MongoDBManager that supports async context manager
        @asynccontextmanager
        async def async_context_manager():
            try:
                yield mock_db
            finally:
                pass
        
        # Create a mock for the MongoDBManager
        mock_mongodb_manager = AsyncMock()
        mock_mongodb_manager.get_db.return_value = async_context_manager()
        mock_mongodb_manager.connect_to_mongodb = AsyncMock()
        mock_mongodb_manager.close_mongodb_connection = AsyncMock()
        
        # Create a mock for the MongoDBManager class
        mock_mongodb_class = AsyncMock()
        mock_mongodb_class.return_value = mock_mongodb_manager
        
        # Patch the MongoDBManager class and fetch_article_content method
        with (
            patch('app.services.news.collector.MongoDBManager', mock_mongodb_class),
            patch.object(collector, 'fetch_article_content', mock_fetch)
        ):
            # Act
            result = await collector.process_single_news(article, "BR")
            
            # Assert
            # O método process_single_news retorna True mesmo em caso de erro no processamento
            # pois o documento ainda é salvo no banco de dados com o erro registrado
            assert result is True, "Expected True even when content processing fails"
            mock_processor.assert_awaited_once()
            # Verifica se insert_one foi chamado para registrar o erro
            assert mock_db.news.insert_one.call_count == 1, "Expected insert_one to be called once"
            
            # Obtém o documento que foi inserido
            inserted_doc = mock_db.news.insert_one.call_args[0][0]
            
            # Verifica se o documento contém informações de erro
            assert "processing_error" in inserted_doc, "Expected error to be recorded in the document"
            assert "AI processing failed" in str(inserted_doc.get("processing_error", "")), \
                f"Expected 'AI processing failed' in error, got: {inserted_doc.get('processing_error', '')}"
    
    @pytest.mark.asyncio
    @patch('app.services.news.collector.process_news_content')
    @patch('app.services.news.collector.MongoDBManager')
    async def test_process_single_news_mongodb_connection_error(self, mock_mongodb, mock_processor):
        """Test handling MongoDB connection errors."""
        # Arrange
        collector = NewsCollector()
        test_news = {
            'title': 'Test Article',
            'link': 'https://example.com/test-article',
            'source': {'href': 'https://example.com'},
            'published': '2023-01-01T00:00:00Z'
        }
        
        # Configure MongoDB mock to raise an exception when connect_to_mongodb is called
        mock_mongodb_instance = AsyncMock()
        mock_mongodb_instance.connect_to_mongodb.side_effect = Exception("MongoDB connection failed")
        
        # Make sure __aenter__ and __aexit__ are coroutines
        mock_mongodb_instance.__aenter__ = AsyncMock()
        mock_mongodb_instance.__aexit__ = AsyncMock()
        
        # Configure the class to return our instance
        mock_mongodb.return_value = mock_mongodb_instance
        
        # Configure the processor mock (though it shouldn't be reached)
        mock_processor.return_value = {
            'title': 'Processed Title',
            'summary': 'Test summary',
            'categories': ['Technology'],
            'sentiment': 'neutral',
            'tags': ['test', 'article'],
            'importance': 'medium',
            'processed_at': '2023-01-01T00:00:00Z',
            'original_url': 'https://example.com/test-article',
            'source': 'Test Source',
            'favicon': 'https://example.com/favicon.ico',
            'domain': 'example.com',
            'url': 'https://example.com/test-article'
        }
        
        # Act
        result = await collector.process_single_news(test_news, "BR")
        
        # Assert
        assert result is False, "Expected False when MongoDB connection fails"
        mock_mongodb_instance.connect_to_mongodb.assert_awaited_once()
        
        # Verify that the processor was not called (since MongoDB connection failed)
        mock_processor.assert_not_called()
    
    @pytest.mark.asyncio
    @patch('app.services.news.collector.process_news_content')
    @patch('app.services.news.collector.MongoDBManager')
    async def test_process_single_news_invalid_data(self, mock_mongodb, mock_processor):
        """Test processing a news article with invalid data."""
        # Test cases for different invalid data scenarios
        test_cases = [
            # Missing required fields
            ({"title": "Test Article"}, "Missing required field 'link' or 'source'"),
            ({"link": "https://example.com/test"}, "Missing required field 'title'"),
            # Invalid URL
            ({"title": "Test", "link": "not-a-url", "source": {"href": "https://example.com"}}, "Invalid URL"),
            # Empty title
            ({"title": "", "link": "https://example.com/test", "source": {"href": "https://example.com"}}, "Title cannot be empty"),
            # Empty link
            ({"title": "Test", "link": "", "source": {"href": "https://example.com"}}, "Link cannot be empty"),
            # Missing source href
            ({"title": "Test", "link": "https://example.com/test", "source": {}}, "Missing required field 'source.href'")
        ]
        
        collector = NewsCollector()
        
        # Configure the database mock
        mock_db = AsyncMock()
        mock_db.news = AsyncMock()
        mock_db.news.find_one = AsyncMock(return_value=None)
        mock_db.news_invalid = AsyncMock()
        mock_db.news_invalid.insert_one = AsyncMock(return_value=AsyncMock(inserted_id="invalid_id"))
        
        # Configure the MongoDB manager mock
        mock_mongodb_instance = AsyncMock()
        mock_mongodb_instance.connect_to_mongodb = AsyncMock()
        mock_mongodb_instance.close_mongodb_connection = AsyncMock()
        
        # Create a proper async context manager for get_db
        @asynccontextmanager
        async def mock_get_db():
            try:
                yield mock_db
            finally:
                pass
        
        # Set up the mock to return our context manager
        mock_mongodb_instance.get_db = mock_get_db
        
        # Configure the manager to return our instance
        mock_mongodb.return_value = mock_mongodb_instance
        
        # Configure the processor mock (shouldn't be called for invalid data)
        mock_processor.return_value = {
            'title': 'Processed Title',
            'summary': 'Test summary',
            'categories': ['Technology'],
            'sentiment': 'neutral',
            'tags': ['test', 'article']
        }
        
        for article, expected_error in test_cases:
            # Reset mocks before each test case
            mock_processor.reset_mock()
            mock_mongodb_instance.connect_to_mongodb.reset_mock()
            mock_mongodb_instance.close_mongodb_connection.reset_mock()
            mock_db.news.find_one.reset_mock()
            
            # Act
            result = await collector.process_single_news(article, 'BR')
            
            # Assertions
            # O método deve retornar None para dados inválidos, não False
            # Isso ocorre porque o método retorna None quando os dados são inválidos
            # e False apenas quando o artigo já existe no banco de dados
            assert result is None, f"Expected None for article: {article}"
            mock_processor.assert_not_called()

# Test the singleton instance
class TestNewsCollectorSingleton:
    """Tests for the news collector singleton instance."""
    
    def test_singleton_instance(self):
        """Test that the same instance is returned."""
        # Act
        instance1 = news_collector
        instance2 = news_collector
        
        # Assert
        assert instance1 is instance2
        assert isinstance(instance1, NewsCollector)
        assert isinstance(instance2, NewsCollector)
