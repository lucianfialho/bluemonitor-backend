"""Task management service for background tasks."""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import uuid

class TaskManager:
    """Manages background tasks and their status."""
    
    def __init__(self):
        """Initialize the task manager with an empty tasks dictionary."""
        self.tasks: Dict[str, Dict[str, Any]] = {}
    
    def create_task(self, task_type: str, metadata: Optional[dict] = None) -> str:
        """Create a new task and return its ID.
        
        Args:
            task_type: Type of the task (e.g., 'news_collection').
            metadata: Additional metadata for the task.
            
        Returns:
            str: The generated task ID.
        """
        task_id = str(uuid.uuid4())
        self.tasks[task_id] = {
            'task_id': task_id,
            'type': task_type,
            'status': 'pending',
            'created_at': datetime.utcnow(),
            'started_at': None,
            'completed_at': None,
            'metadata': metadata or {},
            'result': None,
            'error': None
        }
        return task_id
    
    def start_task(self, task_id: str) -> bool:
        """Mark a task as started.
        
        Args:
            task_id: ID of the task to start.
            
        Returns:
            bool: True if the task was found and updated, False otherwise.
        """
        if task_id not in self.tasks:
            return False
            
        task = self.tasks[task_id]
        
        # Don't start if already in progress or completed
        if task['status'] in ['processing', 'completed', 'failed']:
            return False
            
        task.update({
            'status': 'processing',
            'started_at': datetime.utcnow(),
            'completed_at': None,
            'error': None
        })
        return True
    
    def complete_task(self, task_id: str, result: Any = None) -> bool:
        """Mark a task as completed.
        
        Args:
            task_id: ID of the task to complete.
            result: Optional result of the task.
            
        Returns:
            bool: True if the task was found and updated, False otherwise.
        """
        if task_id not in self.tasks:
            return False
            
        task = self.tasks[task_id]
        
        # Don't complete if already completed or failed
        if task['status'] in ['completed', 'failed']:
            return False
            
        task.update({
            'status': 'completed',
            'completed_at': datetime.utcnow(),
            'result': result,
            'error': None
        })
        return True
    
    def fail_task(self, task_id: str, error: Exception) -> bool:
        """Mark a task as failed.
        
        Args:
            task_id: ID of the task that failed.
            error: The exception that caused the failure.
            
        Returns:
            bool: True if the task was found and updated, False otherwise.
        """
        if task_id in self.tasks:
            self.tasks[task_id].update({
                'status': 'failed',
                'completed_at': datetime.utcnow(),
                'error': str(error)
            })
            return True
        return False
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a task.
        
        Args:
            task_id: ID of the task to check.
            
        Returns:
            Optional[Dict[str, Any]]: Task status information, or None if not found.
        """
        task = self.tasks.get(task_id)
        if task:
            # Calculate duration if task is in progress
            if task['status'] == 'processing' and task['started_at']:
                duration = (datetime.utcnow() - task['started_at']).total_seconds()
                task['duration_seconds'] = duration
            
            # Calculate duration if task is completed
            if task['status'] in ['completed', 'failed'] and task['started_at'] and task['completed_at']:
                duration = (task['completed_at'] - task['started_at']).total_seconds()
                task['duration_seconds'] = duration
            
            return task
        return None
    
    def cleanup_old_tasks(self, days: int = 7) -> int:
        """Remove tasks older than the specified number of days.
        
        Args:
            days: Number of days to keep tasks.
            
        Returns:
            int: Number of tasks removed.
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        initial_count = len(self.tasks)
        
        # Remove tasks that are completed or failed and older than cutoff
        # Only consider tasks that have a completed_at timestamp
        self.tasks = {
            task_id: task for task_id, task in self.tasks.items()
            if task['status'] not in ['completed', 'failed'] or 
               (task['completed_at'] and task['completed_at'] > cutoff)
        }
        
        # Also clean up any tasks that are too old based on created_at
        # This is a safety net for tasks that might not have been properly completed
        initial_count_after_first_pass = len(self.tasks)
        self.tasks = {
            task_id: task for task_id, task in self.tasks.items()
            if task['created_at'] > cutoff
        }
        
        return initial_count - len(self.tasks)
    
    def get_task_statistics(self) -> Dict[str, Any]:
        """Get statistics about the tasks in the task manager.
        
        Returns:
            dict: A dictionary containing task statistics.
        """
        stats = {
            'total': len(self.tasks),
            'by_status': {},
            'by_type': {}
        }
        
        # Count tasks by status and type
        for task in self.tasks.values():
            # Count by status
            status = task.get('status', 'unknown')
            stats['by_status'][status] = stats['by_status'].get(status, 0) + 1
            
            # Count by type
            task_type = task.get('type', 'unknown')
            stats['by_type'][task_type] = stats['by_type'].get(task_type, 0) + 1
        
        # Calculate success rate for completed tasks
        completed = stats['by_status'].get('completed', 0)
        failed = stats['by_status'].get('failed', 0)
        total_completed = completed + failed
        
        if total_completed > 0:
            stats['success_rate'] = (completed / total_completed) * 100
        else:
            stats['success_rate'] = 0.0
        
        # Add timestamps for the statistics
        stats['timestamp'] = datetime.utcnow().isoformat()
        
        return stats

# Create a singleton instance
task_manager = TaskManager()
