"""Database connection and session management."""
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, List, Optional, Union

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING

from app.core.config import settings

# Configure logger
logger = logging.getLogger(__name__)


class MongoDBManager:
    """MongoDB connection manager."""
    
    def __init__(self):
        """Initialize the MongoDB manager."""
        self._client = None
        self._db = None
        self._lock = asyncio.Lock()
    
    @property
    def client(self) -> AsyncIOMotorClient:
        """Get the MongoDB client instance.
        
        Raises:
            RuntimeError: If the client is not initialized.
        """
        if self._client is None:
            raise RuntimeError("MongoDB client is not initialized. Call connect_to_mongodb() first.")
        return self._client
    
    @property
    def db(self) -> AsyncIOMotorDatabase:
        """Get the database instance.
        
        Raises:
            RuntimeError: If the database is not initialized.
        """
        if self._db is None:
            raise RuntimeError("Database is not initialized. Call connect_to_mongodb() first.")
        return self._db
    
    async def connect_to_mongodb(self) -> None:
        """Connect to MongoDB.
        
        This method is idempotent and can be called multiple times safely.
        """
        if self._client is not None:
            return
            
        async with self._lock:
            if self._client is not None:  # Check again in case another coroutine got the lock first
                return
                
            try:
                self._client = AsyncIOMotorClient(
                    settings.MONGODB_URL, 
                    connectTimeoutMS=10000, 
                    serverSelectionTimeoutMS=10000
                )
                # Test the connection
                await self._client.admin.command('ping')
                self._db = self._client[settings.MONGODB_DB_NAME]
                # Ensure indexes
                await self._ensure_indexes()
                logger.info(f"Successfully connected to MongoDB at {settings.MONGODB_URL}")
            except Exception as e:
                logger.error(f"Failed to connect to MongoDB: {str(e)}")
                self._client = None
                self._db = None
                raise
    
    async def close_mongodb_connection(self) -> None:
        """Close MongoDB connection."""
        async with self._lock:
            if self._client is not None:
                self._client.close()
                self._client = None
                self._db = None
    
    async def _ensure_indexes(self) -> None:
        """Ensure database indexes."""
        if self._db is None:
            return

        # News collection indexes
        await self._db.news.create_index(
            [("original_url", ASCENDING)], unique=True, name="unique_news_url"
        )
        await self._db.news.create_index(
            [("publish_date", DESCENDING)], name="news_publish_date_desc"
        )
        await self._db.news.create_index(
            [("collection_date", DESCENDING)], name="news_collection_date_desc"
        )
        await self._db.news.create_index(
            [("country_focus", ASCENDING)], name="news_country_focus"
        )
    
    @asynccontextmanager
    async def get_db(self) -> AsyncGenerator[AsyncIOMotorDatabase, None]:
        """Get a database connection.
        
        This is a context manager that yields the database connection.
        """
        await self.connect_to_mongodb()
        try:
            yield self.db
        finally:
            await self.close_mongodb_connection()
    
    async def connect(self) -> None:
        """Alias for connect_to_mongodb for backward compatibility."""
        await self.connect_to_mongodb()
    
    async def close(self) -> None:
        """Alias for close_mongodb_connection for backward compatibility."""
        await self.close_mongodb_connection()

    def get_database(self) -> AsyncIOMotorDatabase:
        """Get the database instance.
        
        Returns:
            AsyncIOMotorDatabase: The MongoDB database instance.
            
        Raises:
            RuntimeError: If the database is not initialized.
        """
        return self.db
        
    @asynccontextmanager
    async def get_db_client(self) -> AsyncGenerator[AsyncIOMotorClient, None]:
        """Get a MongoDB client instance.
        
        Yields:
            AsyncIOMotorClient: The MongoDB client instance.
            
        Raises:
            RuntimeError: If the client cannot be initialized.
        """
        await self.connect_to_mongodb()
        try:
            yield self.client
        except Exception as e:
            logger.error(f"Error in database client session: {str(e)}")
            raise

# Initialize the database connection manager
mongodb_manager = MongoDBManager()
