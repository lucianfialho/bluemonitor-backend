"""Tests for the TaskManager class."""
import asyncio
from datetime import datetime, timedelta
import pytest

from app.services.task_manager import TaskManager, task_manager

@pytest.mark.asyncio
async def test_create_task():
    """Test creating a new task."""
    manager = TaskManager()
    task_id = manager.create_task("test_task", {"param1": "value1"})
    
    assert task_id is not None
    assert len(task_id) == 36  # UUID length
    
    task = manager.get_task_status(task_id)
    assert task is not None
    assert task["task_id"] == task_id
    assert task["type"] == "test_task"
    assert task["status"] == "pending"
    assert "created_at" in task
    assert task["metadata"] == {"param1": "value1"}

@pytest.mark.asyncio
async def test_task_lifecycle():
    """Test the complete lifecycle of a task."""
    manager = TaskManager()
    task_id = manager.create_task("test_lifecycle")
    
    # Check initial status
    task = manager.get_task_status(task_id)
    assert task["status"] == "pending"
    assert task["started_at"] is None
    assert task["completed_at"] is None
    assert task["result"] is None
    assert task["error"] is None
    
    # Start the task
    assert manager.start_task(task_id) is True
    task = manager.get_task_status(task_id)
    assert task["status"] == "processing"
    assert task["started_at"] is not None
    assert task["completed_at"] is None
    
    # Complete the task
    result = {"items_processed": 10, "status": "success"}
    assert manager.complete_task(task_id, result) is True
    task = manager.get_task_status(task_id)
    assert task["status"] == "completed"
    assert task["completed_at"] is not None
    assert task["result"] == result
    assert task["error"] is None
    assert "duration_seconds" in task
    
    # Try to start or complete a completed task (should return False)
    assert manager.start_task(task_id) is False
    assert manager.complete_task(task_id, {}) is False

@pytest.mark.asyncio
async def test_task_failure():
    """Test task failure handling."""
    manager = TaskManager()
    task_id = manager.create_task("test_failure")
    manager.start_task(task_id)
    
    # Fail the task
    error = Exception("Something went wrong")
    assert manager.fail_task(task_id, error) is True
    
    task = manager.get_task_status(task_id)
    assert task["status"] == "failed"
    assert task["completed_at"] is not None
    assert task["error"] == "Something went wrong"
    assert task["result"] is None
    assert "duration_seconds" in task

@pytest.mark.asyncio
async def test_cleanup_old_tasks():
    """Test cleaning up old tasks."""
    manager = TaskManager()
    now = datetime.utcnow()
    
    # Create some old tasks (2 days old)
    old_task_ids = []
    for i in range(3):
        task_id = manager.create_task(f"old_task_{i}")
        # Manually set the created_at to 2 days ago
        task = manager.tasks[task_id]
        task['created_at'] = now - timedelta(days=2)
        
        # Start and complete the task
        manager.start_task(task_id)
        task['started_at'] = now - timedelta(days=2, hours=1)
        
        manager.complete_task(task_id, {"test": "old"})
        task['completed_at'] = now - timedelta(days=2)
        old_task_ids.append(task_id)
    
    # Create some recent tasks
    recent_task_ids = []
    for i in range(2):
        task_id = manager.create_task(f"recent_task_{i}")
        manager.start_task(task_id)
        recent_task_ids.append(task_id)
    
    # Clean up tasks older than 1 day
    removed = manager.cleanup_old_tasks(days=1)
    
    # Should have removed the old tasks
    assert removed == 3, f"Expected to remove 3 old tasks, but removed {removed}"
    
    # Old tasks should be gone
    for task_id in old_task_ids:
        assert manager.get_task_status(task_id) is None, f"Old task {task_id} was not removed"
    
    # Recent tasks should still be there
    for task_id in recent_task_ids:
        assert manager.get_task_status(task_id) is not None, f"Recent task {task_id} was incorrectly removed"

@pytest.mark.asyncio
async def test_singleton():
    """Test that task_manager is a singleton."""
    from app.services.task_manager import task_manager as tm1
    from app.services.task_manager import task_manager as tm2
    
    # Both should be the same instance
    assert tm1 is tm2
    
    # Create a task using one reference
    task_id = tm1.create_task("singleton_test")
    
    # Should be accessible from the other reference
    task = tm2.get_task_status(task_id)
    assert task is not None
    assert task["task_id"] == task_id
    assert task["type"] == "singleton_test"
