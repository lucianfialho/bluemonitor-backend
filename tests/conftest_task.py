"""Pytest fixtures for task manager tests."""
import pytest

from app.services.task_manager import TaskManager

@pytest.fixture
def task_manager():
    """Create a new TaskManager instance for testing."""
    # Create a new instance
    manager = TaskManager()
    
    # Clear any existing tasks
    manager.tasks.clear()
    
    yield manager
    
    # Clean up
    manager.tasks.clear()

@pytest.fixture
def sample_task_data():
    """Return sample task data for testing."""
    return {
        "task_id": "550e8400-e29b-41d4-a716-446655440000",
        "type": "test_task",
        "status": "pending",
        "created_at": "2023-01-01T12:00:00Z",
        "started_at": None,
        "completed_at": None,
        "metadata": {"test": "data"},
        "result": None,
        "error": None
    }
