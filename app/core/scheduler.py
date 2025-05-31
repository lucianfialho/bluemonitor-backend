"""Scheduler configuration and task management."""
import logging
from typing import Any, Callable, Coroutine, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import settings

logger = logging.getLogger(__name__)

class Scheduler:
    """Scheduler manager for background tasks."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Scheduler, cls).__new__(cls)
            cls._instance._scheduler = AsyncIOScheduler()
        return cls._instance
    
    @property
    def scheduler(self) -> AsyncIOScheduler:
        """Get the scheduler instance."""
        return self._scheduler
    
    def add_job(
        self,
        func: Callable[..., Coroutine[Any, Any, None]],
        trigger: str,
        id: Optional[str] = None,
        **trigger_args
    ) -> None:
        """Add a job to the scheduler.
        
        Args:
            func: The coroutine function to run.
            trigger: The trigger type ('interval', 'cron', 'date').
            id: Optional job ID. If not provided, uses the function name.
            **trigger_args: Arguments for the trigger.
        """
        job_id = id or func.__name__
        
        if trigger == 'interval':
            # Remove any trigger-specific args that might be passed in
            trigger_kwargs = trigger_args.copy()
            if 'id' in trigger_kwargs:
                del trigger_kwargs['id']
            if 'replace_existing' in trigger_kwargs:
                del trigger_kwargs['replace_existing']
                
            trigger = IntervalTrigger(**trigger_kwargs)
        
        self._scheduler.add_job(
            func,
            trigger=trigger,
            id=job_id,
            replace_existing=True,
        )
        logger.info(f"Added job {func.__name__} with trigger {trigger}")
    
    def start(self) -> None:
        """Start the scheduler."""
        if not self._scheduler.running:
            self._scheduler.start()
            logger.info("Scheduler started")
    
    def shutdown(self) -> None:
        """Shutdown the scheduler."""
        if self._scheduler.running:
            self._scheduler.shutdown()
            logger.info("Scheduler stopped")

# Create a singleton instance
scheduler = Scheduler()
