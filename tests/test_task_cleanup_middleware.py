"""Tests for the task cleanup middleware."""
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.middleware.task_cleanup import TaskCleanupMiddleware, setup_task_cleanup

@pytest.fixture
def test_app():
    """Create a test FastAPI application with the middleware."""
    app = FastAPI()
    
    # Add a test endpoint
    @app.get("/test")
    async def test_endpoint():
        return {"status": "ok"}
    
    return app

@pytest.mark.asyncio
async def test_task_cleanup_middleware():
    """Test the task cleanup middleware."""
    # Create a mock task manager
    mock_task_manager = AsyncMock()
    mock_task_manager.cleanup_old_tasks.return_value = 2
    
    # Create a test app
    app = FastAPI()
    
    # Add a test endpoint
    @app.get("/test")
    async def test_endpoint():
        return {"status": "ok"}
    
    # Patch the task manager
    with patch('app.middleware.task_cleanup.task_manager', mock_task_manager):
        # Add the middleware to the test app
        middleware = TaskCleanupMiddleware(
            app,
            cleanup_interval=0.1,  # Short interval for testing
            max_task_age_days=1
        )
        
        # Create a test client
        client = TestClient(middleware)
        
        # Make a request to trigger the middleware
        response = client.get("/test")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        
        # Wait for the cleanup task to run
        await asyncio.sleep(0.2)
        
        # Check that cleanup_old_tasks was called
        mock_task_manager.cleanup_old_tasks.assert_called_once_with(days=1)

@pytest.mark.asyncio
async def test_setup_task_cleanup(test_app):
    """Test the setup_task_cleanup function."""
    # Create a mock task manager
    mock_task_manager = AsyncMock()
    mock_task_manager.cleanup_old_tasks.return_value = 0
    
    # Patch the task manager and add_middleware
    with patch('app.middleware.task_cleanup.task_manager', mock_task_manager), \
         patch.object(test_app, 'add_middleware') as mock_add_middleware:
        
        # Call the setup function
        setup_gen = setup_task_cleanup(test_app)
        await setup_gen.__anext__()
        
        # Check that add_middleware was called with the correct arguments
        mock_add_middleware.assert_called_once()
        args, kwargs = mock_add_middleware.call_args
        assert args[0] == TaskCleanupMiddleware
        assert kwargs["cleanup_interval"] == 3600
        assert kwargs["max_task_age_days"] == 7
        
        # Cleanup
        try:
            await setup_gen.__anext__()
        except StopAsyncIteration:
            pass

@pytest.mark.asyncio
async def test_periodic_cleanup():
    """Test the periodic cleanup task."""
    # Create a mock task manager
    mock_task_manager = AsyncMock()
    mock_task_manager.cleanup_old_tasks.return_value = 1
    
    # Create a test app
    app = FastAPI()
    
    # Create the middleware with a short interval
    middleware = TaskCleanupMiddleware(
        app,
        cleanup_interval=0.1,
        max_task_age_days=1
    )
    
    # Patch the task manager
    with patch('app.middleware.task_cleanup.task_manager', mock_task_manager):
        # Start the periodic cleanup
        task = asyncio.create_task(middleware._periodic_cleanup())
        
        # Wait for the task to run at least once
        await asyncio.sleep(0.2)
        
        # Cancel the task
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        
        # Check that cleanup_old_tasks was called
        mock_task_manager.cleanup_old_tasks.assert_called_with(days=1)
        assert mock_task_manager.cleanup_old_tasks.call_count > 0
