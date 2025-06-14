"""Integration tests for task cleanup functionality."""
import asyncio
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import app
from app.services.task_manager import task_manager
from app.middleware.task_cleanup import TaskCleanupMiddleware

# Use the test client
client = TestClient(app)

@pytest.fixture
def mock_datetime_now(monkeypatch):
    """Mock datetime.utcnow() for testing."""
    class MockDateTime:
        @classmethod
        def utcnow(cls):
            return datetime(2023, 1, 1, 12, 0, 0)
    
    monkeypatch.setattr('datetime.datetime', MockDateTime)
    return MockDateTime

@pytest.mark.asyncio
async def test_task_cleanup_middleware_integration():
    """Test that the task cleanup middleware works with the task manager."""
    # Clear any existing tasks
    task_manager.tasks.clear()
    
    # Create some test tasks with different statuses and ages
    now = datetime.utcnow()
    
    # Task 1: Completed just now
    task1_id = task_manager.create_task("test_task", {"test": "data1"})
    task = task_manager.tasks[task1_id]
    task['status'] = 'completed'
    task['completed_at'] = now
    
    # Task 2: Failed 8 days ago (should be cleaned up)
    task2_id = task_manager.create_task("test_task", {"test": "data2"})
    task = task_manager.tasks[task2_id]
    task['status'] = 'failed'
    task['completed_at'] = now - timedelta(days=8)
    
    # Task 3: Still processing (should not be cleaned up)
    task3_id = task_manager.create_task("test_task", {"test": "data3"})
    task = task_manager.tasks[task3_id]
    task['status'] = 'processing'
    task['started_at'] = now - timedelta(hours=1)
    
    # Create a test app with the middleware
    test_app = FastAPI()
    
    # Add a test endpoint
    @test_app.get("/test")
    async def test_endpoint():
        return {"status": "ok"}
    
    # Add the middleware
    middleware = TaskCleanupMiddleware(
        test_app,
        cleanup_interval=0.1,  # Short interval for testing
        max_task_age_days=7
    )
    
    # Create a test client
    test_client = TestClient(middleware)
    
    # Make a request to trigger the middleware
    response = test_client.get("/test")
    assert response.status_code == 200
    
    # Wait for the cleanup task to run
    await asyncio.sleep(0.2)
    
    # Check that the tasks were cleaned up correctly
    tasks = task_manager.tasks
    assert task1_id in tasks  # Should still be there
    assert task2_id not in tasks  # Should be cleaned up
    assert task3_id in tasks  # Should still be there (still processing)
    
    # Clean up
    task_manager.tasks.clear()

@pytest.mark.asyncio
async def test_task_cleanup_with_real_api():
    """Test task cleanup with the real API."""
    # Clear any existing tasks
    task_manager.tasks.clear()
    
    try:
        # Create a task that will be cleaned up
        old_task_id = task_manager.create_task("test_task", {"test": "old_data"})
        task_manager.tasks[old_task_id].update({
            'status': 'completed',
            'completed_at': datetime.utcnow() - timedelta(days=8)  # 8 days old
        })
        
        # Create a task that should be kept
        new_task_id = task_manager.create_task("test_task", {"test": "new_data"})
        task_manager.tasks[new_task_id].update({
            'status': 'completed',
            'completed_at': datetime.utcnow() - timedelta(days=1)  # 1 day old
        })
        
        # Manually trigger the cleanup (since the interval might be long)
        removed = task_manager.cleanup_old_tasks(days=7)
        
        # Check that the old task was removed and the new one was kept
        assert removed >= 1  # At least the old task was removed
        assert old_task_id not in task_manager.tasks
        assert new_task_id in task_manager.tasks
        
    finally:
        # Clean up
        task_manager.tasks.clear()
