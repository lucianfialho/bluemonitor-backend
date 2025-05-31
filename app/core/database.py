"""Database connection and session management."""
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

logger = logging.getLogger(__name__)

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING

from app.core.config import settings


class MongoDBManager:
    """MongoDB connection manager."""

    client: Optional[AsyncIOMotorClient] = None
    db: Optional[AsyncIOMotorDatabase] = None

    @classmethod
    async def connect_to_mongodb(cls) -> None:
        """Connect to MongoDB."""
        try:
            cls.client = AsyncIOMotorClient(settings.MONGODB_URL)
            # Test the connection
            await cls.client.admin.command('ping')
            cls.db = cls.client[settings.MONGODB_DB_NAME]
            # Ensure indexes
            await cls._ensure_indexes()
            logger.info(f"Successfully connected to MongoDB at {settings.MONGODB_URL}")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {str(e)}")
            raise

    @classmethod
    async def close_mongodb_connection(cls) -> None:
        """Close MongoDB connection."""
        if cls.client:
            cls.client.close()
            cls.client = None
            cls.db = None

    @classmethod
    async def _ensure_indexes(cls) -> None:
        """Ensure database indexes."""
        if cls.db is None:
            return

        # News collection indexes
        await cls.db.news.create_index(
            [("original_url", ASCENDING)], unique=True, name="unique_news_url"
        )
        await cls.db.news.create_index(
            [("publish_date", DESCENDING)], name="news_publish_date_desc"
        )
        await cls.db.news.create_index(
            [("collection_date", DESCENDING)], name="news_collection_date_desc"
        )
        await cls.db.news.create_index(
            [("country_focus", ASCENDING)], name="news_country_focus"
        )

        # Topics collection indexes
        await cls.db.topics.create_index(
            [("last_updated_at", DESCENDING)], name="topics_last_updated_desc"
        )
        await cls.db.topics.create_index(
            [("country_focus", ASCENDING)], name="topics_country_focus"
        )

    @classmethod
    @asynccontextmanager
    async def get_db_client(cls) -> AsyncGenerator[AsyncIOMotorClient, None]:
        """Get a MongoDB client instance."""
        if not cls.client:
            await cls.connect_to_mongodb()
        try:
            if cls.client is None:
                raise RuntimeError("MongoDB client not initialized")
            yield cls.client
        finally:
            pass  # Don't close the client here, let it be managed by the lifespan

    @classmethod
    @asynccontextmanager
    async def get_db(cls) -> AsyncGenerator[AsyncIOMotorDatabase, None]:
        """Get a database connection.
        
        Yields:
            The database connection.
        """
        if cls.db is None:
            await cls.connect_to_mongodb()
        try:
            yield cls.db
        finally:
            # Don't close the connection, just yield it
            pass

# Initialize the database connection manager
mongodb_manager = MongoDBManager()
