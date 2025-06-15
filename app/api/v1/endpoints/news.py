"""News endpoints."""
import logging
import json
import re
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, List, Optional, Dict, Union, AsyncGenerator, Set, Generator, Tuple
from contextlib import asynccontextmanager
from enum import Enum
from bson import ObjectId, errors
from app.services.task_manager import task_manager

from app.schemas.navigation import EnhancedNewsResponse, LinkableTerm, NavigationMetadata
from app.services.ai.navigation import navigation_system
from app.services.ai.fact_extraction import fact_extraction_system

from fastapi import (
    APIRouter, 
    Depends, 
    HTTPException, 
    Query, 
    BackgroundTasks, 
    Request, 
    Path,
    status,
    Body,
    Response
)
from fastapi.responses import JSONResponse, Response
from fastapi.background import BackgroundTasks
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING, ReturnDocument

from app.services.news.collector import news_collector
from app.core.config import settings
from app.schemas.news import (
    NewsResponse,
    NewsListResponse,
    NewsItemResponse,
    NewsSource,
    NewsImage,
    Sentiment,
    NewsMetrics,
    RelatedNewsItem,
    NewsFilters,
    NewsItemBase
)
from app.api.v1.utils import convert_objectid_to_str

# Configure logging
logger = logging.getLogger(__name__)

# Cache configuration
CACHE_EXPIRE = 300  # 5 minutes

# Constants
DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 100
VALID_SORT_FIELDS = {
    "published_at", "title", "source_name", "created_at", "updated_at"
}

# Router
router = APIRouter()

class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"

# Configure logging
logger = logging.getLogger(__name__)

def convert_objectid_to_str(doc: Any) -> Any:
    """Recursively convert ObjectId and other non-serializable types to string."""
    if doc is None:
        return None
    
    # Handle ObjectId
    if hasattr(doc, '__class__') and doc.__class__.__name__ == 'ObjectId':
        return str(doc)
    
    # Handle datetime
    if hasattr(doc, 'isoformat') and hasattr(doc, 'strftime'):
        return doc.isoformat()
    
    # Handle lists
    if isinstance(doc, list):
        return [convert_objectid_to_str(item) for item in doc]
    
    # Handle dictionaries
    if isinstance(doc, dict):
        result = {}
        for key, value in doc.items():
            result[key] = convert_objectid_to_str(value)
        return result
    
    # Return as is for other types
    return doc

# Dependência para obter conexão com o banco de dados
async def get_db(request: Request) -> Generator[AsyncIOMotorDatabase, None, None]:
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

# Define projection to fetch only necessary fields for list view
NEWS_LIST_PROJECTION = {
    "title": 1,
    "description": 1,
    "url": 1,
    "source_name": 1,
    "source_domain": 1,
    "image_url": 1,
    "favicon_url": 1,
    "published_at": 1,
    "created_at": 1,
    "updated_at": 1,
    "categories": 1,
    "topic_id": 1,
    "topic_category": 1,
    "sentiment": 1,
    "sentiment_score": 1,
    "sentiment_label": 1,
    "keywords": 1,
    "country": 1,
    "language": 1,
    "publish_date": 1,
    "_id": 1,
    "topics": 1,
    "content": 1  # Adicionado para incluir o conteúdo quando necessário
}

def _build_news_query(
    q: Optional[str] = None,
    source: Optional[str] = None,
    category: Optional[str] = None,
    topic_id: Optional[str] = None,
    has_topic: Optional[bool] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    language: Optional[str] = None
) -> Dict[str, Any]:
    """Build MongoDB query for news listing based on filters.
    
    Args:
        q: Search query text
        source: Filter by source name or domain
        category: Filter by category name
        topic_id: Filter by topic ID
        has_topic: Filter by whether article has a topic
        from_date: Filter by publish date (>=)
        to_date: Filter by publish date (<=)
        language: Filter by language code
        
    Returns:
        Dictionary with MongoDB query
    """
    query = {}
    
    # Text search
    if q:
        query["$text"] = {"$search": q}
    
    # Source filter
    if source:
        query["$or"] = [
            {"source_name": {"$regex": source, "$options": "i"}},
            {"source_domain": {"$regex": source, "$options": "i"}}
        ]
    
    # Category filter
    if category:
        query["topic_category"] = {"$regex": f"^{category}$", "$options": "i"}
    
    # Topic filters
    if topic_id:
        try:
            query["topic_id"] = str(topic_id)
        except (errors.InvalidId, TypeError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid topic ID format"
            )
    
    if has_topic is not None:
        if has_topic:
            query["topic_id"] = {"$exists": True, "$ne": None}
        else:
            query["$or"] = [
                {"topic_id": {"$exists": False}},
                {"topic_id": None}
            ]
    
    # Date range filters
    date_filters = {}
    if from_date:
        date_filters["$gte"] = from_date
    if to_date:
        date_filters["$lte"] = to_date
    
    if date_filters:
        query["published_at"] = date_filters
    
    # Language filter
    if language:
        query["language"] = language.lower()
    
    return query

