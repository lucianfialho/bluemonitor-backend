"""Topics endpoints."""
import logging
import uuid
from typing import Any, AsyncGenerator, Dict, List, Optional, Union
from bson import ObjectId, errors
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, Request, status, Path, Body
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import MongoDBManager
from app.api.v1.utils import convert_objectid_to_str
from app.services.ai.topic_cluster import topic_cluster
from app.schemas.topics import TopicResponse, TopicListResponse

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()

# Dependência para obter conexão com o banco de dados
async def get_db(request: Request) -> AsyncGenerator[AsyncIOMotorDatabase, None]:
    """Dependency that provides a database connection for the request."""
    mongodb_manager = request.app.state.mongodb_manager
    
    # Garante que a conexão está ativa
    try:
        await mongodb_manager.connect_to_mongodb()
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to connect to database"
        )
    
    # Verifica se o banco de dados está acessível
    try:
        # Tenta listar as coleções para verificar a conexão
        await mongodb_manager.db.list_collection_names()
        yield mongodb_manager.db
    except Exception as e:
        logger.error(f"Database operation failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database operation failed"
        )
    finally:
        # Fecha a conexão após o uso
        await mongodb_manager.close_mongodb_connection()

@router.get("", response_model=TopicListResponse)
async def list_topics(
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db),
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(10, le=100, description="Maximum number of items to return (max 100)"),
    country: Optional[str] = Query(None, description="Filter by country code (e.g., 'BR' for Brazil)"),
    category: Optional[str] = Query(None, description="Filter by category name"),
    min_articles: Optional[int] = Query(None, ge=1, description="Minimum number of articles in topic"),
    max_articles: Optional[int] = Query(None, ge=1, description="Maximum number of articles in topic"),
    sort_by: str = Query("updated_at", description="Field to sort by (created_at, updated_at, article_count)"),
    sort_order: str = Query("desc", description="Sort order (asc or desc)")
) -> TopicListResponse:
    """List all topics with pagination and filtering options.
    
    Args:
        request: FastAPI request object.
        db: Async database connection.
        skip: Number of items to skip.
        limit: Maximum number of items to return.
        country: Filter by country (e.g., 'BR' for Brazil).
        category: Filter by category name.
        min_articles: Minimum number of articles in topic.
        max_articles: Maximum number of articles in topic.
        sort_by: Field to sort results by.
        sort_order: Sort order (asc or desc).
        
    Returns:
        TopicListResponse with paginated topics and metadata.
        
    Raises:
        HTTPException: If an error occurs while retrieving topics.
    """
    try:
        # Build the query
        query = {"is_active": True}  # Only show active topics by default
        
        # Apply filters
        if country:
            query["country_focus"] = country.upper()
            
        if category:
            query["category"] = category
            
        if min_articles is not None:
            query["article_count"] = {"$gte": min_articles}
            
        if max_articles is not None:
            if "article_count" in query:
                query["article_count"]["$lte"] = max_articles
            else:
                query["article_count"] = {"$lte": max_articles}
        
        # Validate sort fields
        valid_sort_fields = {"created_at", "updated_at", "last_updated", "article_count", "first_seen"}
        sort_field = sort_by if sort_by in valid_sort_fields else "updated_at"
        sort_order_int = -1 if sort_order.lower() == "desc" else 1
        
        # Get total count for pagination
        total = await db.topics.count_documents(query)
        
        # Build sort criteria
        sort_criteria = [(sort_field, sort_order_int)]
        
        # Get paginated results
        cursor = db.topics.find(query).sort(sort_criteria).skip(skip).limit(limit)
        topics = await cursor.to_list(length=limit)
        
        # Convert ObjectId to string for JSON serialization
        topics = [convert_objectid_to_str(topic) for topic in topics]

        # Calculate pagination metadata
        has_more = (skip + limit) < total
        next_skip = skip + limit if has_more else None

        return TopicListResponse(
            data=topics,
            pagination={
                "total": total,
                "skip": skip,
                "limit": limit,
                "has_more": has_more,
                "next_skip": next_skip
            }
        )
    except Exception as e:
        error_id = str(uuid.uuid4())
        logger.error(f"Error listing topics (ID: {error_id}): {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_server_error",
                "message": "An error occurred while retrieving topics.",
                "error_id": error_id,
                "suggestion": "Please try again later or contact support if the issue persists.",
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.get(
    "/{topic_id}",
    response_model=dict[str, Any],
    responses={
        200: {
            "description": "Topic retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": "507f1f77bcf86cd799439011",
                        "name": "Autism Research",
                        "description": "Latest research and developments in autism",
                        "keywords": ["autism", "research", "studies"],
                        "article_count": 5,
                        "last_updated_at": "2023-01-01T12:00:00Z",
                        "country_focus": "BR",
                        "news_articles": [
                            {
                                "id": "507f1f77bcf86cd799439012",
                                "title": "New Study on Autism",
                                "url": "https://example.com/news/autism-study"
                            }
                        ]
                    }
                }
            }
        },
        400: {
            "description": "Invalid topic ID format",
            "content": {
                "application/json": {
                    "example": {
                        "error": "invalid_id_format",
                        "message": "Invalid topic ID format: invalid_id",
                        "suggestion": "Ensure the ID is a valid 24-character hex string"
                    }
                }
            }
        },
        404: {
            "description": "Topic not found",
            "content": {
                "application/json": {
                    "example": {
                        "error": "not_found",
                        "message": "Topic with ID 507f1f77bcf86cd799439011 not found",
                        "suggestion": "Check the ID or try another topic"
                    }
                }
            }
        },
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "example": {
                        "error": "internal_server_error",
                        "message": "An error occurred while retrieving the topic.",
                        "error_id": "550e8400-e29b-41d4-a716-446655440000",
                        "suggestion": "Please try again later or contact support if the issue persists.",
                        "timestamp": "2023-01-01T12:00:00Z"
                    }
                }
            }
        }
    }
)
async def get_topic(
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db),
    topic_id: str = Path(..., description="The ID of the topic to retrieve"),
    include_articles: bool = Query(True, description="Include associated news articles"),
    include_article_content: bool = Query(False, description="Include full article content in the response")
) -> TopicResponse:
    """Get a single topic by ID with optional associated news articles.
    
    Args:
        request: FastAPI request object.
        db: Async database connection.
        topic_id: The ID of the topic to retrieve.
        include_articles: Whether to include associated news articles.
        
    Returns:
        The requested topic with optional associated news articles.
        
    Raises:
        HTTPException: If the topic is not found or an error occurs.
    """
    # Validate the topic_id format
    if not ObjectId.is_valid(topic_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_id_format",
                "message": f"Invalid topic ID format: {topic_id}",
                "suggestion": "Ensure the ID is a valid 24-character hex string"
            }
        )
    
    try:
        obj_id = ObjectId(topic_id)
        
        # Find the topic by ID
        topic = await db.topics.find_one({"_id": obj_id})
        
        if not topic:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "not_found",
                    "message": f"Topic with ID {topic_id} not found",
                    "suggestion": "Check the ID or try another topic",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        # Convert ObjectId to string for JSON serialization
        topic = convert_objectid_to_str(topic)
        
        # Get associated news articles if requested and they exist
        news_articles = []
        if include_articles and "articles" in topic and topic["articles"]:
            try:
                logger.debug(f"Fetching news articles for topic {topic_id}")
                
                # Convert string IDs to ObjectId for the query
                news_ids = [ObjectId(id_str) for id_str in topic["articles"] if ObjectId.is_valid(id_str)]
                
                if news_ids:  # Only query if we have valid IDs
                    # Execute the query with projection to get only needed fields
                    news_cursor = db.news.find(
                        {"_id": {"$in": news_ids}},
                        {
                            "title": 1,
                            "url": 1,
                            "published_at": 1,
                            "source": 1,
                            "image": 1
                        }
                    )
                    
                    # Get articles and convert to list
                    news_articles = await news_cursor.to_list(length=100)
                    
                    # Convert ObjectIds in news articles to strings
                    news_articles = [convert_objectid_to_str(article) for article in news_articles]
                    
                    logger.debug(f"Found {len(news_articles)} news articles for topic {topic_id}")
                
            except Exception as e:
                # Log the error but don't fail the request
                logger.error(f"Error fetching related news for topic {topic_id}: {str(e)}", exc_info=True)
        
        # Return the topic with articles if any
        result = {**topic}
        if include_articles:
            result["news_articles"] = news_articles
            
        return result
            
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
        
    except Exception as e:
        error_id = str(uuid.uuid4())
        logger.error(f"Error retrieving topic {topic_id} (ID: {error_id}): {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_server_error",
                "message": "An error occurred while retrieving the topic.",
                "error_id": error_id,
                "suggestion": "Please try again later or contact support if the issue persists.",
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.post(
    "/cluster",
    response_model=dict[str, str],
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        202: {
            "description": "Topic clustering started",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Topic clustering started in the background. This may take a few minutes.",
                        "task_id": "550e8400-e29b-41d4-a716-446655440000"
                    }
                }
            }
        },
        500: {
            "description": "Error starting topic clustering",
            "content": {
                "application/json": {
                    "example": {
                        "error": "clustering_error",
                        "message": "Failed to start topic clustering",
                        "error_id": "123e4567-e89b-12d3-a456-426614174000",
                        "suggestion": "Please try again later or check the logs for more details.",
                        "timestamp": "2023-01-01T12:00:00Z"
                    }
                }
            }
        }
    }
)
async def cluster_topics(
    request: Request,
    background_tasks: BackgroundTasks,
    country: str = 'BR',
    force_update: bool = Query(
        False,
        description="Force reclustering even if recent clustering was performed"
    )
) -> dict[str, str]:
    """Trigger manual topic clustering for news articles.
    
    This endpoint starts an asynchronous task to cluster recent news articles into topics.
    The clustering process runs in the background and may take several minutes to complete.
    
    Args:
        request: FastAPI request object.
        background_tasks: FastAPI background tasks manager.
        country: Country code to cluster topics for (default: 'BR').
        force_update: Whether to force reclustering even if recent clustering was performed.
        
    Returns:
        A confirmation message and task ID.
        
    Raises:
        HTTPException: If there's an error starting the clustering process.
    """
    try:
        # Generate a unique task ID for tracking
        task_id = str(uuid.uuid4())
        
        # Log the clustering request
        logger.info(f"Starting topic clustering task {task_id} for country {country}")
        
        # Define the background task
        async def _run_clustering():
            try:
                await topic_cluster.cluster_recent_news(country, force_update=force_update)
                logger.info(f"Completed topic clustering task {task_id} for country {country}")
            except Exception as e:
                logger.error(
                    f"Error in topic clustering task {task_id} for country {country}: {str(e)}",
                    exc_info=True
                )
        
        # Add the task to run in the background
        background_tasks.add_task(_run_clustering)
        
        # Return a response immediately
        return {
            "message": "Topic clustering started in the background. This may take a few minutes.",
            "task_id": task_id,
            "status": "processing",
            "country": country,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        error_id = str(uuid.uuid4())
        logger.error(
            f"Error starting topic clustering (ID: {error_id}): {str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "clustering_error",
                "message": "Failed to start topic clustering",
                "error_id": error_id,
                "suggestion": "Please try again later or check the logs for more details.",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
