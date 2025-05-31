"""Topics endpoints."""
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import mongodb_manager

router = APIRouter()


@router.get("")
async def list_topics(
    skip: int = 0,
    limit: int = 10,
    country: Optional[str] = None,
    db: AsyncIOMotorDatabase = Depends(mongodb_manager.get_db),
) -> dict[str, Any]:
    """List all topics with pagination and optional country filter.
    
    Args:
        skip: Number of items to skip.
        limit: Maximum number of items to return.
        country: Filter by country (e.g., 'BR' for Brazil).
        db: Database connection.
        
    Returns:
        List of topics with pagination metadata.
    """
    query = {}
    if country:
        query["country_focus"] = country.upper()

    cursor = db.topics.find(query).sort("last_updated_at", -1).skip(skip).limit(limit)
    total = await db.topics.count_documents(query)
    topics = await cursor.to_list(length=limit)

    return {
        "data": topics,
        "pagination": {
            "total": total,
            "skip": skip,
            "limit": limit,
        },
    }


@router.get("/{topic_id}")
async def get_topic(
    topic_id: str,
    db: AsyncIOMotorDatabase = Depends(mongodb_manager.get_db),
) -> dict[str, Any]:
    """Get a single topic by ID.
    
    Args:
        topic_id: The ID of the topic to retrieve.
        db: Database connection.
        
    Returns:
        The requested topic with its associated news articles.
        
    Raises:
        HTTPException: If the topic is not found.
    """
    topic = await db.topics.find_one({"_id": topic_id})
    if not topic:
        raise HTTPException(
            status_code=404, detail=f"Topic with ID {topic_id} not found"
        )
    
    # Get associated news articles
    news_articles = []
    if "news_articles_ids" in topic:
        news_cursor = db.news.find({"_id": {"$in": topic["news_articles_ids"]}})
        news_articles = await news_cursor.to_list(length=100)
    
    return {
        **topic,
        "news_articles": news_articles,
    }
