"""Tests for the tasks API endpoints."""
import pytest
from fastapi import status
from httpx import AsyncClient

from app.services.task_manager import task_manager

@pytest.mark.asyncio
async def test_get_task_status(client: AsyncClient):
    """Test getting the status of a task."""
    # Create a test task
    task_id = task_manager.create_task("test_task", {"test": "data"})
    task_manager.start_task(task_id)
    
    # Get the task status
    response = await client.get(f"/api/v1/tasks/{task_id}")
    assert response.status_code == status.HTTP_200_OK
    
    data = response.json()
    assert data["task_id"] == task_id
    assert data["type"] == "test_task"
    assert data["status"] == "processing"
    assert data["metadata"]["test"] == "data"
    assert "created_at" in data
    assert "started_at" in data
    
    # Test with include_result=True
    result = {"items_processed": 5}
    task_manager.complete_task(task_id, result)
    
    response = await client.get(f"/api/v1/tasks/{task_id}?include_result=true")
    assert response.status_code == status.HTTP_200_OK
    
    data = response.json()
    assert data["status"] == "completed"
    assert data["result"] == result
    assert "completed_at" in data
    assert "duration_seconds" in data

@pytest.mark.asyncio
async def test_get_nonexistent_task(client: AsyncClient):
    """Test getting a task that doesn't exist."""
    response = await client.get("/api/v1/tasks/nonexistent-task-id")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    
    data = response.json()
    assert data["detail"] == "Task nonexistent-task-id not found"

@pytest.mark.asyncio
async def test_list_tasks(client: AsyncClient):
    """Test listing tasks with filters."""
    # Clear any existing tasks
    task_manager.tasks.clear()
    
    # Create some test tasks
    task1 = task_manager.create_task("test_task_1", {"source": "test"})
    task_manager.start_task(task1)
    
    task2 = task_manager.create_task("test_task_2", {"source": "test"})
    task_manager.start_task(task2)
    task_manager.complete_task(task2, {"items": 10})
    
    task3 = task_manager.create_task("other_task", {"source": "other"})
    task_manager.start_task(task3)
    task_manager.fail_task(task3, Exception("Test error"))
    
    # Get all tasks
    response = await client.get("/api/v1/tasks/")
    assert response.status_code == status.HTTP_200_OK
    
    tasks = response.json()
    assert len(tasks) >= 3  # There might be other tasks from other tests
    
    # Filter by status
    response = await client.get("/api/v1/tasks/?status=completed")
    assert response.status_code == status.HTTP_200_OK
    
    completed_tasks = response.json()
    assert len(completed_tasks) >= 1
    assert all(t["status"] == "completed" for t in completed_tasks)
    
    # Filter by task type
    response = await client.get("/api/v1/tasks/?task_type=test_task_1")
    assert response.status_code == status.HTTP_200_OK
    
    filtered_tasks = response.json()
    assert len(filtered_tasks) >= 1
    assert all(t["type"] == "test_task_1" for t in filtered_tasks)
    
    # Test pagination
    response = await client.get("/api/v1/tasks/?limit=1")
    assert response.status_code == status.HTTP_200_OK
    
    paginated_tasks = response.json()
    assert len(paginated_tasks) == 1

@pytest.mark.asyncio
async def test_news_collection_endpoint(client: AsyncClient):
    """Test the news collection endpoint."""
    # Test with a query
    response = await client.post(
        "/api/v1/news/collect",
        json={"query": "autismo", "country": "BR"}
    )
    
    assert response.status_code == status.HTTP_202_ACCEPTED
    data = response.json()
    
    assert "task_id" in data
    assert data["status"] == "processing"
    assert data["country"] == "BR"
    
    # Test without a query (should use default queries)
    response = await client.post("/api/v1/news/collect")
    assert response.status_code == status.HTTP_202_ACCEPTED
    
    data = response.json()
    assert "task_id" in data
    assert data["status"] == "processing"
    
    # Test with an invalid country (should still accept but might fail later)
    response = await client.post(
        "/api/v1/news/collect",
        json={"country": "INVALID"}
    )
    assert response.status_code == status.HTTP_202_ACCEPTED