def _format_news_item_light(item: dict, include_content: bool = False) -> dict:
    """Format a news item with minimal fields for list views.
    
    VERSÃO MELHORADA: Mantém performance + adiciona melhorias leves
    """
    from datetime import datetime
    
    # ===== LÓGICA EXISTENTE MANTIDA =====
    now = datetime.utcnow()
    
    # Ensure required fields have proper defaults
    item_id = str(item.get("_id", ""))
    title = item.get("title", "Sem título")
    
    # ✅ MELHORIA 1: Validar URL
    url = item.get("url", "")
    if not url and "original_url" in item:
        url = item["original_url"]
    
    # Validar se URL é válida
    if url == "https://source-not-available.com/" or not (url and url.startswith(("http://", "https://"))):
        url = None
    
    source_name = item.get("source_name", "Fonte desconhecida")
    source_domain = item.get("source_domain", "")
    
    # ✅ MELHORIA 2: Auto-gerar description básica
    description = item.get("description", "")
    auto_generated_desc = False
    if not description and item.get("content") and len(item["content"]) > 50:
        content = item["content"]
        description = content[:150] + "..." if len(content) > 150 else content
        auto_generated_desc = True
    
    # Handle dates (mantido como está)
    published_at = item.get("published_at")
    if isinstance(published_at, str):
        try:
            published_at = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            published_at = now
    
    created_at = item.get("created_at", now)
    if isinstance(created_at, str):
        try:
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            created_at = now
    
    updated_at = item.get("updated_at", created_at)
    if isinstance(updated_at, str):
        try:
            updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            updated_at = created_at
    elif updated_at is None:
        updated_at = created_at
    
    # ✅ MELHORIA 3: Enriquecimento leve para listas
    categories = item.get("categories", [])
    if not categories:
        categories = auto_categorize_news(title, description)[:2]  # Max 2 para listas
    
    # ✅ MELHORIA 4: Sentiment básico
    sentiment = item.get("sentiment")
    if not sentiment:
        sentiment = auto_analyze_sentiment(title, description)
    
    # ✅ MELHORIA 5: Keywords básicas
    keywords = item.get("keywords", [])
    if not keywords:
        keywords = extract_keywords_smart(title, description)[:5]  # Max 5 para listas
    
    # ✅ MELHORIA 6: Source melhorado
    source_id = generate_source_id(source_domain) if source_domain else None
    reliability_score = calculate_source_reliability(source_domain)
    
    # Build the result with proper defaults
    result = {
        "id": str(item.get("_id", "")),
        "title": title,
        "description": description if include_content else "",  # ✅ Melhorada
        "url": url,  # ✅ Validada
        "source": {
            "id": source_id,  # ✅ NOVO
            "name": source_name,
            "domain": source_domain,
            "reliability_score": reliability_score  # ✅ NOVO
        },
        "published_at": published_at,
        "image": {
            "url": str(item["image_url"])
        } if item.get("image_url") else None,
        "categories": categories,  # ✅ Melhorada
        "topic_id": str(item["topic_id"]) if item.get("topic_id") else None,
        "topic_category": item.get("topic_category"),
        "sentiment": sentiment,  # ✅ NOVO
        "keywords": keywords,  # ✅ NOVO
        "topics": item.get("topics", []),
        "language": item.get("language", "pt"),
        "country": item.get("country", "BR"),
        "created_at": created_at,
        "updated_at": updated_at
    }
    
    # ✅ MELHORIA 7: Metadata de qualidade básico
    result["metadata"] = {
        "data_quality_score": calculate_quality_score(result),
        "has_image": bool(item.get("image_url")),
        "has_content": bool(item.get("content")),
        "has_valid_url": bool(url),
        "is_recent": is_article_recent(published_at),
        "auto_generated_description": auto_generated_desc,
        "source_reliability": reliability_score
    }
    
    # Include content if requested (mantido)
    if include_content:
        result["content"] = item.get("content", "")
    
    return result


from fastapi_cache.decorator import cache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache import FastAPICache
from fastapi_cache.coder import PickleCoder

# Configure cache
CACHE_EXPIRE = 300  # 5 minutes

def get_news_list_key_builder(
    func,
    namespace: str = "",
    *,
    request: Request = None,
    response: Response = None,
    **kwargs
) -> str:
    """Generate a unique cache key for the news list endpoint."""
    # Extract query parameters from request
    query_params = request.query_params
    skip = int(query_params.get("skip", 0))
    limit = int(query_params.get("limit", DEFAULT_PAGE_SIZE))
    q = query_params.get("q")
    source = query_params.get("source")
    category = query_params.get("category")
    topic_id = query_params.get("topic_id")
    has_topic = query_params.get("has_topic")
    from_date = query_params.get("from_date")
    to_date = query_params.get("to_date")
    language = query_params.get("language")
    sort_by = query_params.get("sort_by", "published_at")
    sort_order = query_params.get("sort_order", "desc")
    include_content = query_params.get("include_content", "false").lower() == "true"
    
    # Build key parts
    key_parts = [
        f"skip:{skip}",
        f"limit:{limit}",
        f"q:{q}" if q else "",
        f"source:{source}" if source else "",
        f"category:{category}" if category else "",
        f"topic_id:{topic_id}" if topic_id else "",
        f"has_topic:{has_topic}" if has_topic is not None else "",
        f"from_date:{from_date}" if from_date else "",
        f"to_date:{to_date}" if to_date else "",
        f"language:{language}" if language else "",
        f"sort_by:{sort_by}",
        f"sort_order:{sort_order}",
        f"include_content:{include_content}",
    ]
    
    # Join non-empty parts with colons
    key = "news_list:" + ":".join(filter(None, key_parts))
    return key

