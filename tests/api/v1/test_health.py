"""Tests for health check endpoints."""
import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check():
    """Test the basic health check endpoint."""
    response = client.get("/api/v1/health")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "ok"}


def test_health_check_tasks():
    """Test the task manager health check endpoint."""
    from app.services.task_manager import task_manager
    
    # Clear any existing tasks
    task_manager.tasks.clear()
    
    # Create some test tasks
    task_id1 = task_manager.create_task("test_task", {"test": "data1"})
    task_manager.start_task(task_id1)
    
    task_id2 = task_manager.create_task("test_task", {"test": "data2"})
    task_manager.complete_task(task_id2, {"result": "success"})
    
    # Make the request
    response = client.get("/api/v1/health/tasks")
    
    # Check the response
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    # Check the basic structure
    assert data["status"] == "ok"
    assert data["task_manager"] == "operational"
    assert isinstance(data["task_count"], int)
    assert data["task_count"] >= 2  # At least our 2 test tasks
    
    # Check the status breakdown
    assert "tasks_by_status" in data
    assert "pending" in data["tasks_by_status"] or "processing" in data["tasks_by_status"]
    
    # Check the long running flag (should be True since we have a processing task)
    assert data["has_long_running_tasks"] is True


def test_health_check_tasks_error(monkeypatch):
    """Test the task manager health check when there's an error."""
    # Mock the task manager to raise an exception
    def mock_get_task_statistics():
        raise Exception("Test error")
    
    from app.services import task_manager as tm
    monkeypatch.setattr(tm.TaskManager, "get_task_statistics", mock_get_task_statistics)
    
    # Make the request
    response = client.get("/api/v1/health/tasks")
    
    # Check the error response
    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    data = response.json()
    assert "detail" in data
    assert "Task manager is not available" in data["detail"]
