"""Unit tests for the TopicCluster service."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, ANY
from datetime import datetime, timedelta
import numpy as np
from bson import ObjectId

from app.services.ai.topic_cluster import TopicCluster

@pytest.fixture
def sample_article():
    """Return a sample article for testing."""
    return {
        "_id": ObjectId(),
        "title": "Novo tratamento para autismo mostra resultados promissores",
        "description": "Pesquisadores descobrem nova abordagem para tratamento do autismo",
        "content": "Um novo tratamento para o Transtorno do Espectro Autista (TEA) está mostrando resultados promissores em estudos iniciais...",
        "publish_date": "2023-06-01T10:00:00",
        "source": "Health News",
        "url": "https://example.com/artigo1",
        "country_focus": "BR",
        "embedding": np.random.rand(768).tolist(),
        "in_topic": False
    }

@pytest.fixture
def topic_cluster():
    """Return a TopicCluster instance for testing."""
    return TopicCluster()

class TestTopicCluster:
    """Test cases for the TopicCluster class."""

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

    @pytest.mark.asyncio
    async def test_cluster_recent_news_no_articles(self, topic_cluster):
        """Test clustering with no articles to process."""
        # Create a mock for the database
        mock_db = MagicMock()
        mock_db.news = MagicMock()
        
        # Configure the mock cursor to return an empty list with method chaining support
        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(return_value=[])
        # Allow method chaining for sort() and limit()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        # Make find return the mock cursor
        mock_db.news.find.return_value = mock_cursor
        
        # Mock the count_documents to return 0
        mock_db.news.count_documents = AsyncMock(return_value=0)
        
        # Create a mock for the MongoDBManager
        mock_mongo = MagicMock()
        
        # Create an async context manager mock for get_db
        mock_get_db = AsyncMock()
        mock_get_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_get_db.__aexit__ = AsyncMock(return_value=None)
        
        # Configure the mock to return our context manager
        mock_mongo.get_db.return_value = mock_get_db
        
        # Mock the connect_to_mongodb method
        mock_mongo.connect_to_mongodb = AsyncMock(return_value=None)
        
        # Mock the close_mongodb_connection method
        mock_mongo.close_mongodb_connection = AsyncMock(return_value=None)
        
        # Patch the MongoDBManager class to return our mock
        with patch('app.services.ai.topic_cluster.MongoDBManager', return_value=mock_mongo):
            # Call the method under test
            await topic_cluster.cluster_recent_news('BR')
            
            # Verify the correct methods were called
            mock_mongo.connect_to_mongodb.assert_awaited_once()
            mock_mongo.get_db.assert_called_once()
            
            # Verify count_documents was called with the correct queries
            expected_queries = [
                {},
                {'embedding': {'$exists': True, '$ne': None}},
                {'in_topic': True},
                {
                    'country_focus': 'BR',
                    'embedding': {'$exists': True, '$ne': None},
                    'in_topic': {'$ne': True}
                },
                {'embedding': {'$exists': True, '$ne': None}}
            ]
            
            # Get all calls to count_documents
            count_calls = mock_db.news.count_documents.call_args_list
            assert len(count_calls) == 5, f"Expected 5 calls to count_documents, got {len(count_calls)}"
            
            # Verify each query
            for i, call in enumerate(count_calls):
                args, _ = call
                assert args[0] == expected_queries[i], f"Unexpected query at position {i}: {args[0]}"
            
            # Verify find was called with the correct query
            # The actual code modifies the query if no articles are found with country filter
            mock_db.news.find.assert_any_call(
                {
                    'embedding': {'$exists': True, '$ne': None}
                }
            )
            
            # Verify cursor methods were called
            mock_cursor.sort.assert_called_once_with("publish_date", -1)
            mock_cursor.limit.assert_called_once_with(1000)  # self.max_articles_to_process
            mock_cursor.to_list.assert_awaited_once()
            mock_mongo.close_mongodb_connection.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_process_topic_new_topic(self, topic_cluster, sample_article):
        """Test processing a new topic."""
        # Mock the MongoDB methods
        mock_db = AsyncMock()
        mock_db.topics = AsyncMock()
        mock_db.news = AsyncMock()
        
        # Mock the find_similar_topic to return None (no similar topic found)
        with patch.object(topic_cluster, '_find_similar_topic', return_value=None) as mock_find, \
             patch.object(topic_cluster, '_create_new_topic') as mock_create, \
             patch('app.services.ai.topic_cluster.MongoDBManager') as mock_mongo:
            
            mock_mongo.return_value.__aenter__.return_value = mock_db
            
            await topic_cluster._process_topic([sample_article], 'BR')
            
            # Verify the methods were called
            mock_find.assert_called_once()
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_merge_similar_topics(self):
        """Test merging similar topics."""
        # Create a mock for the database
        mock_db = MagicMock()
        mock_db.topics = MagicMock()
        mock_db.news = MagicMock()
        
        # Configure the mock cursor to return a list with two sample topics
        from bson import ObjectId
        
        # Create ObjectId for articles
        
        article1_id = ObjectId("5f8d7a6e4b5c3d2e1f0a9b8c")
        article2_id = ObjectId("6e7f8a9b0c1d2e3f4a5b6c7d")
        
        sample_topic1 = {
            "_id": "topic1",
            "title": "Test Topic 1",
            "embedding": [0.1, 0.2, 0.3],
            "articles": [article1_id],
            "category": "Saúde",
            "country_focus": "BR",
            "is_active": True,
            "created_at": datetime.utcnow()
        }
        sample_topic2 = {
            "_id": "topic2",
            "title": "Test Topic 2",
            "embedding": [0.9, 0.8, 0.7],
            "articles": [article2_id],
            "category": "Saúde",
            "country_focus": "BR",
            "is_active": True,
            "created_at": datetime.utcnow()
        }
        
        # Configure the mock cursor to return our sample topics
        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(return_value=[sample_topic1, sample_topic2])
        
        # Make find return the mock cursor
        mock_db.topics.find.return_value = mock_cursor
        
        # Mock the update operations to return success
        mock_db.topics.update_one = AsyncMock()
        mock_db.news.update_many = AsyncMock()
        mock_db.topics.delete_one = AsyncMock()
        
        # Create a sample article to return
        sample_article = {
            '_id': article2_id,
            'title': 'Test Article',
            'source_name': 'Test Source',
            'content': 'Test content',
            'url': 'http://example.com',
            'publish_date': datetime.utcnow()
        }
        
        # Create a mock for find_one that returns the sample article
        async def mock_find_one(query, *args, **kwargs):
            if '_id' in query and query['_id'] == article2_id:
                return sample_article
            return None
            
        mock_db.news.find_one = mock_find_one
        
        # Create a mock for the MongoDBManager
        mock_mongo = MagicMock()
        
        # Create an async context manager mock for get_db
        mock_get_db = AsyncMock()
        mock_get_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_get_db.__aexit__ = AsyncMock(return_value=None)
        
        # Configure the mock to return our context manager
        mock_mongo.get_db.return_value = mock_get_db
        
        # Mock the connect_to_mongodb method as a coroutine
        mock_mongo.connect_to_mongodb = AsyncMock(return_value=None)
        
        # Mock the close_mongodb_connection method as a coroutine
        mock_mongo.close_mongodb_connection = AsyncMock(return_value=None)
        
        # Patch the MongoDBManager class to return our mock instance
        with patch('app.services.ai.topic_cluster.MongoDBManager') as mock_mongo_cls, \
             patch('app.services.ai.topic_cluster.cosine_similarity') as mock_cosine_sim:
            
            # Configure the mock class to return our mock instance
            mock_mongo_cls.return_value = mock_mongo
            
            # Configure cosine_similarity to return a high similarity score
            mock_cosine_sim.return_value = np.array([[0.9]])  # Above threshold (0.4)
            
            # Create a new instance of TopicCluster to ensure it uses our mock
            from app.services.ai.topic_cluster import TopicCluster
            topic_cluster = TopicCluster()
            
            # Call the method with topic documents
            await topic_cluster._merge_similar_topics(sample_topic1, sample_topic2)
            
            # Verify MongoDBManager was instantiated
            mock_mongo_cls.assert_called_once()
            
            # Verify the correct methods were called
            mock_mongo.connect_to_mongodb.assert_awaited_once()
            
            # Verify get_db was called and used as async context manager
            mock_mongo.get_db.assert_called_once()
            
            # Get the async context manager mock
            mock_get_db = mock_mongo.get_db.return_value
            mock_get_db.__aenter__.assert_awaited_once()
            mock_get_db.__aexit__.assert_awaited_once()
            
            # Verify the update operations were called
            mock_db.topics.update_one.assert_any_call(
                {"_id": sample_topic1["_id"]},
                {
                    "$set": {
                        "updated_at": ANY,
                        "article_count": 2,
                        "last_updated": ANY
                    },
                    "$addToSet": {
                        "sources": {
                            "$each": ["Test Source"]
                        }
                    }
                }
            )
            
            # Verify the topic was marked as inactive
            mock_db.topics.delete_one.assert_awaited_once_with(
                {"_id": sample_topic2["_id"]}
            )
            
            # Verify articles were updated to point to the new topic
            mock_db.news.update_many.assert_called_once_with(
                {"_id": {"$in": [article2_id]}},
                {"$set": {
                    "in_topic": True,
                    "topic_id": sample_topic1["_id"]
                }}
            )
            
            # Verify the connection was closed
            mock_mongo.close_mongodb_connection.assert_awaited_once()

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