async def _get_news_list(
    db: AsyncIOMotorDatabase,
    skip: int = 0,
    limit: int = DEFAULT_PAGE_SIZE,
    q: Optional[str] = None,
    source: Optional[str] = None,
    category: Optional[str] = None,
    topic_id: Optional[str] = None,
    has_topic: Optional[bool] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    language: Optional[str] = None,
    sort_by: str = "published_at",
    sort_order: str = "desc",
    include_content: bool = False
) -> Tuple[List[Dict[str, Any]], int]:
    """Internal function to fetch news with pagination and filtering."""
    # Build query
    query = _build_news_query(
        q=q,
        source=source,
        category=category,
        topic_id=topic_id,
        has_topic=has_topic,
        from_date=from_date,
        to_date=to_date,
        language=language
    )
    
    # Get total count
    total = await db.news.count_documents(query)
    
    # Determine sort order
    sort_order_int = -1 if sort_order.lower() == "desc" else 1
    sort_field = [(sort_by, sort_order_int)]
    
    # Add secondary sort on _id for consistent pagination
    if sort_by != "_id":
        sort_field.append(("_id", sort_order_int))
    
    # Fetch paginated results
    cursor = (
        db.news
        .find(query, projection=NEWS_LIST_PROJECTION)
        .sort(sort_field)
        .skip(skip)
        .limit(limit)
    )
    
    # Convert to list and format results
    items = await cursor.to_list(length=limit)
    formatted_items = [
        _format_news_item_light(item, include_content=include_content) for item in items
    ]
    
    return formatted_items, total

@router.get("", response_model=NewsListResponse)
# @cache(
#     expire=CACHE_EXPIRE,
#     key_builder=get_news_list_key_builder,
#     namespace="news",
#     coder=PickleCoder
# )
async def list_news(
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db),
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(DEFAULT_PAGE_SIZE, le=MAX_PAGE_SIZE, 
                      description=f"Maximum number of items to return (max {MAX_PAGE_SIZE})"),
    q: Optional[str] = Query(None, description="Search query"),
    source: Optional[str] = Query(None, description="Filter by source name or domain"),
    category: Optional[str] = Query(None, description="Filter by category"),
    topic_id: Optional[str] = Query(None, description="Filter by topic ID"),
    has_topic: Optional[bool] = Query(None, description="Filter by whether article has a topic"),
    from_date: Optional[datetime] = Query(None, description="Filter by publish date (>="),
    to_date: Optional[datetime] = Query(None, description="Filter by publish date (<="),
    language: Optional[str] = Query(None, description="Filter by language code"),
    sort_by: str = Query("published_at", description="Field to sort by"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"),
    include_content: bool = Query(False, description="Include full article content")
):
    """List news articles with filtering, sorting, and pagination.
    
    This endpoint is cached for 5 minutes to improve performance. The cache key is based on
    all query parameters, so different combinations of filters will be cached separately.
    
    Args:
        request: FastAPI request object
        db: Database connection
        skip: Number of items to skip (pagination)
        limit: Maximum number of items to return (1-100)
        q: Search query (searches in title and content)
        source: Filter by source name or domain
        category: Filter by category name
        topic_id: Filter by topic ID
        has_topic: Filter by whether article has a topic
        from_date: Filter by publish date (>=)
        to_date: Filter by publish date (<=)
        language: Filter by language code
        sort_by: Field to sort by
        sort_order: Sort order (asc/desc)
        include_content: Whether to include full article content
        
    Returns:
        Paginated list of news articles with metadata
    """
    import time
    start_time = time.time()
    request_id = str(uuid.uuid4())[:8]
    
    try:
        logger.info(f"[{request_id}] Starting news list request")
        
        # Fetch data using the helper function
        fetch_start = time.time()
        formatted_items, total = await _get_news_list(
            db=db,
            skip=skip,
            limit=limit,
            q=q,
            source=source,
            category=category,
            topic_id=topic_id,
            has_topic=has_topic,
            from_date=from_date,
            to_date=to_date,
            language=language,
            sort_by=sort_by,
            sort_order=sort_order,
            include_content=include_content
        )
        fetch_time = time.time() - fetch_start
        
        # Calculate pagination metadata
        has_more = (skip + limit) < total
        next_skip = skip + limit if has_more else None
        
        # Log performance metrics
        total_time = time.time() - start_time
        logger.info(
            f"[{request_id}] Fetched {len(formatted_items)} of {total} items in {total_time:.2f}s | "
            f"DB Query: {fetch_time:.3f}s"
        )
        
        # Return response in the expected format
        return {
            "data": formatted_items,
            "pagination": {
                "total": total,
                "skip": skip,
                "limit": limit,
                "has_more": has_more,
                "next_skip": next_skip
            }
        }
        
    except HTTPException:
        raise
    except errors.OperationFailure as e:
        logger.error(f"Database operation failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database operation failed"
        )
    except Exception as e:
        error_id = str(uuid.uuid4())
        logger.error(f"Error listing news (ID: {error_id}): {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_server_error",
                "message": "An error occurred while retrieving news.",
                "error_id": error_id,
                "suggestion": "Please try again later or contact support if the issue persists.",
                "timestamp": datetime.utcnow().isoformat()
            }
        )


