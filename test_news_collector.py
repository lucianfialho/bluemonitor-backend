"""Test script for the news collector service."""
import asyncio
import logging
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.absolute()))

from app.core.config import settings
from app.core.database import mongodb_manager
from app.services.news.collector import NewsCollector
from app.services.ai.processor import ai_processor

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG to see all messages
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('test_news_collector.log')
    ]
)
logger = logging.getLogger(__name__)

# Set log level for specific loggers
logging.getLogger('app.services.ai.processor').setLevel(logging.DEBUG)
logging.getLogger('sentence_transformers').setLevel(logging.DEBUG)
logging.getLogger('transformers').setLevel(logging.INFO)  # Keep transformers at INFO to reduce noise

async def test_news_collection():
    """Test the news collection and processing pipeline."""
    logger.info("Starting news collection test...")
    
    try:
        # Initialize MongoDB connection
        await mongodb_manager.connect_to_mongodb()
        logger.info("Connected to MongoDB")
        
        # Initialize AI models
        logger.info("Loading AI models...")
        await ai_processor.load_models()
        logger.info("AI models loaded successfully")
        
        # Initialize news collector
        collector = NewsCollector()
        
        # Test query
        test_query = "autismo Brasil"
        logger.info(f"Testing with query: {test_query}")
        
        # Process a small batch of news
        await collector.process_news_batch(test_query, 'BR')
        
        # Check if news were saved to the database
        async with mongodb_manager.get_db() as db:
            # Get all news for the test query
            all_news = await db.news.find({"query_source": test_query}).to_list(length=100)
            news_count = len(all_news)
            logger.info(f"Total news in database for query '{test_query}': {news_count}")
            
            if news_count == 0:
                # Try to get any news in the database
                all_news = await db.news.find().to_list(length=100)
                news_count = len(all_news)
                logger.info(f"Total news in database (all queries): {news_count}")
                
                if news_count > 0:
                    logger.info("Available collections in database:")
                    collections = await db.list_collection_names()
                    for collection in collections:
                        count = await db[collection].count_documents({})
                        logger.info(f"- {collection}: {count} documents")
                
            # Log details of each news item
            for i, news in enumerate(all_news[:5]):  # Log first 5 news items
                logger.info(f"\nNews {i+1}:")
                logger.info(f"  Title: {news.get('extracted_title')}")
                logger.info(f"  Source: {news.get('source_name')}")
                logger.info(f"  URL: {news.get('original_url')}")
                logger.info(f"  Published: {news.get('publish_date')}")
                logger.info(f"  Collection date: {news.get('collection_date')}")
                
                # Check for processing errors
                if 'processing_error' in news:
                    logger.error(f"  Processing error: {news['processing_error']}")
                
                # Check embedding
                embedding = news.get('embedding', [])
                logger.info(f"  Embedding: {'Yes' if embedding else 'No'}")
                if embedding:
                    logger.info(f"  Embedding dimensions: {len(embedding)}")
                else:
                    logger.warning("  No embedding generated for this news article")
            
            if news_count > 5:
                logger.info(f"... and {news_count - 5} more news items")
        
        logger.info("News collection test completed successfully")
        
    except Exception as e:
        logger.error(f"Error during news collection test: {str(e)}", exc_info=True)
    finally:
        # Clean up
        await mongodb_manager.close_mongodb_connection()
        logger.info("Disconnected from MongoDB")

if __name__ == "__main__":
    asyncio.run(test_news_collection())
