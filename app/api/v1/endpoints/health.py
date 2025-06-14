"""Health check endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from starlette import status
from typing import Dict, Any

from app.services.task_manager import task_manager

router = APIRouter()


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> Dict[str, str]:
    """Basic health check endpoint.
    
    Returns:
        dict: Status message indicating the service is running.
    """
    return {"status": "ok"}


@router.get("/health/tasks", status_code=status.HTTP_200_OK)
async def health_check_tasks() -> Dict[str, Any]:
    """Check the health of the task manager.
    
    Returns:
        dict: Status and statistics about the task manager.
    """
    try:
        # Get task statistics
        stats = task_manager.get_task_statistics()
        
        # Check if there are any long-running tasks
        long_running = any(
            task.get("status") == "processing" 
            for task in task_manager.tasks.values()
        )
        
        return {
            "status": "ok",
            "task_manager": "operational",
            "task_count": stats["total"],
            "tasks_by_status": stats["by_status"],
            "has_long_running_tasks": long_running
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Task manager is not available: {str(e)}"
        )