def format_news_item(item: dict, include_full_content: bool = True) -> dict:
    """Format a news item for API response.
    
    VERSÃO MELHORADA: Mantém toda a lógica existente + melhorias pontuais
    """
    from datetime import datetime
    
    # ===== LÓGICA EXISTENTE MANTIDA =====
    # Get the best available content (prefer content over description)
    content = item.get("content")
    if not content and "description" in item:
        content = item["description"]
    
    # Get the best available URL (prefer url over original_url)
    url = item.get("url")
    if not url and "original_url" in item:
        url = item["original_url"]
    
    # ✅ MELHORIA 1: Validar URLs inválidas
    if url == "https://source-not-available.com/" or not (url and url.startswith(("http://", "https://"))):
        url = None
    
    # Get source information with fallbacks
    source_name = item.get("source_name")
    if not source_name and "source" in item and isinstance(item["source"], dict):
        source_name = item["source"].get("name")
    source_name = source_name or "Unknown Source"
    
    source_domain = item.get("source_domain", "")
    if not source_domain and "source" in item and isinstance(item["source"], dict):
        source_domain = item["source"].get("domain", "")
    
    # ✅ MELHORIA 2: Auto-gerar description se vazia
    description = item.get("description", "")
    auto_generated_desc = False
    if not description and content and len(content) > 50:
        description = content[:200].strip()
        if len(content) > 200:
            last_period = description.rfind('.')
            if last_period > 150:
                description = description[:last_period + 1]
            else:
                description += "..."
        auto_generated_desc = True
    
    # Format published_at - ensure it's a datetime object or None
    published_at = item.get("published_at")
    if isinstance(published_at, str):
        try:
            published_at = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            published_at = None
    
    # Prepare image data - handle both image_url and nested image object
    image = None
    if "image_url" in item and item["image_url"]:
        image = {
            "url": str(item["image_url"]),  # Ensure URL is string
            "width": item.get("image_width"),
            "height": item.get("image_height"),
            "caption": item.get("image_caption")
        }
    elif "image" in item and isinstance(item["image"], dict) and item["image"].get("url"):
        image = {
            "url": str(item["image"]["url"]),  # Ensure URL is string
            "width": item["image"].get("width"),
            "height": item["image"].get("height"),
            "caption": item["image"].get("caption")
        }
    
    # Prepare topics - ensure it's always a list of strings
    topics = []
    if "topics" in item and isinstance(item["topics"], list):
        topics = [str(topic) for topic in item["topics"]]
    elif "topic_ids" in item and isinstance(item["topic_ids"], list):
        topics = [str(topic_id) for topic_id in item["topic_ids"]]
    
    # ✅ MELHORIA 3: Melhorar análise de sentiment
    sentiment = None
    if "sentiment_score" in item or "sentiment_label" in item:
        sentiment = {
            "score": float(item.get("sentiment_score", 0.0)),
            "label": str(item.get("sentiment_label", "neutral"))
        }
    elif "sentiment" in item and isinstance(item["sentiment"], dict):
        sentiment = {
            "score": float(item["sentiment"].get("score", 0.0)),
            "label": str(item["sentiment"].get("label", "neutral"))
        }
    # ✅ NOVO: Auto-análise se não existe
    elif not sentiment:
        sentiment = auto_analyze_sentiment(item.get("title", ""), description)
    
    # ✅ MELHORIA 4: Auto-categorização se vazia
    categories = item.get("categories", [])
    if not categories:
        categories = auto_categorize_news(item.get("title", ""), content or description)
    
    # ✅ MELHORIA 5: Keywords extraídas se vazias
    keywords = item.get("keywords", [])
    if not keywords:
        keywords = extract_keywords_smart(item.get("title", ""), content or description)
    
    # Get favicon from favicon_url, favicon, or source.favicon
    favicon = None
    if "favicon_url" in item and item["favicon_url"]:
        favicon = str(item["favicon_url"])
    elif "favicon" in item and item["favicon"]:
        favicon = str(item["favicon"])
    elif "source" in item and isinstance(item["source"], dict) and item["source"].get("favicon"):
        favicon = str(item["source"]["favicon"])
    # ✅ MELHORIA 6: Auto-gerar favicon se não existe
    elif source_domain and source_domain != "source-not-available.com":
        favicon = f"https://{source_domain}/favicon.ico"
    
    # Get language and country with fallbacks
    language = str(item.get("language", "pt")).lower()
    country = str(item.get("country", "BR")).upper()
    
    # Get timestamps with fallbacks
    created_at = item.get("created_at", datetime.utcnow())
    updated_at = item.get("updated_at", datetime.utcnow())
    published_at = item.get("published_at", created_at)
    
    # Handle datetime objects for JSON serialization
    if hasattr(created_at, 'isoformat'):
        created_at = created_at.isoformat()
    if hasattr(updated_at, 'isoformat'):
        updated_at = updated_at.isoformat()
    if hasattr(published_at, 'isoformat'):
        published_at = published_at.isoformat()
    else:
        published_at = str(published_at) if published_at is not None else created_at
    
    # ✅ MELHORIA 7: Source ID gerado
    source_id = generate_source_id(source_domain) if source_domain else None
    
    # Build the response dictionary with all required fields
    response = {
        "id": str(item.get("_id", "")),
        "title": str(item.get("title", "")),
        "description": description,  # ✅ Melhorada
        "content": str(content) if include_full_content and content else "",
        "url": url,  # ✅ Validada
        "source": {
            "id": source_id,  # ✅ NOVO
            "name": str(source_name),
            "domain": str(source_domain),
            "favicon": favicon,
            "reliability_score": calculate_source_reliability(source_domain)  # ✅ NOVO
        } if favicon else {
            "id": source_id,  # ✅ NOVO
            "name": str(source_name),
            "domain": str(source_domain),
            "reliability_score": calculate_source_reliability(source_domain)  # ✅ NOVO
        },
        "published_at": published_at,
        "image": image,
        "topics": topics,
        "categories": categories,  # ✅ Melhorada
        "topic_id": str(item["topic_id"]) if item.get("topic_id") else None,
        "topic_category": item.get("topic_category"),
        "sentiment": sentiment,  # ✅ Melhorada
        "keywords": keywords,  # ✅ Melhorada
        "entities": item.get("entities", []),
        "language": language,
        "country": country,
        "created_at": created_at,
        "updated_at": updated_at,
        "metadata": {}
    }
    
    # Add metrics if present (mantido como está)
    if "metrics" in item and item["metrics"]:
        response["metrics"] = {
            "views": int(item["metrics"].get("views", 0)),
            "shares": int(item["metrics"].get("shares", 0)),
            "engagement_rate": float(item["metrics"].get("engagement_rate", 0.0)),
            "avg_read_time": int(item["metrics"].get("avg_read_time", 0))
        }
    
    # ✅ MELHORIA 8: Metadata enriquecido
    response["metadata"] = {
        # Metadata original mantido
        "has_image": bool(image and image.get("url")),
        "has_favicon": bool(favicon),
        "has_description": bool(item.get("description")),
        "language": language,
        "country": country,
        "processed_at": item.get("processed_at") or datetime.utcnow().isoformat(),
        "source": source_domain,
        
        # Novos campos de qualidade
        "auto_generated_description": auto_generated_desc,
        "data_quality_score": calculate_quality_score(response),
        "content_length": len(content) if content else 0,
        "title_length": len(item.get("title", "")),
        "reading_time_estimate": estimate_reading_time(content),
        "is_recent": is_article_recent(published_at),
        "has_valid_url": bool(url),
        "processing_enhanced": True
    }
    
    # Add any additional metadata from the item (mantido)
    if isinstance(item.get("metadata"), dict):
        response["metadata"].update(item["metadata"])
    
    # Remove None values from the response (mantido)
    return {k: v for k, v in response.items() if v is not None}




