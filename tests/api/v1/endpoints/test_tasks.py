"""Tests for task management endpoints."""
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.services.task_manager import TaskManager, task_manager

# O cliente de teste será injetado pela fixture test_client


def test_get_task_status_success(test_client):
    """Test getting the status of an existing task."""
    # Create a test task
    test_task = {
        "task_id": "test-task-123",
        "type": "test_task",
        "status": "completed",
        "created_at": datetime.utcnow() - timedelta(minutes=30),
        "started_at": datetime.utcnow() - timedelta(minutes=29),
        "completed_at": datetime.utcnow() - timedelta(minutes=25),
        "metadata": {"param1": "value1"},
        "result": {"output": "success"},
        "error": None
    }
    
    # Mock the task manager
    with patch.object(task_manager, 'get_task_status', return_value=test_task):
        response = test_client.get("/api/v1/tasks/test-task-123")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["task_id"] == "test-task-123"
        assert data["status"] == "completed"
        assert data["result"] == "[hidden]"  # Result should be hidden by default
        assert "started_at" in data
        assert "completed_at" in data


def test_get_task_status_include_result(test_client):
    """Test getting task status with include_result=True."""
    # Create a test task
    test_task = {
        "task_id": "test-task-124",
        "type": "test_task",
        "status": "completed",
        "created_at": datetime.utcnow() - timedelta(minutes=30),
        "started_at": datetime.utcnow() - timedelta(minutes=29),
        "completed_at": datetime.utcnow() - timedelta(minutes=25),
        "metadata": {"param1": "value1"},
        "result": {"output": "success"},
        "error": None
    }
    
    # Mock the task manager
    with patch.object(task_manager, 'get_task_status', return_value=test_task):
        response = test_client.get("/api/v1/tasks/test-task-124?include_result=true")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["task_id"] == "test-task-124"
        assert data["result"] == {"output": "success"}  # Result should be included


def test_get_task_status_not_found(test_client):
    """Test getting the status of a non-existent task."""
    # Mock the task manager to return None (task not found)
    with patch.object(task_manager, 'get_task_status', return_value=None):
        response = test_client.get("/api/v1/tasks/nonexistent-task")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()


def test_list_tasks(test_client):
    """Test listing tasks with filters."""
    # Create test tasks
    now = datetime.utcnow()
    test_tasks = [
        {
            "task_id": f"test-task-{i}",
            "type": "test_task",
            "status": "completed",
            "created_at": now - timedelta(minutes=30 - i),
            "started_at": now - timedelta(minutes=29 - i),
            "completed_at": now - timedelta(minutes=25 - i),
            "metadata": {"param1": f"value{i}"},
            "result": {"output": f"success-{i}"},
            "error": None
        }
        for i in range(5)
    ]
    
    # Add a failed task
    test_tasks.append({
        "task_id": "failed-task-1",
        "type": "test_task_fail",
        "status": "failed",
        "created_at": now - timedelta(minutes=10),
        "started_at": now - timedelta(minutes=9),
        "completed_at": now - timedelta(minutes=8),
        "metadata": {"param1": "fail"},
        "result": None,
        "error": "Something went wrong"
    })
    
    # Mock the task manager
    with patch.object(task_manager, 'tasks', {t["task_id"]: t for t in test_tasks}), \
         patch.object(task_manager, 'get_task_status', side_effect=lambda x: task_manager.tasks.get(x)):
        
        # Test without filters
        response = client.get("/api/v1/tasks")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 6  # All tasks should be returned
        
        # Test with status filter
        response = test_client.get("/api/v1/tasks?status=completed")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert all(t["status"] == "completed" for t in data)
        
        # Test with task_type filter
        response = test_client.get("/api/v1/tasks?task_type=test_task_fail")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["task_id"] == "failed-task-1"
        
        # Test with limit
        response = test_client.get("/api/v1/tasks?limit=2")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        
        # Test with days filter (should still return all since they're recent)
        response = test_client.get("/api/v1/tasks?days=1")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 6


def test_list_tasks_cleanup(test_client, task_manager):
    """Test that old tasks are cleaned up when listing."""
    # Create an old task
    old_task = {
        "task_id": "old-task-1",
        "type": "old_task",
        "status": "completed",
        "created_at": datetime.utcnow() - timedelta(days=31),  # Older than default 30 days
        "started_at": None,
        "completed_at": None,
        "metadata": {},
        "result": None,
        "error": None
    }
    
    # Mock the task manager
    with patch.object(task_manager, 'tasks', {"old-task-1": old_task}), \
         patch.object(task_manager, 'get_task_status', side_effect=lambda x: task_manager.tasks.get(x)) as mock_get_task, \
         patch.object(task_manager, 'cleanup_old_tasks') as mock_cleanup:
        
        # This should trigger cleanup
        response = client.get("/api/v1/tasks")
        
        # Check that cleanup was called
        mock_cleanup.assert_called_once()
        
        # The old task should not be returned
        data = response.json()
        assert len(data) == 0
