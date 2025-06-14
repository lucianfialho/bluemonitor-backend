"""Tests for the news endpoints."""
import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import status, HTTPException
from fastapi.testclient import TestClient
from bson import ObjectId

# Import the global task manager
from app.services.task_manager import task_manager as global_task_manager
# Import only what we can safely import
from app.api.v1.endpoints.news import _get_news_list, _build_news_query, _format_news_item_light, format_news_item

# Mock the news_collector to avoid import errors
from unittest.mock import MagicMock
import sys

# Create a mock for the news_collector module
mock_collector = MagicMock()
sys.modules['app.services.news.collector'] = mock_collector
mock_collector.news_collector = MagicMock()

# Now import the module under test with the mock in place
from app.api.v1.endpoints.news import router as news_router, collect_news

# Test the GET /news/{news_id} endpoint
class TestGetNews:
    """Tests for the GET /news/{news_id} endpoint."""
    
    async def test_get_news_success(
        self, 
        test_client, 
        test_news,
        db
    ):
        """Test successfully retrieving a news article by ID."""
        # Arrange
        news_id = str(test_news["_id"])
        
        # Act
        response = test_client.get(f"/api/v1/news/{news_id}")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Check the basic structure
        assert "data" in data
        assert "metadata" in data
        assert data["metadata"]["cache_hit"] is False
        
        # Check the news data
        news_data = data["data"]
        assert news_data["id"] == news_id
        assert news_data["title"] == test_news["title"]
        assert news_data["description"] == test_news["description"]
        assert news_data["url"] == test_news["url"]
        assert news_data["source"]["name"] == test_news["source_name"]
        assert news_data["source"]["domain"] == test_news["source_domain"]
        assert news_data["topics"] == test_news["topics"]
        assert news_data["language"] == test_news["language"]
        assert news_data["country"] == test_news["country"]
        
        # Check that related_news is not included by default
        assert "related_news" not in data
        assert "metrics" not in data
        
        # Check that view count was incremented
        updated_news = await db.news.find_one({"_id": test_news["_id"]})
        assert "metrics" in updated_news
        assert updated_news["metrics"].get("views", 0) == 1  # Should be 1 after the view
    
    async def test_get_news_with_related(
        self, 
        test_client, 
        test_news
    ):
        """Test retrieving a news article with related news."""
        # Arrange
        news_id = str(test_news["_id"])
        
        # Act
        response = test_client.get(
            f"/api/v1/news/{news_id}",
            params={"include_related": True}
        )
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Check that related_news is included
        assert "related_news" in data
        assert isinstance(data["related_news"], list)
        
        # Should find at least one related news (the one with the same topic)
        assert len(data["related_news"]) >= 1
        
        # Check the structure of related news items
        for item in data["related_news"]:
            assert "id" in item
            assert "title" in item
            assert "url" in item
            assert "published_at" in item
    
    async def test_get_news_with_metrics(
        self, 
        test_client, 
        test_news
    ):
        """Test retrieving a news article with metrics."""
        # Arrange
        news_id = str(test_news["_id"])
        
        # Act
        response = test_client.get(
            f"/api/v1/news/{news_id}",
            params={"include_metrics": True}
        )
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Check that metrics are included
        assert "metrics" in data
        metrics = data["metrics"]
        
        # Check the metrics data
        assert metrics["views"] == 101  # 100 from fixture + 1 from the first test
        assert metrics["shares"] == 20
        assert metrics["engagement_rate"] == 0.85
        assert metrics["avg_read_time"] == 120
    
    def test_get_nonexistent_news(self, test_client):
        """Test retrieving a news article that doesn't exist."""
        # Arrange
        non_existent_id = str(ObjectId())
        
        # Act
        response = test_client.get(f"/api/v1/news/{non_existent_id}")
        
        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["error"] == "not_found"
        assert non_existent_id in data["message"]
    
    def test_get_news_invalid_id_format(self, test_client):
        """Test retrieving a news article with an invalid ID format."""
        # Arrange
        invalid_id = "not-a-valid-object-id"
        
        # Act
        response = test_client.get(f"/api/v1/news/{invalid_id}")
        
        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert data["error"] == "invalid_id_format"
        assert invalid_id in data["message"]