@router.get(
    "/{news_id}",
    response_model=NewsResponse,
    response_model_exclude_none=True,
    responses={
        200: {
            "description": "News article retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "data": {
                            "id": "507f1f77bcf86cd799439011",
                            "title": "Título da Notícia",
                            "description": "Descrição da notícia...",
                            "url": "https://example.com/noticia",
                            "source": {
                                "name": "Example News",
                                "domain": "example.com"
                            },
                            "published_at": "2023-01-01T12:00:00Z",
                            "image": {
                                "url": "https://example.com/image.jpg",
                                "width": 800,
                                "height": 600,
                                "caption": "Imagem ilustrativa"
                            },
                            "topics": ["saúde", "tecnologia"],
                            "sentiment": {
                                "score": 0.85,
                                "label": "positive"
                            },
                            "language": "pt",
                            "country": "BR",
                            "created_at": "2023-01-01T12:00:00Z",
                            "updated_at": "2023-01-01T12:00:00Z"
                        },
                        "related_news": [
                            {
                                "id": "507f1f77bcf86cd799439012",
                                "title": "Notícia Relacionada",
                                "url": "https://example.com/noticia-relacionada",
                                "published_at": "2023-01-01T12:00:00Z",
                                "source_name": "Example News",
                                "image_url": "https://example.com/related-image.jpg"
                            }
                        ],
                        "metrics": {
                            "views": 150,
                            "shares": 25,
                            "engagement_rate": 0.75,
                            "avg_read_time": 120,
                            "last_viewed_at": "2023-01-01T12:00:00Z"
                        },
                        "metadata": {
                            "retrieved_at": "2023-01-01T12:00:00Z",
                            "cache_hit": False
                        }
                    }
                }
            }
        },
        400: {
            "description": "Invalid news ID format",
            "content": {
                "application/json": {
                    "example": {
                        "error": "invalid_id_format",
                        "message": "Invalid news ID format: invalid_id",
                        "suggestion": "Ensure the ID is a valid 24-character hex string"
                    }
                }
            }
        },
        404: {
            "description": "News article not found",
            "content": {
                "application/json": {
                    "example": {
                        "error": "not_found",
                        "message": "News article with ID 507f1f77bcf86cd799439011 not found",
                        "suggestion": "Check the ID or try another article"
                    }
                }
            }
        }
    }
)
async def get_news(
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db),
    news_id: str = Path(
        ...,
        description="The ID of the news article to retrieve",
        example="507f1f77bcf86cd799439011"
    ),
    include_related: bool = Query(
        False, 
        description="Include related news articles based on topic or category"
    ),
    include_metrics: bool = Query(
        False,
        description="Include view count and engagement metrics"
    )
) -> NewsResponse:
    """Get a single news article by ID with optional related content and metrics.
    
    This endpoint retrieves a news article by its ID and can include additional
    related content and engagement metrics. The response is cached for performance.
    
    Args:
        request: FastAPI request object.
        db: Async database connection.
        news_id: The ID of the news article to retrieve.
        include_related: Whether to include related news articles.
        include_metrics: Whether to include engagement metrics.
        
    Returns:
        NewsResponse: The requested news article with optional related content and metrics.
        
    Raises:
        HTTPException: If the news article is not found or an error occurs.
    """
    logger.info(f"Fetching news article with ID: {news_id}")
    
    # Validate news_id format
    if not ObjectId.is_valid(news_id):
        logger.error(f"Invalid news ID format: {news_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_id_format",
                "message": f"Invalid news ID format: {news_id}",
                "suggestion": "Ensure the ID is a valid 24-character hex string"
            }
        )
    
    try:
        logger.debug(f"Querying database for news article with ID: {news_id}")
        news_item = await db.news.find_one({"_id": ObjectId(news_id)})
        
        if not news_item:
            logger.warning(f"News article with ID {news_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "not_found",
                    "message": f"News article with ID {news_id} not found",
                    "suggestion": "Check the ID or try another article",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        logger.debug(f"Found news article: {news_item.get('title', 'No title')}")
        
        # Format the news item with full content
        try:
            formatted_item = format_news_item(news_item, include_full_content=True)
            logger.debug("Successfully formatted news item")
        except Exception as format_error:
            logger.error(f"Error formatting news item: {str(format_error)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "format_error",
                    "message": "Error formatting news article data",
                    "error_details": str(format_error)
                }
            )
        
        # Get related news if requested
        related_news = []
        if include_related and news_item.get("topics"):
            try:
                logger.debug(f"Looking for related news with topics: {news_item.get('topics')[:3]}")
                # Create a query to find related news by topics
                related_query = {
                    "_id": {"$ne": ObjectId(news_id)},
                    "topics": {"$in": news_item["topics"][:3]}  # Limit to first 3 topics
                }
                
                # Find related news
                related_cursor = db.news.find(related_query).limit(3)  # Limit to 3 related articles
                related_items = await related_cursor.to_list(3)
                
                logger.debug(f"Found {len(related_items)} related news articles")
                
                # Format related items with limited content
                for item in related_items:
                    try:
                        related_item = format_news_item(item, include_full_content=False)
                        # Ensure required fields for RelatedNewsItem
                        related_news.append({
                            "id": related_item["id"],
                            "title": related_item["title"],
                            "url": related_item["url"],
                            "published_at": related_item["published_at"],
                            "source_name": related_item["source"]["name"],
                            "image_url": related_item.get("image", {}).get("url") if related_item.get("image") else None
                        })
                    except Exception as format_error:
                        logger.error(f"Error formatting related news item {item.get('_id')}: {str(format_error)}", 
                                    exc_info=True)
                        continue
                        
            except Exception as related_error:
                logger.error(f"Error fetching related news: {str(related_error)}", exc_info=True)
        
        # Get metrics if requested
        metrics = None
        if include_metrics:
            try:
                logger.debug(f"Fetching metrics for news article {news_id}")
                metrics_data = await db.metrics.find_one({"news_id": ObjectId(news_id)})
                if metrics_data:
                    # Ensure all metrics fields are present and have the correct types
                    metrics = {
                        "views": int(metrics_data.get("views", 0)),
                        "shares": int(metrics_data.get("shares", 0)),
                        "engagement_rate": float(metrics_data.get("engagement_rate", 0.0)),
                        "avg_read_time": int(metrics_data.get("avg_read_time", 0)),
                        "last_viewed_at": metrics_data.get("last_viewed_at")
                    }
                    # Convert last_viewed_at to ISO format if it's a datetime
                    if metrics["last_viewed_at"] and hasattr(metrics["last_viewed_at"], 'isoformat'):
                        metrics["last_viewed_at"] = metrics["last_viewed_at"].isoformat()
                    logger.debug(f"Found metrics: {metrics}")
                else:
                    logger.debug("No metrics found for this article")
            except Exception as metrics_error:
                logger.error(f"Error fetching metrics: {str(metrics_error)}", exc_info=True)
        
        # Prepare the response with all required fields
        response_metadata = {
            "retrieved_at": datetime.utcnow().isoformat(),
            "cache_hit": False,
            "request_id": str(uuid.uuid4())
        }
        
        # Create the response object with all fields properly set
        response_data = {
            "data": formatted_item,
            "metadata": response_metadata
        }
        
        # Add related_news and metrics if they exist
        if related_news:
            response_data["related_news"] = related_news
        if metrics:
            response_data["metrics"] = metrics
        
        # Log the response data for debugging
        logger.debug(f"Response data: {json.dumps(response_data, default=str, ensure_ascii=False)[:500]}...")
        
        # Validate the response against the Pydantic model
        try:
            response = NewsResponse(**response_data)
            logger.info(f"Successfully retrieved news article {news_id}")
            return response
        except Exception as validation_error:
            logger.error(f"Response validation error: {str(validation_error)}", exc_info=True)
            # Include validation errors in the response for debugging
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "validation_error",
                    "message": "Error validating response data",
                    "error_details": str(validation_error)
                }
            )
            
    except HTTPException:
        # Re-raise HTTP exceptions as they are already properly formatted
        raise
        
    except Exception as e:
        logger.error(f"Unexpected error in get_news: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_server_error",
                "message": "An unexpected error occurred while processing your request",
                "request_id": str(uuid.uuid4())
            }
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
        
    except Exception as e:
        error_id = str(uuid.uuid4())
        logger.error(f"Error retrieving news (ID: {news_id}): {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_server_error",
                "message": "An error occurred while retrieving the news article.",
                "error_id": error_id,
                "suggestion": "Please try again later or contact support if the issue persists.",
                "timestamp": datetime.utcnow().isoformat()
            }
        ) from e

