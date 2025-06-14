"""Task management endpoints."""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse

from app.services.task_manager import task_manager
from app.core.config import settings

router = APIRouter(tags=["tasks"])

@router.get("/{task_id}", response_model=Dict[str, Any])
async def get_task_status(
    task_id: str,
    include_result: bool = Query(False, description="Include task result in response")
) -> Dict[str, Any]:
    """Get the status of a background task.
    
    Args:
        task_id: The ID of the task to check.
        include_result: Whether to include the task result in the response.
        
    Returns:
        dict: Task status and metadata.
        
    Raises:
        HTTPException: If the task is not found.
    """
    task = task_manager.get_task_status(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found"
        )
    
    # Remove result if not requested
    if not include_result and 'result' in task:
        task = task.copy()
        task['result'] = "[hidden]" if task.get('result') is not None else None
    
    return task

@router.get("", response_model=List[Dict[str, Any]])
async def list_tasks(
    status: Optional[str] = Query(None, description="Filter by status (pending, processing, completed, failed)"),
    task_type: Optional[str] = Query(None, description="Filter by task type"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of tasks to return"),
    days: int = Query(7, ge=1, description="Only include tasks from the last N days")
) -> List[Dict[str, Any]]:
    """List all tasks with optional filtering.
    
    Args:
        status: Filter by task status.
        task_type: Filter by task type.
        limit: Maximum number of tasks to return.
        days: Only include tasks from the last N days.
        
    Returns:
        List of tasks with their status and metadata.
    """
    # Clean up old tasks
    task_manager.cleanup_old_tasks(days=min(days, 30))  # Cap at 30 days for safety
    
    # Get all tasks
    tasks = [
        task_manager.get_task_status(task_id)
        for task_id in list(task_manager.tasks.keys())[:limit]
    ]
    
    # Apply filters
    if status:
        tasks = [t for t in tasks if t and t.get('status') == status]
    if task_type:
        tasks = [t for t in tasks if t and t.get('type') == task_type]
    
    # Sort by creation time (newest first)
    tasks = sorted(
        [t for t in tasks if t],
        key=lambda x: x.get('created_at', datetime.min),
        reverse=True
    )
    
    return tasks[:limit]

# This router will be included in the main router with the /tasks prefix