# Test the GET /news endpoint
class TestListNews:
    """Tests for the GET /news endpoint."""
    
    async def test_list_news_success(self, test_client, test_news):
        """Test successfully listing news articles."""
        # Act
        response = test_client.get("/api/v1/news")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Check the response structure
        assert "data" in data
        assert "pagination" in data
        
        # Check pagination info
        pagination = data["pagination"]
        assert "total" in pagination
        assert "skip" in pagination
        assert "limit" in pagination
        assert "has_more" in pagination
        
        # Should have at least the test news and the related ones we added
        assert pagination["total"] >= 5  # 1 main + 4 related
        assert len(data["data"]) > 0
        
        # Check that the test news is in the results
        news_ids = [item["id"] for item in data["data"]]
        assert str(test_news["_id"]) in news_ids
    
    def test_list_news_with_pagination(self, test_client):
        """Test listing news with pagination parameters."""
        # Act - Get first page
        response = test_client.get(
            "/api/v1/news",
            params={"skip": 0, "limit": 2}
        )
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Should have 2 items per page
        assert len(data["data"]) == 2
        assert data["pagination"]["skip"] == 0
        assert data["pagination"]["limit"] == 2
        
        # Get second page
        response = test_client.get(
            "/api/v1/news",
            params={"skip": 2, "limit": 2}
        )
        
        # Should have more items on the second page
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["data"]) > 0
    
    def test_list_news_with_filters(self, test_client, test_news):
        """Test listing news with various filters."""
        # Test with topic filter
        response = test_client.get(
            "/api/v1/news",
            params={"topic": "test"}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["data"]) > 0
        
        # All returned items should have the topic "test"
        for item in data["data"]:
            assert "test" in item["topics"]
        
        # Test with source filter
        response = test_client.get(
            "/api/v1/news",
            params={"source": "example.com"}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["data"]) > 0
        
        # All returned items should be from the test source
        for item in data["data"][:5]:  # Check first 5 items to avoid too many requests
            assert item["source"]["domain"] == "example.com"
        
        # Test with has_image filter
        response = test_client.get(
            "/api/v1/news",
            params={"has_image": True}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # The test news should be in the results
        news_ids = [item["id"] for item in data["data"]]
        assert str(test_news["_id"]) in news_ids
        
        # All returned items should have an image
        for item in data["data"][:5]:  # Check first 5 items to avoid too many requests
            assert item.get("image") is not None
            assert item["image"].get("url") is not None

# Test the POST /news/collect endpoint
class TestCollectNews:
    """Tests for the POST /news/collect endpoint."""
    
    async def test_collect_news_success(self, test_client, task_manager):
        """Test successfully triggering a news collection."""
        # Arrange
        test_query = "autismo"
        
        # Act
        response = test_client.post(
            "/api/v1/news/collect",
            json={"query": test_query, "country": "BR"}
        )
        
        # Assert
        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        
        # Check the response structure
        assert "message" in data
        assert "status" in data
        assert data["status"] == "processing"
        assert "task_id" in data
        assert "country" in data
        assert data["country"] == "BR"
        assert "timestamp" in data
        
        # Check that a task was created
        task_id = data["task_id"]
        assert task_id in task_manager.tasks
        
        task = task_manager.tasks[task_id]
        assert task["status"] == "processing"
        assert task["metadata"]["query"] == test_query
        assert task["metadata"]["country"] == "BR"
        assert task["metadata"]["source"] == "api"
    
    async def test_collect_news_without_query(self, test_client, task_manager):
        """Test triggering news collection without a query."""
        # Act
        response = test_client.post(
            "/api/v1/news/collect",
            json={"country": "US"}
        )
        
        # Assert
        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        
        # Check the response structure
        assert "message" in data
        assert "status" in data
        assert data["status"] == "processing"
        assert "task_id" in data
        assert data["country"] == "US"
        
        # Check that a task was created
        task_id = data["task_id"]
        assert task_id in task_manager.tasks
        
        task = task_manager.tasks[task_id]
        assert task["status"] == "processing"
        assert "query" not in task["metadata"]  # No query provided
        assert task["metadata"]["country"] == "US"
    
    async def test_collect_news_invalid_country(self, test_client):
        """Test triggering news collection with an invalid country code."""
        # Act
        response = test_client.post(
            "/api/v1/news/collect",
            json={"country": "INVALID"}
        )
        
        # Assert - Should still accept but might log a warning
        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        assert data["country"] == "INVALID"  # The endpoint doesn't validate country codes
    
    async def test_collect_news_with_very_long_query(self, test_client, task_manager):
        """Test triggering news collection with a very long query."""
        # Arrange
        long_query = "a" * 1000  # Very long query string
        
        # Act
        response = test_client.post(
            "/api/v1/news/collect",
            json={"query": long_query, "country": "BR"}
        )
        
        # Assert
        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        
        # Check that a task was created with the full query
        task_id = data["task_id"]
        task = task_manager.tasks[task_id]
        assert task["metadata"]["query"] == long_query
    
    async def test_collect_news_with_special_characters(self, test_client, task_manager):
        """Test triggering news collection with special characters in query."""
        # Arrange
        special_chars_query = "autismo & inclusão @2023 #TEA"
        
        # Act
        response = test_client.post(
            "/api/v1/news/collect",
            json={"query": special_chars_query, "country": "BR"}
        )
        
        # Assert
        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        
        # Check that a task was created with the exact query
        task_id = data["task_id"]
        task = task_manager.tasks[task_id]
        assert task["metadata"]["query"] == special_chars_query
    
    async def test_collect_news_with_empty_query_object(self, test_client, task_manager):
        """Test triggering news collection with an empty query object."""
        # Act
        response = test_client.post(
            "/api/v1/news/collect",
            json={}
        )
        
        # Assert
        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        
        # Should still create a task with default values
        task_id = data["task_id"]
        assert task_id in task_manager.tasks
        
        task = task_manager.tasks[task_id]
        assert task["status"] == "processing"
        assert "query" not in task["metadata"]
        assert task["metadata"]["country"] == "BR"  # Default value from the endpoint
    
    async def test_collect_news_with_null_country(self, test_client, task_manager):
        """Test triggering news collection with null country."""
        # Act
        response = test_client.post(
            "/api/v1/news/collect",
            json={"query": "autismo", "country": None}
        )
        
        # Assert - Should use default country (BR)
        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        assert data["country"] == "BR"
        
        task_id = data["task_id"]
        task = task_manager.tasks[task_id]
        assert task["metadata"]["country"] == "BR"
    
    async def test_collect_news_with_very_long_country(self, test_client, task_manager):
        """Test triggering news collection with a very long country code."""
        # Arrange
        long_country = "A" * 100  # Very long country code
        
        # Act
        response = test_client.post(
            "/api/v1/news/collect",
            json={"query": "autismo", "country": long_country}
        )
        
        # Assert - Should accept but might be truncated by the API
        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        
        # The country in the response might be truncated or modified by the API
        assert len(data["country"]) <= 10  # Assuming a reasonable max length
    
    async def test_collect_news_with_unicode_characters(self, test_client, task_manager):
        """Test triggering news collection with Unicode characters in query."""
        # Arrange
        unicode_query = "autismo e inclusão - 自闭症"  # Chinese characters for autism
        
        # Act
        response = test_client.post(
            "/api/v1/news/collect",
            json={"query": unicode_query, "country": "BR"}
        )
        
        # Assert
        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        
        # Check that a task was created with the exact query
        task_id = data["task_id"]
        task = task_manager.tasks[task_id]
        assert task["metadata"]["query"] == unicode_query
    
    async def test_collect_news_with_whitespace_query(self, test_client, task_manager):
        """Test triggering news collection with a query that's only whitespace."""
        # Arrange
        whitespace_query = "   \t\n  "
        
        # Act
        response = test_client.post(
            "/api/v1/news/collect",
            json={"query": whitespace_query, "country": "BR"}
        )
        
        # Assert - Should be treated as no query provided
        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        
        task_id = data["task_id"]
        task = task_manager.tasks[task_id]
        # The endpoint might normalize the query or treat it as empty
        assert "query" not in task["metadata"] or task["metadata"]["query"].strip() == ""
    
    async def test_collect_news_with_html_in_query(self, test_client, task_manager):
        """Test triggering news collection with HTML in the query."""
        # Arrange
        html_query = "<script>alert('xss')</script> autismo"
        
        # Act
        response = test_client.post(
            "/api/v1/news/collect",
            json={"query": html_query, "country": "BR"}
        )
        
        # Assert - Should be accepted as is (sanitization would happen in the collector)
        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        
        task_id = data["task_id"]
        task = task_manager.tasks[task_id]
        assert task["metadata"]["query"] == html_query
    
    async def test_collect_news_with_invalid_json(self, test_client):
        """Test triggering news collection with invalid JSON."""
        # Act
        response = test_client.post(
            "/api/v1/news/collect",
            content="invalid json",
            headers={"Content-Type": "application/json"}
        )
        
        # Assert - Should return 422 Unprocessable Entity
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert "detail" in data
        assert "json" in data["detail"][0]["loc"]
    
    async def test_collect_news_with_wrong_content_type(self, test_client):
        """Test triggering news collection with wrong content type."""
        # Act
        response = test_client.post(
            "/api/v1/news/collect",
            content='{"query": "autismo"}',
            headers={"Content-Type": "text/plain"}
        )
        
        # Assert - Should return 415 Unsupported Media Type or 422
        assert response.status_code in (status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, status.HTTP_422_UNPROCESSABLE_ENTITY)
    
    async def test_collect_news_with_malformed_country(self, test_client, task_manager):
        """Test triggering news collection with a malformed country code."""
        # Arrange
        malformed_country = "123"  # Not a valid country code
        
        # Act
        response = test_client.post(
            "/api/v1/news/collect",
            json={"query": "autismo", "country": malformed_country}
        )
        
        # Assert - Should still accept but might log a warning
        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        assert data["country"] == malformed_country  # The endpoint doesn't validate country codes
    
    async def test_collect_news_with_very_long_request(self, test_client, task_manager):
        """Test triggering news collection with a very large request body."""
        # Arrange
        large_query = "x" * (10 * 1024)  # 10KB of data
        
        # Act
        response = test_client.post(
            "/api/v1/news/collect",
            json={"query": large_query, "country": "BR"}
        )
        
        # Assert - Should accept very large queries within limits
        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        assert "task_id" in data
    
    async def test_collect_news_with_extra_fields(self, test_client, task_manager):
        """Test triggering news collection with extra fields in the request."""
        # Arrange
        extra_fields = {
            "query": "autismo",
            "country": "BR",
            "extra_field1": "value1",
            "extra_field2": 123,
            "nested": {"key": "value"}
        }
        
        # Act
        response = test_client.post(
            "/api/v1/news/collect",
            json=extra_fields
        )
        
        # Assert - Should accept the request but ignore extra fields
        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        assert data["country"] == "BR"
        
        # Check that the task was created with only the expected fields
        task_id = data["task_id"]
        task = task_manager.tasks[task_id]
        assert task["metadata"]["query"] == "autismo"
        assert task["metadata"]["country"] == "BR"
        assert task["metadata"]["source"] == "api"
        # Extra fields should not be in the task metadata
        assert "extra_field1" not in task["metadata"]
        assert "extra_field2" not in task["metadata"]
        assert "nested" not in task["metadata"]
    
    async def test_collect_news_with_task_manager_error(self, test_client, monkeypatch):
        """Test error handling when task manager fails to create a task."""
        # Arrange
        def mock_create_task(*args, **kwargs):
            raise Exception("Task manager error")
        
        # Patch the task manager's create_task method to raise an exception
        monkeypatch.setattr(global_task_manager, "create_task", mock_create_task)
        
        # Act
        response = test_client.post(
            "/api/v1/news/collect",
            json={"query": "autismo", "country": "BR"}
        )
        
        # Assert - Should return 500 Internal Server Error
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert "error" in data
        assert "internal_server_error" in data["error"]

# Test the news collection process
class TestNewsCollectionProcess:
    """Tests for the news collection process triggered by the collect endpoint."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self, test_client, db):
        """Setup method to clean the database before each test."""
        # Clean up the database
        yield
        # Cleanup is handled by the db fixture
    
    async def test_news_collection_process(self, test_client, db, monkeypatch):
        """Test the complete news collection process."""
        # Mock the news collector to avoid external API calls
        mock_collector = MagicMock()
        mock_collector.process_news_batch.return_value = {
            "total_articles": 5,
            "new_articles": 3,
            "existing_articles": 2,
            "failed_articles": 0,
            "articles": [
                {"title": "Test News 1", "url": "http://example.com/1"},
                {"title": "Test News 2", "url": "http://example.com/2"},
                {"title": "Test News 3", "url": "http://example.com/3"}
            ]
        }
        
        # Patch the news collector
        monkeypatch.setattr("app.api.v1.endpoints.news.news_collector", mock_collector)
        
        # Trigger the collection
        response = test_client.post(
            "/api/v1/news/collect",
            json={"query": "autismo", "country": "BR"}
        )
        
        # Check the initial response
        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        task_id = data["task_id"]
        
        # Wait for the background task to complete
        # In a real test, we'd need to wait for the task to complete
        # For now, we'll just check that the task was created
        assert task_id in global_task_manager.tasks
        
        # The task should be marked as completed
        task = global_task_manager.tasks[task_id]
        assert task["status"] == "completed"
        assert "result" in task
        assert task["result"]["total_articles"] == 5
    
    async def test_news_collection_with_error(self, test_client, monkeypatch):
        """Test news collection when an error occurs during collection."""
        # Mock the news collector to raise an exception
        mock_collector = MagicMock()
        mock_collector.process_news_batch.side_effect = Exception("API Error")
        
        # Patch the news collector
        monkeypatch.setattr("app.api.v1.endpoints.news.news_collector", mock_collector)
        
        # Trigger the collection
        response = test_client.post(
            "/api/v1/news/collect",
            json={"query": "autismo", "country": "BR"}
        )
        
        # Check the initial response
        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        task_id = data["task_id"]
        
        # The task should be marked as failed
        task = global_task_manager.tasks[task_id]
        assert task["status"] == "failed"
        assert "error" in task
        assert "API Error" in str(task["error"])
    
    async def test_news_collection_with_partial_failure(self, test_client, monkeypatch):
        """Test news collection when some articles fail to be processed."""
        # Mock the news collector to simulate partial failure
        mock_collector = MagicMock()
        mock_collector.process_news_batch.return_value = {
            "total_articles": 5,
            "new_articles": 2,
            "existing_articles": 1,
            "failed_articles": 2,
            "articles": [
                {"title": "Test News 1", "url": "http://example.com/1"},
                {"title": "Test News 2", "url": "http://example.com/2"}
            ]
        }
        
        # Patch the news collector
        monkeypatch.setattr("app.api.v1.endpoints.news.news_collector", mock_collector)
        
        # Trigger the collection
        response = test_client.post(
            "/api/v1/news/collect",
            json={"query": "autismo", "country": "BR"}
        )
        
        # Check the initial response
        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        task_id = data["task_id"]
        
        # The task should be marked as completed with partial results
        task = global_task_manager.tasks[task_id]
        assert task["status"] == "completed"
        assert "result" in task
        assert task["result"]["total_articles"] == 5
        assert task["result"]["failed_articles"] == 2

# Test helper functions
class TestHelperFunctions:
    """Tests for helper functions in the news endpoints."""
    
    async def test_format_news_item_light(self, test_client, db):
        """Test the _format_news_item_light helper function."""
        from app.api.v1.endpoints.news import _format_news_item_light
        
        # Create a test news item
        test_item = {
            "_id": ObjectId(),
            "title": "Test News",
            "description": "Test Description",
            "url": "http://example.com/test",
            "source_name": "Test Source",
            "source_domain": "example.com",
            "published_at": datetime.utcnow(),
            "topics": ["test"],
            "language": "en",
            "country": "US",
            "metrics": {
                "views": 10,
                "shares": 2,
                "engagement_rate": 0.5,
                "avg_read_time": 60
            },
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # Format the item
        formatted = _format_news_item_light(test_item)
        
        # Check the formatted output
        assert formatted["id"] == str(test_item["_id"])
        assert formatted["title"] == test_item["title"]
        assert formatted["description"] == test_item["description"]
        assert formatted["url"] == test_item["url"]
        assert formatted["source"]["name"] == test_item["source_name"]
        assert formatted["source"]["domain"] == test_item["source_domain"]
        assert formatted["topics"] == test_item["topics"]
        assert formatted["language"] == test_item["language"]
        assert formatted["country"] == test_item["country"]
        assert "created_at" in formatted
        assert "updated_at" in formatted
        assert "published_at" in formatted
    
    async def test_build_news_query(self, test_client):
        """Test the _build_news_query helper function."""
        from app.api.v1.endpoints.news import _build_news_query
        
        # Test with no filters
        query = _build_news_query()
        assert query == {}
        
        # Test with text search
        query = _build_news_query(q="test query")
        assert "$text" in query
        assert query["$text"]["$search"] == "test query"
        
        # Test with source filter
        query = _build_news_query(source="example.com")
        assert "source_domain" in query
        assert query["source_domain"] == "example.com"
        
        # Test with category filter
        query = _build_news_query(category="health")
        assert "categories" in query
        assert query["categories"] == "health"
        
        # Test with topic filter
        query = _build_news_query(topic_id="507f1f77bcf86cd799439011")
        assert "topics" in query
        assert ObjectId("507f1f77bcf86cd799439011") in query["topics"]
        
        # Test with has_topic filter
        query = _build_news_query(has_topic=True)
        assert "topics" in query
        assert "$exists" in query["topics"]
        assert "$ne" in query["topics"]
        assert query["topics"]["$ne"] == []
        
        # Test with date range
        from_date = datetime(2023, 1, 1)
        to_date = datetime(2023, 12, 31)
        query = _build_news_query(from_date=from_date, to_date=to_date)
        assert "published_at" in query
        assert "$gte" in query["published_at"]
        assert "$lte" in query["published_at"]
        assert query["published_at"]["$gte"] == from_date
        assert query["published_at"]["$lte"] == to_date
        
        # Test with language filter
        query = _build_news_query(language="pt")
        assert "language" in query
        assert query["language"] == "pt"
    
    async def test_get_news_list(self, test_client, db, monkeypatch):
        """Test the _get_news_list helper function."""
        # Create test data
        test_news = [
            {
                "_id": ObjectId(),
                "title": f"Test News {i}",
                "description": f"Test Description {i}",
                "url": f"http://example.com/test/{i}",
                "source_name": "Test Source",
                "source_domain": "example.com",
                "published_at": datetime.utcnow(),
                "topics": ["test"],
                "language": "en",
                "country": "US",
                "metrics": {
                    "views": i * 10,
                    "shares": i * 2,
                    "engagement_rate": 0.5,
                    "avg_read_time": 60
                },
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            for i in range(10)
        ]
        
        # Insert test data
        await db.news.insert_many(test_news)
        
        # Test with no filters
        result = await _get_news_list(db)
        assert "data" in result
        assert "pagination" in result
        assert len(result["data"]) == 10
        assert result["pagination"]["total"] == 10
        assert result["pagination"]["skip"] == 0
        assert result["pagination"]["limit"] == 10  # Default page size
        assert not result["pagination"]["has_more"]
        
        # Test with pagination
        result = await _get_news_list(db, skip=5, limit=3)
        assert len(result["data"]) == 3
        assert result["pagination"]["skip"] == 5
        assert result["pagination"]["limit"] == 3
        assert result["pagination"]["has_more"]  # Should have more items
        
        # Test with sorting
        result = await _get_news_list(db, sort_by="title", sort_order="asc")
        titles = [item["title"] for item in result["data"]]
        assert titles == sorted(titles)  # Should be in ascending order
        
        # Test with text search
        result = await _get_news_list(db, q="Test News 1")
        assert len(result["data"]) >= 1  # At least one item should match
        assert any("Test News 1" in item["title"] for item in result["data"])
        
        # Test with source filter
        result = await _get_news_list(db, source="example.com")
        assert len(result["data"]) == 10  # All items should match
        assert all(item["source"]["domain"] == "example.com" for item in result["data"])
        
        # Test with topic filter
        result = await _get_news_list(db, topic_id=str(test_news[0]["_id"]))
        # The actual filtering by topic would depend on the implementation
        
        # Test with date range
        now = datetime.utcnow()
        yesterday = now - timedelta(days=1)
        tomorrow = now + timedelta(days=1)
        
        # All items should be within this range
        result = await _get_news_list(db, from_date=yesterday, to_date=tomorrow)
        assert len(result["data"]) == 10
        
        # No items should be from the future
        future_date = now + timedelta(days=365)
        result = await _get_news_list(db, from_date=future_date)
        assert len(result["data"]) == 0
        
        # Test with include_content=True
        result = await _get_news_list(db, include_content=True)
        assert all("content" in item for item in result["data"])
    
    async def test_get_news_list_with_empty_database(self, test_client, db):
        """Test _get_news_list with an empty database."""
        # Ensure the collection is empty
        await db.news.delete_many({})
        
        # Test with no filters
        result = await _get_news_list(db)
        assert "data" in result
        assert "pagination" in result
        assert len(result["data"]) == 0
        assert result["pagination"]["total"] == 0
        assert not result["pagination"]["has_more"]
        
        # Test with pagination
        result = await _get_news_list(db, skip=10, limit=5)
        assert len(result["data"]) == 0
        assert result["pagination"]["skip"] == 10
        assert result["pagination"]["limit"] == 5
        assert not result["pagination"]["has_more"]
    
    async def test_get_news_list_with_invalid_parameters(self, test_client, db):
        """Test _get_news_list with invalid parameters."""
        # Test with negative skip
        result = await _get_news_list(db, skip=-1)
        assert result["pagination"]["skip"] == 0  # Should be clamped to 0
        
        # Test with zero limit
        result = await _get_news_list(db, limit=0)
        assert result["pagination"]["limit"] == 1  # Should use minimum limit
        
        # Test with very large limit
        result = await _get_news_list(db, limit=1000)
        assert result["pagination"]["limit"] == 100  # Should use maximum limit
        
        # Test with invalid sort_order
        result = await _get_news_list(db, sort_order="invalid")
        assert result["pagination"]["sort_order"] == "desc"  # Should use default
    
    async def test_format_news_item(self, test_client, db):
        """Test the format_news_item function with various input scenarios."""
        from app.api.v1.endpoints.news import format_news_item
        
        # Create a test news item with all possible fields
        test_item = {
            "_id": ObjectId(),
            "title": "Test News",
            "description": "Test Description",
            "content": "Test Content",
            "url": "http://example.com/test",
            "source_name": "Test Source",
            "source_domain": "example.com",
            "published_at": datetime.utcnow(),
            "topics": ["test", "health"],
            "language": "en",
            "country": "US",
            "authors": ["Author 1", "Author 2"],
            "image_url": "http://example.com/image.jpg",
            "metrics": {
                "views": 100,
                "shares": 20,
                "engagement_rate": 0.85,
                "avg_read_time": 120,
                "last_viewed_at": datetime.utcnow()
            },
            "sentiment": {
                "score": 0.75,
                "label": "positive"
            },
            "keywords": ["test", "news", "health"],
            "entities": [
                {"text": "Test", "type": "ORG"},
                {"text": "Health", "type": "TOPIC"}
            ],
            "metadata": {
                "source_id": "12345",
                "external_id": "ext-123",
                "extracted_at": datetime.utcnow().isoformat()
            },
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # Test with full content
        formatted = format_news_item(test_item, include_full_content=True)
        
        # Check required fields
        assert formatted["id"] == str(test_item["_id"])
        assert formatted["title"] == test_item["title"]
        assert formatted["description"] == test_item["description"]
        assert formatted["content"] == test_item["content"]
        assert formatted["url"] == test_item["url"]
        
        # Check nested objects
        assert formatted["source"]["name"] == test_item["source_name"]
        assert formatted["source"]["domain"] == test_item["source_domain"]
        
        # Check lists
        assert formatted["topics"] == test_item["topics"]
        assert formatted["authors"] == test_item["authors"]
        assert formatted["keywords"] == test_item["keywords"]
        
        # Check nested objects
        assert formatted["sentiment"]["score"] == test_item["sentiment"]["score"]
        assert formatted["sentiment"]["label"] == test_item["sentiment"]["label"]
        
        # Check timestamps
        assert "created_at" in formatted
        assert "updated_at" in formatted
        assert "published_at" in formatted
        
        # Test without full content
        formatted_light = format_news_item(test_item, include_full_content=False)
        assert "content" not in formatted_light  # Content should be excluded
        
        # Test with missing optional fields
        minimal_item = {
            "_id": ObjectId(),
            "title": "Minimal News",
            "url": "http://example.com/minimal",
            "source_name": "Minimal Source",
            "source_domain": "example.com",
            "published_at": datetime.utcnow(),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        formatted_minimal = format_news_item(minimal_item)
        assert formatted_minimal["title"] == "Minimal News"
        assert formatted_minimal["source"]["name"] == "Minimal Source"
        assert "description" not in formatted_minimal  # Not in minimal item
        assert "content" not in formatted_minimal  # Not in minimal item
        
        # Test with None values
        item_with_none = {
            "_id": ObjectId(),
            "title": None,  # Should be required, but test handling
            "url": "http://example.com/none",
            "source_name": "None Test",
            "source_domain": "example.com",
            "published_at": None,  # Should be required, but test handling
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "topics": None,
            "metrics": None,
            "sentiment": None
        }
        
        formatted_none = format_news_item(item_with_none)
        assert formatted_none["title"] is None
        assert formatted_none["published_at"] is None
        assert formatted_none.get("topics") == []  # Should default to empty list
        assert formatted_none.get("metrics") is None
        assert formatted_none.get("sentiment") is None
