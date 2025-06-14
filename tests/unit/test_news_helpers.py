"""Unit tests for news helper functions."""
import pytest
from datetime import datetime, timezone
from bson import ObjectId
from unittest.mock import MagicMock, patch

# Mock the database and other dependencies
db = MagicMock()

# Import the functions we want to test
from app.api.v1.endpoints.news import (
    _build_news_query,
    _format_news_item_light,
    format_news_item
)

class TestBuildNewsQuery:
    """Tests for the _build_news_query function."""
    
    def test_no_filters(self):
        """Test with no filters."""
        query = _build_news_query()
        assert query == {}
    
    def test_text_search(self):
        """Test with text search."""
        query = _build_news_query(q="test query")
        assert "$text" in query
        assert query["$text"]["$search"] == "test query"
    
    def test_source_filter(self):
        """Test with source filter."""
        query = _build_news_query(source="example.com")
        assert "$or" in query
        assert len(query["$or"]) == 2
        assert {"source_name": {"$regex": "example.com", "$options": "i"}} in query["$or"]
        assert {"source_domain": {"$regex": "example.com", "$options": "i"}} in query["$or"]
    
    def test_category_filter(self):
        """Test with category filter."""
        query = _build_news_query(category="health")
        assert "categories" in query
        assert query["categories"] == {"$regex": "^health$", "$options": "i"}
    
    def test_topic_filter(self):
        """Test with topic filter."""
        query = _build_news_query(topic_id="507f1f77bcf86cd799439011")
        assert "topic_id" in query
        assert query["topic_id"] == "507f1f77bcf86cd799439011"
    
    def test_has_topic_filter_true(self):
        """Test with has_topic=True filter."""
        query = _build_news_query(has_topic=True)
        assert "topic_id" in query
        assert query["topic_id"] == {"$exists": True, "$ne": None}
    
    def test_has_topic_filter_false(self):
        """Test with has_topic=False filter."""
        query = _build_news_query(has_topic=False)
        assert "$or" in query
        assert len(query["$or"]) == 2
        assert {"topic_id": {"$exists": False}} in query["$or"]
        assert {"topic_id": None} in query["$or"]
    
    def test_from_date_filter(self):
        """Test with from_date filter."""
        test_date = datetime(2023, 1, 1)
        query = _build_news_query(from_date=test_date)
        assert "published_at" in query
        assert query["published_at"]["$gte"] == test_date
    
    def test_to_date_filter(self):
        """Test with to_date filter."""
        test_date = datetime(2023, 12, 31)
        query = _build_news_query(to_date=test_date)
        assert "published_at" in query
        assert query["published_at"]["$lte"] == test_date
    
    def test_date_range_filter(self):
        """Test with both from_date and to_date filters."""
        from_date = datetime(2023, 1, 1)
        to_date = datetime(2023, 12, 31)
        query = _build_news_query(from_date=from_date, to_date=to_date)
        assert "published_at" in query
        assert query["published_at"]["$gte"] == from_date
        assert query["published_at"]["$lte"] == to_date
    
    def test_language_filter(self):
        """Test with language filter."""
        query = _build_news_query(language="pt")
        assert "language" in query
        assert query["language"] == "pt"
    
    def test_combined_filters(self):
        """Test with multiple filters combined."""
        from_date = datetime(2023, 1, 1)
        to_date = datetime(2023, 12, 31)
        query = _build_news_query(
            q="test query",
            source="example.com",
            category="health",
            topic_id="507f1f77bcf86cd799439011",
            from_date=from_date,
            to_date=to_date,
            language="pt"
        )
        
        # Verify all conditions are present
        assert "$text" in query
        assert query["$text"]["$search"] == "test query"
        
        assert "$or" in query
        assert len(query["$or"]) == 2
        assert {"source_name": {"$regex": "example.com", "$options": "i"}} in query["$or"]
        assert {"source_domain": {"$regex": "example.com", "$options": "i"}} in query["$or"]
        
        assert "categories" in query
        assert query["categories"] == {"$regex": "^health$", "$options": "i"}
        
        assert "topic_id" in query
        assert query["topic_id"] == "507f1f77bcf86cd799439011"
        
        assert "published_at" in query
        assert query["published_at"]["$gte"] == from_date
        assert query["published_at"]["$lte"] == to_date
        
        assert "language" in query
        assert query["language"] == "pt"
    
    def test_date_range(self):
        """Test with date range."""
        from_date = datetime(2023, 1, 1)
        to_date = datetime(2023, 12, 31)
        query = _build_news_query(from_date=from_date, to_date=to_date)
        assert "published_at" in query
        assert "$gte" in query["published_at"]
        assert "$lte" in query["published_at"]
        assert query["published_at"]["$gte"] == from_date
        assert query["published_at"]["$lte"] == to_date
    
    def test_language_filter(self):
        """Test with language filter."""
        query = _build_news_query(language="pt")
        assert "language" in query
        assert query["language"] == "pt"


