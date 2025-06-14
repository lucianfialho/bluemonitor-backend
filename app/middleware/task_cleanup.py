"""Middleware for cleaning up old tasks."""
import asyncio
from datetime import timedelta
import logging
from typing import Callable, Awaitable, Optional, Dict, Any

from fastapi import Request, Response
from starlette.types import ASGIApp, Scope, Receive, Send

from app.core.config import settings
from app.services.task_manager import task_manager

logger = logging.getLogger(__name__)

class TaskCleanupMiddleware:
    """Middleware to clean up old completed/failed tasks."""
    
    def __init__(
        self,
        app: ASGIApp,
        cleanup_interval: int = 3600,  # 1 hour in seconds
        max_task_age_days: int = 7
    ) -> None:
        """Initialize the middleware.
        
        Args:
            app: The FastAPI application.
            cleanup_interval: How often to run cleanup, in seconds.
            max_task_age_days: Maximum age of tasks to keep.
        """
        self.app = app
        self.cleanup_interval = cleanup_interval
        self.max_task_age_days = max_task_age_days
        self.cleanup_task: Optional[asyncio.Task] = None
    
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Handle the request and start the cleanup task if not already running."""
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        
        # Start cleanup task on first request
        if self.cleanup_task is None:
            self.cleanup_task = asyncio.create_task(self._periodic_cleanup())
        
        # Forward the request to the next middleware/app
        await self.app(scope, receive, send)
    
    async def _periodic_cleanup(self) -> None:
        """Periodically clean up old tasks."""
        while True:
            try:
                # Clean up tasks older than max_task_age_days
                removed = task_manager.cleanup_old_tasks(days=self.max_task_age_days)
                if removed > 0:
                    logger.info(f"Cleaned up {removed} old tasks")
                
            except Exception as e:
                logger.error(f"Error cleaning up tasks: {e}", exc_info=True)
            
            # Wait for the next cleanup interval
            await asyncio.sleep(self.cleanup_interval)

async def setup_task_cleanup(app: ASGIApp) -> None:
    """Set up the task cleanup middleware."""
    # Get configuration from settings
    cleanup_interval = getattr(settings, "TASK_CLEANUP_INTERVAL", 3600)
    max_task_age_days = getattr(settings, "TASK_RETENTION_DAYS", 7)
    
    # Convert to int if they're strings (from environment variables)
    cleanup_interval = int(cleanup_interval) if cleanup_interval else 3600
    max_task_age_days = int(max_task_age_days) if max_task_age_days else 7
    
    logger.info(
        f"Setting up task cleanup: interval={cleanup_interval}s, "
        f"retention={max_task_age_days} days"
    )
    
    # Add the middleware
    app.add_middleware(
        TaskCleanupMiddleware,
        cleanup_interval=cleanup_interval,
        max_task_age_days=max_task_age_days
    )
    yield
    # Cleanup on shutdown if needed
