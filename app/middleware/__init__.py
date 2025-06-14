"""Middleware package for the application."""

# This file makes the middleware directory a Python package
# and can be used to expose middleware components for easier importing.

# Import middleware components to make them available when importing from app.middleware
from .task_cleanup import TaskCleanupMiddleware, setup_task_cleanup  # noqa: F401
