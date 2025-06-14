"""Tests for health check endpoints."""
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from app.main import app
from app.services.task_manager import TaskManager, task_manager

client = TestClient(app)


def test_health_check():
    """Test the basic health check endpoint."""
    response = client.get("/api/v1/health")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "ok"}


def test_health_check_tasks_success():
    """Test the task health check endpoint with successful task manager."""
    # Mock task manager statistics
    mock_stats = {
        "total": 5,
        "by_status": {"pending": 2, "processing": 1, "completed": 2}
    }
    
    # Create a mock task
    test_task = {
        "task_id": "test-task-123",
        "type": "test_task",
        "status": "processing",
        "created_at": datetime.utcnow() - timedelta(minutes=5),
        "started_at": datetime.utcnow() - timedelta(minutes=4),
        "completed_at": None,
        "metadata": {},
        "result": None,
        "error": None
    }
    
    # Patch the task manager
    with patch.object(task_manager, 'get_task_statistics', return_value=mock_stats), \
         patch.dict(task_manager.tasks, {"test-task-123": test_task}):
        
        response = client.get("/api/v1/health/tasks")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ok"
        assert data["task_manager"] == "operational"
        assert data["task_count"] == 5
        assert data["tasks_by_status"] == {"pending": 2, "processing": 1, "completed": 2}
        assert data["has_long_running_tasks"] is True


def test_health_check_tasks_error():
    """Test the task health check endpoint when task manager raises an exception."""
    # Patch the task manager to raise an exception
    with patch.object(task_manager, 'get_task_statistics', side_effect=Exception("Test error")):
        response = client.get("/api/v1/health/tasks")
        
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert "Task manager is not available" in response.json()["detail"]
        assert "Test error" in response.json()["detail"]


def test_health_check_tasks_no_long_running():
    """Test the task health check when there are no long-running tasks."""
    # Mock task manager statistics
    mock_stats = {
        "total": 3,
        "by_status": {"pending": 1, "completed": 2}
    }
    
    # Create a completed task
    test_task = {
        "task_id": "test-task-124",
        "type": "test_task",
        "status": "completed",
        "created_at": datetime.utcnow() - timedelta(minutes=30),
        "started_at": datetime.utcnow() - timedelta(minutes=29),
        "completed_at": datetime.utcnow() - timedelta(minutes=28),
        "metadata": {},
        "result": {"success": True},
        "error": None
    }
    
    # Patch the task manager
    with patch.object(task_manager, 'get_task_statistics', return_value=mock_stats), \
         patch.dict(task_manager.tasks, {"test-task-124": test_task}):
        
        response = client.get("/api/v1/health/tasks")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["has_long_running_tasks"] is False
