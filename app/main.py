"""Main FastAPI application module."""
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.core.config import settings
from app.core.database import mongodb_manager
from app.core.logging import configure_logging
from app.core.scheduler import scheduler
from app.tasks import setup_scheduled_tasks
from app.api.v1.router import api_router

# Configure logging
configure_logging()

# Get logger
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    """
    Handle application startup and shutdown events.
    
    This context manager ensures that database connections are properly
    established when the application starts and closed when it shuts down.
    """
    # Startup: Connect to MongoDB
    logger.info("Starting application...")
    await mongodb_manager.connect_to_mongodb()
    logger.info("Connected to MongoDB")
    
    # Initialize and start the scheduler
    setup_scheduled_tasks()
    scheduler.start()
    logger.info("Scheduler started")
    
    try:
        yield
    finally:
        # Shutdown: Stop the scheduler and close MongoDB connection
        logger.info("Shutting down application...")
        scheduler.shutdown()
        logger.info("Scheduler stopped")
        await mongodb_manager.close_mongodb_connection()
        logger.info("Disconnected from MongoDB")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description="Backend API for BlueMonitor - A platform for tracking autism-related news in Brazil",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# Set up CORS
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include API routers
app.include_router(api_router, prefix=settings.API_V1_STR)

# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle request validation errors."""
    logger.error("Validation error", exc_info=exc)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors(), "body": exc.body},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle global exceptions."""
    logger.error("Unhandled exception", exc_info=exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


# Health check endpoint
@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


# Root endpoint
@app.get("/", tags=["root"])
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "message": "Welcome to BlueMonitor API",
        "version": "0.1.0",
        "docs": "/docs",
        "redoc": "/redoc",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.is_development,
        log_level=settings.LOG_LEVEL.lower(),
    )