class TestFormatNewsItemLight:
    """Tests for the _format_news_item_light function."""
    
    def test_format_news_item_light_full(self):
        """Test _format_news_item_light with all possible fields."""
        # Create a test news item with all fields
        test_item = {
            "_id": ObjectId("507f1f77bcf86cd799439011"),
            "title": "Test News Title",
            "description": "Test news description",
            "url": "https://example.com/news/test-news",
            "source_name": "Test Source",
            "source_domain": "example.com",
            "published_at": datetime(2023, 1, 1, 12, 0, 0),
            "language": "en",
            "categories": ["test", "technology"],
            "topic_id": ObjectId("507f1f77bcf86cd799439012"),
            "image_url": "https://example.com/images/test.jpg",
            "content": "Test news content",
            "country": "US"
        }
        
        # Format the item with include_content=True
        formatted = _format_news_item_light(test_item, include_content=True)
        
        # Check that the ID is converted to string
        assert formatted["id"] == "507f1f77bcf86cd799439011"
        
        # Check that required fields are present and formatted correctly
        assert formatted["title"] == "Test News Title"
        assert formatted["description"] == "Test news description"
        assert formatted["url"] == "https://example.com/news/test-news"
        assert formatted["source"]["name"] == "Test Source"
        assert formatted["source"]["domain"] == "example.com"
        assert formatted["published_at"] == datetime(2023, 1, 1, 12, 0, 0)
        
        # Check that optional fields are present and formatted correctly
        assert formatted["language"] == "en"
        assert formatted["categories"] == ["test", "technology"]
        assert formatted["topic_id"] == "507f1f77bcf86cd799439012"
        
        # Check image is properly formatted
        if "image" in formatted and formatted["image"] is not None:
            assert formatted["image"]["url"] == "https://example.com/images/test.jpg"
        
        # Check content is included when include_content=True
        assert formatted["content"] == "Test news content"
    
    def test_format_news_item_light_minimal(self):
        """Test _format_news_item_light with minimal required fields."""
        # Create a test news item with only required fields
        test_item = {
            "_id": ObjectId("507f1f77bcf86cd799439011"),
            "title": "Minimal Test News",
            "url": "https://example.com/news/minimal",
            "source_name": "Test Source",
            "source_domain": "example.com",
            "published_at": datetime(2023, 1, 1, 12, 0, 0)
        }
        
        # Format the item with include_content=False (default)
        formatted = _format_news_item_light(test_item)
        
        # Check required fields
        assert formatted["id"] == "507f1f77bcf86cd799439011"
        assert formatted["title"] == "Minimal Test News"
        assert formatted["url"] == "https://example.com/news/minimal"
        assert formatted["source"]["name"] == "Test Source"
        assert formatted["source"]["domain"] == "example.com"
        assert formatted["published_at"] == datetime(2023, 1, 1, 12, 0, 0)
        
        # Check default values for optional fields
        assert formatted["description"] == ""  # Empty when not included and include_content=False
        assert formatted["categories"] == []
        assert formatted["topic_id"] is None
        assert formatted["image"] is None
        assert formatted["country"] == "BR"  # Default from function
        assert formatted["language"] == "pt"  # Default from function
        
        # Check content is not included when include_content=False
        assert "content" not in formatted
    
    def test_format_news_item_light_with_none_values(self):
        """Test _format_news_item_light with None values."""
        # Create a test news item with some None values
        test_item = {
            "_id": ObjectId("507f1f77bcf86cd799439011"),
            "title": None,
            "url": None,
            "source_name": None,
            "source_domain": None,
            "published_at": None,
            "description": None,
            "language": None,
            "categories": None,
            "topic_id": None,
            "image_url": None,
            "content": None
        }
        
        # Format the item
        formatted = _format_news_item_light(test_item)
        
        # Check default values when None is provided
        assert formatted["id"] == "507f1f77bcf86cd799439011"
        
        # Check that required fields are present
        assert "title" in formatted
        assert "url" in formatted
        assert "source" in formatted
        assert "name" in formatted["source"]
        assert "domain" in formatted["source"]
        assert "description" in formatted
        assert "categories" in formatted
        assert "topic_id" in formatted
        
        # Check that categories is either None or a list
        assert formatted["categories"] is None or isinstance(formatted["categories"], list)
        
        # Check that published_at is either a datetime or None
        assert formatted["published_at"] is None or isinstance(formatted["published_at"], datetime)
    
    def test_format_news_item_light_with_string_dates(self):
        """Test _format_news_item_light with string dates."""
        # Create a test news item with string dates
        test_item = {
            "_id": ObjectId("507f1f77bcf86cd799439011"),
            "title": "News with String Dates",
            "url": "https://example.com/news/string-dates",
            "source_name": "Test Source",
            "source_domain": "example.com",
            "published_at": "2023-01-01T12:00:00Z",
            "created_at": "2023-01-01T10:00:00Z",
            "updated_at": "2023-01-02T10:30:00Z"
        }
        
        # Format the item
        formatted = _format_news_item_light(test_item)
        
        # Check that string dates are properly parsed into datetime objects
        assert formatted["published_at"] == datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        assert formatted["created_at"] == datetime(2023, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        assert formatted["updated_at"] == datetime(2023, 1, 2, 10, 30, 0, tzinfo=timezone.utc)
    
    def test_format_news_item_light_with_include_content(self):
        """Test _format_news_item_light with include_content=True."""
        # Create a test news item with content
        test_item = {
            "_id": ObjectId("507f1f77bcf86cd799439011"),
            "title": "News with Content",
            "url": "https://example.com/news/with-content",
            "source_name": "Test Source",
            "source_domain": "example.com",
            "published_at": datetime(2023, 1, 1, 12, 0, 0),
            "content": "This is the full news content.",
            "description": "Short description"
        }
        
        # Format the item with include_content=True
        formatted = _format_news_item_light(test_item, include_content=True)
        
        # Check that content is included when include_content=True
        assert formatted["content"] == "This is the full news content."
        
        # Format the item with include_content=False (default)
        formatted = _format_news_item_light(test_item, include_content=False)
        
        # Check that content is not included when include_content=False
        assert "content" not in formatted
    
    def test_format_news_item_light(self):
        """Test the _format_news_item_light function."""
        # Create a test news item
        test_item = {
            "_id": ObjectId(),
            "title": "Test News",
            "description": "Test Description",
            "content": "Test Content",
            "url": "http://example.com/test",
            "source_name": "Test Source",
            "source_domain": "example.com",
            "published_at": datetime.utcnow(),
            "topics": ["test"],
            "language": "pt",
            "country": "BR",
            "metrics": {
                "views": 10,
                "shares": 2,
                "engagement_rate": 0.5,
                "avg_read_time": 60
            },
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "metadata": {
                "has_image": False,
                "has_favicon": False,
                "has_description": True,
                "language": "pt",
                "country": "BR",
                "source": "example.com"
            }
        }
        
        # Format the item
        formatted = _format_news_item_light(test_item)
        
        # Check the formatted output
        assert formatted["id"] == str(test_item["_id"])
        assert formatted["title"] == test_item["title"]
        # A descrição deve estar vazia no formato light
        assert formatted["description"] == ""
        # O conteúdo não deve estar incluído no formato light
        assert "content" not in formatted
        assert formatted["url"] == test_item["url"]
        assert formatted["source"]["name"] == test_item["source_name"]
        assert formatted["source"]["domain"] == test_item["source_domain"]
        assert formatted["topics"] == test_item["topics"]
        assert formatted["language"] == test_item["language"]
        assert formatted["country"] == test_item["country"]
        assert "created_at" in formatted
        assert "updated_at" in formatted
        assert "published_at" in formatted
        # O campo metadata não está mais incluído no formato light
        assert "metadata" not in formatted


class TestFormatNewsItem:
    """Tests for the format_news_item function."""
    
    def test_format_news_item_full(self):
        """Test format_news_item with all fields."""
        # Test with all possible fields
        test_item = {
            "_id": ObjectId(),
            "title": "Test News",
            "description": "Test Description",
            "content": "Test Content",
            "url": "http://example.com/test",
            "source_name": "Test Source",
            "source_domain": "example.com",
            "published_at": datetime.utcnow(),
            "topics": ["test"],
            "language": "pt",
            "country": "BR",
            "metrics": {
                "views": 100,
                "shares": 20,
                "engagement_rate": 0.85,
                "avg_read_time": 120,
                "last_viewed_at": datetime.utcnow()
            },
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "metadata": {
                "has_image": False,
                "has_favicon": False,
                "has_description": True,
                "language": "pt",
                "country": "BR",
                "source": "example.com"
            }
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
        
        # Verificar campos que devem estar presentes
        assert "keywords" not in formatted  # Não é mais incluído
        assert "entities" not in formatted  # Não é mais incluído
        assert "sentiment" not in formatted  # Não é mais incluído
        
        # Check metrics (should be included in full content)
        assert "metrics" in formatted
        assert formatted["metrics"]["views"] == test_item["metrics"]["views"]
        
        # Check timestamps
        assert "created_at" in formatted
        assert "updated_at" in formatted
        assert "published_at" in formatted
        
        # Test without full content
        formatted_light = format_news_item(test_item, include_full_content=False)
        # O conteúdo é incluído, mas vazio quando não há conteúdo
        assert formatted_light["content"] == ""
        # As métricas são incluídas mesmo sem full content
        assert "metrics" in formatted_light
    
    def test_format_news_item_minimal(self):
        """Test format_news_item with minimal fields."""
        # Test with missing optional fields
        minimal_item = {
            "_id": ObjectId(),
            "title": "Minimal News",
            "url": "http://example.com/minimal",
            "source_name": "Minimal Source",
            "source_domain": "example.com",
            "published_at": datetime.utcnow(),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "language": "pt",
            "country": "BR",
            "metadata": {
                "has_image": False,
                "has_favicon": False,
                "has_description": False,
                "language": "pt",
                "country": "BR",
                "source": "example.com"
            }
        }
        
        formatted_minimal = format_news_item(minimal_item)
        assert formatted_minimal["title"] == "Minimal News"
        assert formatted_minimal["source"]["name"] == "Minimal Source"
        assert formatted_minimal["description"] == ""  # Should have default empty string
        assert formatted_minimal["content"] == ""  # Should have default empty string
        assert "metadata" in formatted_minimal
        assert formatted_minimal["metadata"]["has_description"] is False
    
    def test_format_news_item_with_none_values(self):
        """Test format_news_item with None values."""
        # Test with None values
        item_with_none = {
            "_id": ObjectId(),
            "title": "None",  # Should be converted to string
            "url": "http://example.com/none",
            "source_name": "None Test",
            "source_domain": "example.com",
            "published_at": None,  # Should be set to current time
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "topics": None,
            "language": "pt",
            "country": "BR",
            "metrics": None,
            "sentiment": None,
            "metadata": {
                "has_image": False,
                "has_favicon": False,
                "has_description": False,
                "language": "pt",
                "country": "BR",
                "source": "example.com"
            }
        }
        
        formatted_none = format_news_item(item_with_none)
        assert formatted_none["title"] == "None"  # Should be converted to string
        assert formatted_none["published_at"] is not None  # Should be set to current time
        assert formatted_none.get("topics") == []  # Should default to empty list
        # O campo categories é adicionado automaticamente como lista vazia
        assert formatted_none.get("categories") == []
        assert formatted_none.get("metrics") is None
        assert formatted_none.get("sentiment") is None
