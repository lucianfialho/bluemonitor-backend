"""Pytest configuration and fixtures for testing the BlueMonitor API."""
import asyncio
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict, Any, Optional

import pytest
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import MongoClient

from app.core.config import settings
from app.core.database import MongoDBManager
from app.core.logging import configure_logging
from app.core.scheduler import scheduler
from app.api.v1.router import api_router
from app.services.task_manager import task_manager as global_task_manager
from app.services.task_manager import TaskManager

# Configure logging for tests
configure_logging()

# Test database configuration
TEST_DATABASE_URL = os.getenv("TEST_MONGODB_URL", "mongodb://localhost:27017")
TEST_DATABASE_NAME = "test_bluemonitor"

# Override settings for testing
settings.MONGODB_URL = f"{TEST_DATABASE_URL}/{TEST_DATABASE_NAME}"
settings.MONGODB_DB_NAME = TEST_DATABASE_NAME
settings.DEBUG = True
settings.ENVIRONMENT = "test"

def create_test_application() -> FastAPI:
    """Create a test FastAPI application."""
    
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        """Lifespan context manager for the test application."""
        # Initialize MongoDB connection
        # Create a new MongoDBManager for the app
        app_mongodb_manager = MongoDBManager()
        await app_mongodb_manager.connect_to_mongodb()
        
        # Store the manager in app state
        app.state.mongodb_manager = app_mongodb_manager
        
        # Start the scheduler (if needed)
        if scheduler.running:
            scheduler.shutdown()
        scheduler.start()
        
        try:
            yield
        finally:
            # Clean up
            if scheduler.running:
                scheduler.shutdown()
            if hasattr(app.state, 'mongodb_manager') and app.state.mongodb_manager.client:
                await app.state.mongodb_manager.close_mongodb_connection()
    
    # Create the FastAPI app with test settings
    app = FastAPI(
        title="BlueMonitor Test API",
        description="Test API for BlueMonitor",
        version="0.1.0",
        lifespan=lifespan,
        debug=True
    )
    
    # Store settings in app state
    app.state.settings = settings
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include API router
    app.include_router(api_router, prefix="/api/v1")
    
    # Health check endpoint
    @app.get("/health")
    async def health_check():
        return {"status": "ok"}
    
    return app

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="module")
def app() -> FastAPI:
    """Create a test FastAPI application."""
    return create_test_application()

@pytest.fixture(scope="module")
def test_client(app: FastAPI) -> TestClient:
    """Create a test client for the FastAPI application."""
    return TestClient(app)

@pytest.fixture(scope="module")
def app() -> FastAPI:
    """Create a test FastAPI application."""
    return create_test_application()

@pytest.fixture(scope="module")
def test_client(app: FastAPI) -> TestClient:
    """Create a test client for the FastAPI application."""
    return TestClient(app)

@pytest.fixture(scope="module")
async def db() -> AsyncGenerator[AsyncIOMotorDatabase, None]:
    """Create a test database connection."""
    # Create a new MongoDBManager instance for testing
    test_mongodb_manager = MongoDBManager()
    await test_mongodb_manager.connect_to_mongodb()
    
    # Get the database connection
    db = test_mongodb_manager.db
    
    # Clean up before tests
    try:
        # Drop all collections in the test database
        collections = await db.list_collection_names()
        for collection in collections:
            await db.drop_collection(collection)
        
        # Recreate indexes
        await test_mongodb_manager._ensure_indexes()
        
        yield db
    finally:
        # Clean up
        await db.news.delete_many({})
        await test_mongodb_manager.close_mongodb_connection()

@pytest.fixture(scope="module")
async def task_manager():
    """Create a new TaskManager instance for testing."""
    # Create a new instance
    manager = TaskManager()
    
    # Clear any existing tasks
    manager.tasks.clear()
    
    yield manager
    
    # Clean up
    manager.tasks.clear()

@pytest.fixture
async def test_news(db: AsyncIOMotorDatabase):
    """Create test news data in the database."""
    # Drop the collection to ensure a clean state
    await db.news.drop()
    
    # Create test data
    test_news_data = [
        {
            "_id": "507f1f77bcf86cd799439011",
            "title": "Test News 1",
            "content": "This is a test news article about autism.",
            "url": "https://example.com/news/1",
            "source": "Test Source",
            "source_name": "Test Source",
            "source_domain": "example.com",
            "published_at": "2023-01-01T12:00:00Z",
            "topics": ["test", f"topic-{i}"],
            "language": "en",
            "country": "US",
            "metrics": {
                "views": 0,
                "shares": 0,
                "engagement_rate": 0.0,
                "avg_read_time": 0
            },
            "created_at": "2023-01-01T12:00:00Z",
            "updated_at": "2023-01-01T12:00:00Z"
        }
        for i in range(3)
    ]
    
    # Add one more with the same topic
    related_news.append({
        "title": "Same Topic News",
        "description": "This shares a topic with the main news",
        "url": "https://example.com/same-topic",
        "original_url": "https://example.com/original-same-topic",
        "source_name": "Test Source",
        "source_domain": "example.com",
        "published_at": "2023-01-01T12:00:00Z",
        "topics": ["test"],
        "language": "en",
        "country": "US",
        "metrics": {
            "views": 0,
            "shares": 0,
            "engagement_rate": 0.0,
            "avg_read_time": 0
        },
        "created_at": "2023-01-01T12:00:00Z",
        "updated_at": "2023-01-01T12:00:00Z"
    })
    
    # Insert related news
    if related_news:
        await db.news.insert_many(related_news)
    
    # Add metrics
    await db.metrics.insert_one({
        "news_id": result.inserted_id,
        "views": 100,
        "shares": 20,
        "engagement_rate": 0.85,
        "avg_read_time": 120,
        "last_viewed_at": "2023-01-01T12:00:00Z"
    })
    
    return news_data