@router.post("/collect", status_code=202, response_model=dict)
async def collect_news(
    request: Request,
    background_tasks: BackgroundTasks,
    query: Optional[str] = None,
    country: str = 'BR'
) -> dict:
    """Trigger a manual news collection.
    
    This endpoint starts a background task to collect news articles based on the provided query
    or default search terms. The collection happens asynchronously to avoid timeouts.
    
    Args:
        request: FastAPI request object.
        background_tasks: FastAPI background tasks manager.
        query: Optional search query. If not provided, uses default queries.
        country: Country code (default: 'BR' for Brazil).
        
    Returns:
        dict: Confirmation message and task details including task_id for status tracking.
        
    Example response:
        {
            "message": "News collection started in the background. Check logs for progress.",
            "status": "processing",
            "task_id": "550e8400-e29b-41d4-a716-446655440000",
            "country": "BR",
            "timestamp": "2025-06-03T22:30:00.000000"
        }
    """
    try:
        # Create a new task
        task_id = task_manager.create_task(
            task_type='news_collection',
            metadata={
                'query': query,
                'country': country.upper(),
                'source': 'api'
            }
        )
        
        # Mark task as started
        task_manager.start_task(task_id)
        
        # Define the background task
        async def _process_collection():
            try:
                if query:
                    result = await news_collector.process_news_batch(query, country.upper())
                else:
                    # Use default queries if none provided
                    result = {}
                    for q in ["autismo Brasil", "TEA Brasil", "transtorno do espectro autista"]:
                        batch_result = await news_collector.process_news_batch(q, country.upper())
                        # Merge results
                        for key, value in batch_result.items():
                            if key in result:
                                if isinstance(value, int):
                                    result[key] += value
                                elif isinstance(value, list):
                                    result[key].extend(value)
                            else:
                                result[key] = value
                
                # Mark task as completed
                task_manager.complete_task(task_id, result)
                logger.info(f"Completed news collection task {task_id}")
                
            except Exception as e:
                # Mark task as failed
                task_manager.fail_task(task_id, e)
                logger.error(f"Error in news collection task {task_id}: {str(e)}", exc_info=True)
        
        # Run in background to avoid timeout
        background_tasks.add_task(_process_collection)
        
        logger.info(f"Started news collection task {task_id} for country {country}")
        
        return {
            "message": "News collection started in the background. Check logs for progress.",
            "status": "processing",
            "task_id": task_id,
            "country": country.upper(),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error starting news collection: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error starting news collection: {str(e)}"
        )
    
