"""Scheduled background tasks for the application."""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List

from app.core.config import settings
from app.core.scheduler import scheduler
from app.core.database import MongoDBManager
from app.services.news.collector import news_collector
from app.services.ai.topic_cluster import topic_cluster

logger = logging.getLogger(__name__)

# List of search queries for news collection
DEFAULT_SEARCH_QUERIES = [
    "autismo Brasil",
    "TEA Brasil",
    "transtorno do espectro autista",
    "inclusão autismo",
    "direitos autistas",
    "tratamento autismo",
    "educação especial autismo"
]

# Default country for news collection
DEFAULT_COUNTRY = 'BR'

async def collect_news() -> None:
    """Task to collect news from various sources."""
    logger.info("Starting scheduled news collection...")
    
    try:
        # Process each search query
        for query in DEFAULT_SEARCH_QUERIES:
            try:
                await news_collector.process_news_batch(query, DEFAULT_COUNTRY)
            except Exception as e:
                logger.error(f"Error processing query '{query}': {str(e)}", exc_info=True)
        
        logger.info("Completed scheduled news collection")
    except Exception as e:
        logger.error(f"Error in scheduled news collection: {str(e)}", exc_info=True)

async def cluster_topics() -> None:
    """Task to cluster news articles into topics."""
    logger.info("Starting topic clustering...")
    
    try:
        await topic_cluster.cluster_recent_news(DEFAULT_COUNTRY)
        logger.info("Completed topic clustering")
    except Exception as e:
        logger.error(f"Error in topic clustering: {str(e)}", exc_info=True)

async def cleanup_old_data() -> None:
    """Task to clean up old data from the database."""
    logger.info("Starting data cleanup...")
    
    # Create a new MongoDBManager instance
    mongodb_manager = MongoDBManager()
    
    try:
        await mongodb_manager.connect_to_mongodb()
        
        async with mongodb_manager.get_db() as db:
            try:
                # Delete news articles older than 30 days
                cutoff_date = datetime.utcnow() - timedelta(days=30)
                
                result = await db.news.delete_many({
                    "publish_date": {"$lt": cutoff_date}
                })
                
                logger.info(f"Deleted {result.deleted_count} old news articles")
                
                # Clean up topics with no articles
                result = await db.topics.delete_many({
                    "article_count": 0
                })
                
                logger.info(f"Deleted {result.deleted_count} empty topics")
                
            except Exception as e:
                logger.error(f"Error during cleanup operations: {str(e)}", exc_info=True)
                raise
                
    except Exception as e:
        logger.error(f"Failed to connect to database: {str(e)}", exc_info=True)
    finally:
        # Ensure the connection is closed
        if 'mongodb_manager' in locals():
            await mongodb_manager.close_mongodb_connection()
            logger.debug("Database connection closed")

def setup_scheduled_tasks() -> None:
    """Set up all scheduled tasks."""
    logger.info("Setting up scheduled tasks...")
    
    # News collection: Run every 6 hours, starting 1 minute after startup
    scheduler.add_job(
        collect_news,
        'interval',
        id='collect_news',
        hours=6,
        start_date=datetime.now() + timedelta(minutes=1)
    )
    
    # Topic clustering: Run every 12 hours, starting 5 minutes after startup
    scheduler.add_job(
        cluster_topics,
        'interval',
        id='cluster_topics',
        hours=12,
        start_date=datetime.now() + timedelta(minutes=5)
    )
    
    # Data cleanup: Run once per day at 3 AM
    scheduler.add_job(
        cleanup_old_data,
        'interval',
        id='cleanup_old_data',
        days=1,
        start_date=datetime.now().replace(hour=3, minute=0, second=0) + timedelta(days=1)
    )
    
    logger.info("Scheduled tasks set up successfully")
