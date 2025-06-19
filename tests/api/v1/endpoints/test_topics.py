"""Tests for the topics endpoints with fixed async mocks."""
import pytest
from unittest.mock import MagicMock, AsyncMock
from fastapi import HTTPException, status, Request
from bson import ObjectId
from datetime import datetime

from app.api.v1.endpoints.topics import get_topic, get_topics
from app.schemas.topics import TopicListResponse, TopicResponse

# Fixtures
@pytest.fixture
def test_topic():
    """Create a test topic."""
    return {
        "_id": ObjectId("507f1f77bcf86cd799439011"),
        "title": "Test Topic",
        "description": "A test topic",
        "country": "BR",
        "category": "health",
        "article_count": 5,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

@pytest.fixture
def mock_request():
    """Create a mock request object."""
    return MagicMock(spec=Request)

# Tests for get_topic
class TestGetTopic:
    """Tests for the GET /topics/{topic_id} endpoint."""
    
    @pytest.mark.asyncio
    async def test_get_topic_success(self, test_topic, mock_request):
        """Test successfully retrieving a topic by ID."""
        # Create a mock collection with async methods
        mock_collection = MagicMock()
        mock_collection.find_one = AsyncMock(return_value=test_topic)
        
        # Create a mock database with proper attribute and item access
        mock_db = MagicMock()
        mock_db.topics = mock_collection  # Direct attribute access
        
        # Act
        response = await get_topic(
            request=mock_request,
            db=mock_db,
            topic_id=str(test_topic["_id"]),
            include_articles=False
        )
        
        # Assert - Check individual fields to avoid issues with ObjectId and datetime
        assert response["_id"] == str(test_topic["_id"])
        assert response["title"] == test_topic["title"]
        assert response["description"] == test_topic["description"]
        assert response["country"] == test_topic["country"]
        assert response["category"] == test_topic["category"]
        assert response["article_count"] == test_topic["article_count"]
        assert response["is_active"] == test_topic["is_active"]
        
        # Verify database calls
        mock_collection.find_one.assert_awaited_once()
    
    @pytest.mark.asyncio
    async def test_get_topic_not_found(self, test_topic, mock_request):
        """Test getting a non-existent topic returns 404."""
        # Create a mock collection with async methods
        mock_collection = MagicMock()
        mock_collection.find_one = AsyncMock(return_value=None)
        
        # Create a mock database with proper attribute access
        mock_db = MagicMock()
        mock_db.topics = mock_collection
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_topic(
                request=mock_request,
                db=mock_db,
                topic_id=str(test_topic["_id"]),
                include_articles=False
            )
        
        # Assert
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in str(exc_info.value.detail).lower()
        
        # Verify database calls
        mock_collection.find_one.assert_awaited_once()

# Tests for list_topics
class TestListTopics:
    """Tests for the GET /topics endpoint."""
    
    @pytest.mark.asyncio
    async def test_list_topics_success(self, test_topic, mock_request):
        """Test successfully listing topics."""
        # Create a mock cursor that supports chaining
        class MockCursor:
            def __init__(self, data):
                self.data = data
                self.sort_call = None
                self.skip_call = None
                self.limit_call = None
                
            def sort(self, *args, **kwargs):
                self.sort_call = (args, kwargs)
                return self
                
            def skip(self, *args, **kwargs):
                self.skip_call = (args, kwargs)
                return self
                
            def limit(self, *args, **kwargs):
                self.limit_call = (args, kwargs)
                return self
                
            async def to_list(self, length=None):
                return self.data
        
        # Create a mock collection with async methods
        mock_collection = MagicMock()
        mock_cursor = MockCursor([test_topic])
        mock_collection.find.return_value = mock_cursor
        mock_collection.count_documents = AsyncMock(return_value=1)
        
        # Create a mock database with proper attribute access
        mock_db = MagicMock()
        mock_db.topics = mock_collection
        
        # Act
        response = await get_topics(
            request=mock_request,
            db=mock_db,
            skip=0,
            limit=10,
            country="BR",
            category=None,
            min_articles=None,
            max_articles=None,
            sort_by="updated_at",
            sort_order="desc"
        )
        
        # Assert
        assert isinstance(response, TopicListResponse)
        assert len(response.data) == 1
        
        # Compare individual fields to avoid issues with datetime objects
        result_topic = response.data[0]
        assert result_topic["_id"] == str(test_topic["_id"])
        assert result_topic["title"] == test_topic["title"]
        assert result_topic["description"] == test_topic["description"]
        assert result_topic["country"] == test_topic["country"]
        assert result_topic["category"] == test_topic["category"]
        assert result_topic["article_count"] == test_topic["article_count"]
        assert result_topic["is_active"] == test_topic["is_active"]
        
        # Check pagination
        assert response.pagination["total"] == 1
        assert response.pagination["skip"] == 0
        assert response.pagination["limit"] == 10
        
        # Verify database calls
        mock_collection.count_documents.assert_awaited_once()
        mock_collection.find.assert_called_once()
        
        # Verify cursor methods were called with expected arguments
        assert mock_cursor.sort_call is not None, "sort() was not called on cursor"
        assert mock_cursor.skip_call == ((0,), {}), f"Expected skip(0), got {mock_cursor.skip_call}"
        assert mock_cursor.limit_call == ((10,), {}), f"Expected limit(10), got {mock_cursor.limit_call}"

# Tests for cluster_topics
# class TestClusterTopics:
#     """Tests for the POST /topics/cluster endpoint."""
    
#     @pytest.mark.asyncio
#     async def test_cluster_topics_success(self, mock_request):
#         """Test successfully triggering topic clustering."""
#         # Arrange
#         background_tasks = MagicMock()
        
#         # Act
#         response = await cluster_topics(
#             request=mock_request,
#             background_tasks=background_tasks,
#             country="BR",
#             force_update=False
#         )
        
#         # Assert
#         assert "message" in response
#         assert "task_id" in response
#         assert response["status"] == "processing"
#         assert response["country"] == "BR"
#         assert "timestamp" in response
        
#         # Verify background task was added
#         background_tasks.add_task.assert_called_once()