@router.get("/{news_id}/enhanced", response_model=EnhancedNewsResponse)
async def get_enhanced_news(
    news_id: str,
    request: Request,
    include_facts: bool = Query(True, description="Include related facts from same topic"),
    facts_limit: int = Query(5, le=10, description="Maximum number of related facts"),
    db: AsyncIOMotorDatabase = Depends(get_db)
) -> EnhancedNewsResponse:
    """
    Get news article with navigation links and related facts.
    
    This endpoint enhances a news article by:
    - Adding clickable links to related topics in the text
    - Providing structured navigation data
    - Including related facts from the same topic (optional)
    
    Args:
        news_id: The ID of the news article
        include_facts: Whether to include related facts
        facts_limit: Maximum number of related facts to return
        db: Database connection
        
    Returns:
        Enhanced news data with navigation and facts
        
    Raises:
        HTTPException: If news not found or invalid ID
    """
    try:
        # Validar ID
        if not ObjectId.is_valid(news_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Invalid news ID format"
            )
            
        # Buscar artigo
        article = await db.news.find_one({"_id": ObjectId(news_id)})
        if not article:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="News article not found"
            )
        
        # Converter para formato da API
        article_dict = convert_objectid_to_str(article)
        
        # Identificar tópico atual
        current_topic = article.get('topic_title')
        
        # Combinar texto para navegação
        title_text = article.get('title', '')
        content_text = article.get('content', '')
        description_text = article.get('description', '')
        full_text = f"{title_text} {description_text} {content_text}".strip()
        
        # Gerar navegação para título
        if title_text:
            article_dict['title_with_links'] = navigation_system.generate_navigation_html(
                title_text, current_topic
            )
        
        # Gerar navegação para conteúdo
        if content_text:
            article_dict['content_with_links'] = navigation_system.generate_navigation_html(
                content_text, current_topic
            )
        
        # Gerar navegação para descrição
        if description_text:
            article_dict['description_with_links'] = navigation_system.generate_navigation_html(
                description_text, current_topic
            )
        
        # Extrair termos linkáveis
        linkable_terms = navigation_system.extract_linkable_terms(full_text, current_topic)
        
        # Criar metadados de navegação
        navigation_metadata = NavigationMetadata(
            current_topic=current_topic,
            has_navigation=len(linkable_terms) > 0,
            total_linkable_terms=len(linkable_terms),
            categories_found=list(set(term['topic_category'] for term in linkable_terms)),
            most_common_category=max(
                set(term['topic_category'] for term in linkable_terms),
                key=lambda cat: sum(1 for term in linkable_terms if term['topic_category'] == cat)
            ) if linkable_terms else None
        )
        
        # Buscar fatos relacionados se solicitado
        related_facts = []
        if include_facts and current_topic:
            # Buscar tópico para obter ID
            topic = await db.topics.find_one({'title': current_topic, 'is_active': True})
            if topic:
                topic_id = str(topic['_id'])
                all_facts = await fact_extraction_system.extract_facts_from_topic(db, topic_id)
                # Filtrar fatos do artigo atual e pegar os top N
                related_facts = [
                    fact for fact in all_facts 
                    if fact.get('source_article_id') != news_id
                ][:facts_limit]
        
        # Adicionar dados ao artigo
        article_dict.update({
            'has_enhanced_navigation': True,
            'navigation_generated_at': datetime.utcnow().isoformat(),
            'total_linkable_terms': len(linkable_terms),
            'categories_in_text': navigation_metadata.categories_found
        })
        
        return EnhancedNewsResponse(
            data=article_dict,
            navigation=navigation_metadata,
            linkable_terms=[LinkableTerm(**term) for term in linkable_terms],
            related_facts=related_facts if include_facts else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting enhanced news {news_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get enhanced news: {str(e)}"
        )

@router.get("/{news_id}/navigation", response_model=Dict[str, Any])
async def get_news_navigation_data(
    news_id: str,
    request: Request,
    format: str = Query("json", description="Output format: 'html' or 'json'"),
    db: AsyncIOMotorDatabase = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get only navigation data for a news article.
    
    This endpoint provides navigation data without the full article content,
    useful for lightweight requests or when you only need the linkable terms.
    
    Args:
        news_id: The ID of the news article
        format: Output format ('html' or 'json')
        db: Database connection
        
    Returns:
        Navigation data in the requested format
    """
    try:
        # Validar ID
        if not ObjectId.is_valid(news_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Invalid news ID format"
            )
            
        # Buscar artigo
        article = await db.news.find_one(
            {"_id": ObjectId(news_id)},
            {"title": 1, "content": 1, "description": 1, "topic_title": 1}
        )
        if not article:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="News article not found"
            )
        
        # Combinar texto
        current_topic = article.get('topic_title')
        full_text = ' '.join([
            article.get('title', ''),
            article.get('description', ''),
            article.get('content', '')
        ]).strip()
        
        if format.lower() == 'html':
            # Retornar HTML com links
            html_with_links = navigation_system.generate_navigation_html(full_text, current_topic)
            return {
                "format": "html",
                "content_with_links": html_with_links,
                "original_content": full_text,
                "current_topic": current_topic
            }
        else:
            # Retornar dados JSON estruturados
            navigation_data = navigation_system.generate_navigation_json(full_text, current_topic)
            return {
                "format": "json",
                "navigation_data": navigation_data,
                "news_id": news_id
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting navigation data for news {news_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get navigation data: {str(e)}"
        )

def auto_analyze_sentiment(title: str, description: str = "") -> Optional[dict]:
    """Análise rápida de sentimento."""
    text = f"{title} {description}".lower()
    
    if not text.strip():
        return None
    
    positive_words = ["aprovado", "sucesso", "melhoria", "avanço", "conquista", "inclusão"]
    negative_words = ["falta", "problema", "dificuldade", "denúncia", "discriminação"]
    
    pos_count = sum(1 for word in positive_words if word in text)
    neg_count = sum(1 for word in negative_words if word in text)
    
    if pos_count > neg_count:
        return {"score": 0.3, "label": "positive"}
    elif neg_count > pos_count:
        return {"score": -0.3, "label": "negative"}
    else:
        return {"score": 0.0, "label": "neutral"}

def auto_categorize_news(title: str, content: str = "") -> List[str]:
    """Categorização automática básica."""
    text = f"{title} {content}".lower()
    categories = []
    
    category_map = {
        "Educação": ["escola", "educação", "ensino", "professor"],
        "Saúde": ["médico", "terapia", "tratamento", "diagnóstico"],
        "Direitos": ["lei", "direito", "projeto", "aprovado"],
        "Tecnologia": ["app", "digital", "tecnologia", "sistema"],
        "Inclusão": ["inclusão", "acessibilidade", "discriminação"]
    }
    
    for category, keywords in category_map.items():
        if any(keyword in text for keyword in keywords):
            categories.append(category)
    
    return categories[:3]

def extract_keywords_smart(title: str, content: str = "") -> List[str]:
    """Extração básica de keywords."""
    text = f"{title} {content}".lower()
    keywords = set()
    
    # Keywords específicas do autismo
    autism_terms = ["autismo", "tea", "autista", "espectro", "inclusão"]
    for term in autism_terms:
        if term in text:
            keywords.add(term)
    
    # Palavras importantes do título
    title_words = [word for word in title.split() 
                  if len(word) > 4 and word.lower() not in ["para", "com", "sobre"]]
    keywords.update(title_words[:3])
    
    return list(keywords)[:8]

def generate_source_id(domain: str) -> str:
    """Gerar ID da fonte."""
    if not domain:
        return "unknown"
    import hashlib
    clean_domain = domain.lower().replace("www.", "")
    return hashlib.md5(clean_domain.encode()).hexdigest()[:8]

def calculate_source_reliability(domain: str) -> float:
    """Calcular confiabilidade da fonte."""
    if not domain:
        return 0.5
    
    reliable_domains = {
        "g1.globo.com": 0.9,
        "folha.uol.com.br": 0.9,
        "gov.br": 0.9
    }
    
    domain_clean = domain.lower().replace("www.", "")
    
    for known, score in reliable_domains.items():
        if known in domain_clean:
            return score
    
    if ".gov.br" in domain_clean:
        return 0.85
    elif ".edu.br" in domain_clean:
        return 0.8
    
    return 0.6

def calculate_quality_score(item: dict) -> float:
    """Calcular score de qualidade."""
    score = 0
    checks = 6
    
    if item.get("title"): score += 1
    if item.get("description"): score += 1
    if item.get("url"): score += 1
    if item.get("source", {}).get("name"): score += 1
    if item.get("published_at"): score += 1
    if item.get("categories"): score += 1
    
    return round(score / checks, 2)

def estimate_reading_time(content: str) -> int:
    """Estimar tempo de leitura."""
    if not content:
        return 0
    word_count = len(content.split())
    return max(30, int((word_count / 200) * 60))

def is_article_recent(published_at) -> bool:
    """Verificar se é recente."""
    if not published_at:
        return False
    
    from datetime import datetime, timedelta
    
    if isinstance(published_at, str):
        try:
            published_at = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
        except:
            return False
    
    if not isinstance(published_at, datetime):
        return False
    
    now = datetime.utcnow()
    if published_at.tzinfo:
        now = now.replace(tzinfo=published_at.tzinfo)
    
    return (now - published_at).days <= 7