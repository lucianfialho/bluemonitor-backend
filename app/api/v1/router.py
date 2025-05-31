"""API v1 router configuration."""
from fastapi import APIRouter

from app.api.v1.endpoints import health_router, topics_router, news_router

# Create the API router
api_router = APIRouter()

# Include endpoints
api_router.include_router(health_router, tags=["health"])
api_router.include_router(topics_router, prefix="/topics", tags=["topics"])
api_router.include_router(news_router, prefix="/news", tags=["news"])
