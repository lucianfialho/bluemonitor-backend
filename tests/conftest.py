"""Pytest configuration and fixtures for testing the BlueMonitor API."""
import asyncio
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict, Any, Optional

import httpx
import pytest
from asgi_lifespan import LifespanManager
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
        app_mongodb_manager = MongoDBManager()
        await app_mongodb_manager.connect_to_mongodb()
        app.state.mongodb_manager = app_mongodb_manager
        # Start the scheduler (if needed)
        if hasattr(scheduler, 'running') and getattr(scheduler, 'running', False):
            scheduler.shutdown()
        scheduler.start()
        try:
            yield
        finally:
            if hasattr(scheduler, 'running') and getattr(scheduler, 'running', False):
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

@pytest.fixture(scope="function")
def app() -> FastAPI:
    """Create a test FastAPI application (function scope para garantir ciclo de vida correto)."""
    return create_test_application()

@pytest.fixture(scope="function")
def test_client(app: FastAPI) -> TestClient:
    """Create a test client for the FastAPI application (function scope)."""
    return TestClient(app)

@pytest.fixture(scope="function")
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

@pytest.fixture(scope="function")
async def test_db(app: FastAPI) -> AsyncGenerator[AsyncIOMotorDatabase, None]:
    """Retorna o banco de dados usado pelo app FastAPI nos testes."""
    mongodb_manager = app.state.mongodb_manager
    db = mongodb_manager.db
    # Limpa o banco antes do teste
    collections = await db.list_collection_names()
    for collection in collections:
        await db.drop_collection(collection)
    await mongodb_manager._ensure_indexes()
    yield db
    # Limpa após o teste
    await db.news.delete_many({})

@pytest.fixture(scope="function")
async def test_news(test_db: AsyncIOMotorDatabase):
    """Cria dados de notícia de teste no banco do app."""
    await test_db.news.drop()
    test_news_data = [
        {
            "_id": f"507f1f77bcf86cd7994390{i:02d}",
            "title": f"Test News {i+1}",
            "content": "This is a test news article about autism.",
            "url": f"https://example.com/news/{i+1}",
            "original_url": f"https://example.com/original-news/{i+1}",  # Garante unicidade
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
    related_news = [
        {
            "_id": "507f1f77bcf86cd799439099",
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
        }
    ]
    await test_db.news.insert_many(test_news_data + related_news)
    await test_db.metrics.insert_one({
        "news_id": test_news_data[0]["_id"],
        "views": 100,
        "shares": 20,
        "engagement_rate": 0.85,
        "avg_read_time": 120,
        "last_viewed_at": "2023-01-01T12:00:00Z"
    })
    return test_news_data[0]

@pytest.fixture(scope="function")
async def async_client(app: FastAPI) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Cria um AsyncClient para testes de integração, garantindo ciclo de vida do app e acesso ao mongodb_manager via LifespanManager."""
    async with LifespanManager(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

# DICA: Use a fixture async_client para testes de integração que dependem do ciclo de vida do app (lifespan),
# pois ela garante que o app.state.mongodb_manager estará disponível.
# Exemplo de uso em um teste:
# async def test_alguma_coisa(async_client, test_news):
#     response = await async_client.get("/api/v1/news")
#     assert response.status_code == 200
#
# Para testes unitários que não dependem do ciclo de vida, use test_client normalmente.
