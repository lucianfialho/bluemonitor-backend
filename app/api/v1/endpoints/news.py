"""News endpoints."""
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import mongodb_manager
from app.services.news.collector import news_collector
from app.core.config import settings

router = APIRouter()


@router.get("")
async def list_news(
    skip: int = 0,
    limit: int = 10,
    country: Optional[str] = None,
    source: Optional[str] = None,
    db: AsyncIOMotorDatabase = Depends(mongodb_manager.get_db),
) -> dict[str, Any]:
    """List all news articles with pagination and optional filters.
    
    Args:
        skip: Number of items to skip.
        limit: Maximum number of items to return.
        country: Filter by country (e.g., 'BR' for Brazil).
        source: Filter by news source.
        db: Database connection.
        
    Returns:
        List of news articles with pagination metadata.
    """
    query = {}
    if country:
        query["country_focus"] = country.upper()
    if source:
        query["source_name"] = source

    cursor = db.news.find(query).sort("publish_date", -1).skip(skip).limit(limit)
    total = await db.news.count_documents(query)
    news_items = await cursor.to_list(length=limit)

    return {
        "data": news_items,
        "pagination": {
            "total": total,
            "skip": skip,
            "limit": limit,
        },
    }


@router.get("/{news_id}")
async def get_news(
    news_id: str,
    db: AsyncIOMotorDatabase = Depends(mongodb_manager.get_db),
) -> dict[str, Any]:
    """Get a single news article by ID.
    
    Args:
        news_id: The ID of the news article to retrieve.
        db: Database connection.
        
    Returns:
        The requested news article.
        
    Raises:
        HTTPException: If the news article is not found.
    """
    news_item = await db.news.find_one({"_id": news_id})
    if not news_item:
        raise HTTPException(
            status_code=404, detail=f"News article with ID {news_id} not found"
        )
    
    return news_item

@router.post("/collect")
async def collect_news(
    background_tasks: BackgroundTasks,
    query: Optional[str] = None,
    country: str = 'BR'
) -> dict[str, str]:
    """Trigger a manual news collection.
    
    Args:
        background_tasks: FastAPI background tasks manager.
        query: Optional search query. If not provided, uses default queries.
        country: Country code (default: 'BR' for Brazil).
        
    Returns:
        Confirmation message.
    """
    async def _process_collection():
        try:
            if query:
                await news_collector.process_news_batch(query, country)
            else:
                # Use default queries if none provided
                for q in ["autismo Brasil", "TEA Brasil", "transtorno do espectro autista"]:
                    await news_collector.process_news_batch(q, country)
        except Exception as e:
            logger.error(f"Error in manual news collection: {str(e)}", exc_info=True)
    
    # Run in background to avoid timeout
    background_tasks.add_task(_process_collection)
    
    return {"message": "News collection started in the background. Check logs for progress."}
