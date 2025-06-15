import logging
import uuid
import asyncio
import statistics
from typing import Any, AsyncGenerator, Dict, List, Optional, Union
from bson import ObjectId, errors
from datetime import datetime, timedelta
from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, Request, status, Path, Body
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import MongoDBManager
from app.api.v1.utils import convert_objectid_to_str
from app.schemas.topics import TopicResponse, TopicListResponse
from app.schemas.navigation import TopicFactsResponse, ExtractedFact, FactsSummary
from app.core.database import mongodb_manager


# Tentar importar fact extraction se existir
try:
    from app.services.ai.fact_extraction import fact_extraction_system
    HAS_FACT_EXTRACTION = True
except ImportError:
    HAS_FACT_EXTRACTION = False

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()

# 🎨 EPIC ENHANCEMENTS: Category Mapping & Visual Indicators
CATEGORY_ENHANCEMENTS = {
    "educacao_inclusiva": {
        "name": "Educação Inclusiva",
        "color": "#4CAF50",
        "icon": "🎓",
        "priority": "high",
        "description": "Tópicos sobre inclusão e educação especial"
    },
    "diagnostico_tea": {
        "name": "Diagnóstico TEA",
        "color": "#2196F3",
        "icon": "🔬",
        "priority": "high",
        "description": "Diagnóstico e identificação precoce"
    },
    "direitos_inclusao": {
        "name": "Direitos e Inclusão",
        "color": "#FF9800",
        "icon": "⚖️",
        "priority": "high",
        "description": "Direitos legais e inclusão social"
    },
    "tratamento_terapia": {
        "name": "Tratamento e Terapia",
        "color": "#9C27B0",
        "icon": "💊",
        "priority": "medium",
        "description": "Tratamentos e terapias disponíveis"
    },
    "pesquisa_ciencia": {
        "name": "Pesquisa e Ciência",
        "color": "#607D8B",
        "icon": "🔬",
        "priority": "medium",
        "description": "Pesquisas científicas sobre autismo"
    },
    "tecnologia_inovacao": {
        "name": "Tecnologia e Inovação",
        "color": "#795548",
        "icon": "💻",
        "priority": "medium",
        "description": "Tecnologias assistivas e inovações"
    },
    "familia_cuidadores": {
        "name": "Família e Cuidadores",
        "color": "#E91E63",
        "icon": "👨‍👩‍👧‍👦",
        "priority": "high",
        "description": "Orientações para famílias e cuidadores"
    },
    "sensibilizacao_conscientizacao": {
        "name": "Sensibilização",
        "color": "#00BCD4",
        "icon": "💙",
        "priority": "medium",
        "description": "Campanhas de conscientização"
    },
    "violencia_discriminacao": {
        "name": "Violência e Discriminação",
        "color": "#F44336",
        "icon": "⚠️",
        "priority": "high",
        "description": "Casos de violência e discriminação"
    },
    "trabalho_emprego": {
        "name": "Trabalho e Emprego",
        "color": "#3F51B5",
        "icon": "💼",
        "priority": "medium",
        "description": "Inclusão no mercado de trabalho"
    }
}

# 🎯 Trending Score Calculation Weights
TRENDING_WEIGHTS = {
    "recent_articles": 0.4,      # Artigos recentes
    "article_growth": 0.3,       # Crescimento de artigos
    "source_diversity": 0.2,     # Diversidade de fontes
    "quality_boost": 0.1         # Boost por qualidade
}

async def get_db(request: Request) -> AsyncGenerator[AsyncIOMotorDatabase, None]:
    """Dependency that provides a database connection for the request."""
    await mongodb_manager.connect_to_mongodb()
    yield mongodb_manager.db


# 🧠 EPIC INTELLIGENCE FUNCTIONS

def safe_mean(values):
    """Safe mean calculation handling empty lists."""
    if not values:
        return 0.0
    return statistics.mean(values)

def safe_stdev(values):
    """Safe standard deviation calculation."""
    if len(values) < 2:
        return 0.0
    try:
        return statistics.stdev(values)
    except statistics.StatisticsError:
        return 0.0

async def calculate_trending_score(topic: Dict[str, Any], db: AsyncIOMotorDatabase) -> float:
    """
    🔥 Calculate trending score based on multiple factors
    Returns a score between 0.0 and 1.0
    """
    try:
        now = datetime.utcnow()
        last_24h = now - timedelta(hours=24)
        last_week = now - timedelta(days=7)
        
        # Get articles for this topic
        article_ids = [ObjectId(aid) for aid in topic.get('articles', [])]
        
        if not article_ids:
            return 0.0
        
        # Count recent articles (last 24h)
        recent_count = await db.news.count_documents({
            '_id': {'$in': article_ids},
            'created_at': {'$gte': last_24h}
        })
        
        # Count articles in last week for growth calculation
        week_count = await db.news.count_documents({
            '_id': {'$in': article_ids},
            'created_at': {'$gte': last_week}
        })
        
        # Get source diversity
        sources = await db.news.distinct('source.domain', {
            '_id': {'$in': article_ids}
        })
        source_diversity = min(len(sources) / 5.0, 1.0)  # Normalize to max 5 sources
        
        # Calculate growth rate
        total_articles = len(article_ids)
        growth_rate = week_count / max(total_articles, 1) if total_articles > 0 else 0
        
        # Calculate quality boost (based on facts processed)
        quality_boost = 1.0 if topic.get('facts_processed') else 0.5
        
        # Weight the scores
        trending_score = (
            (recent_count / max(total_articles, 1)) * TRENDING_WEIGHTS["recent_articles"] +
            min(growth_rate, 1.0) * TRENDING_WEIGHTS["article_growth"] +
            source_diversity * TRENDING_WEIGHTS["source_diversity"] +
            quality_boost * TRENDING_WEIGHTS["quality_boost"]
        )
        
        return min(trending_score, 1.0)
        
    except Exception as e:
        logger.error(f"Error calculating trending score: {e}")
        return 0.0

async def analyze_topic_sentiment(topic: Dict[str, Any], db: AsyncIOMotorDatabase) -> Dict[str, Any]:
    """
    🧠 Analyze overall sentiment of topic based on articles
    """
    try:
        article_ids = [ObjectId(aid) for aid in topic.get('articles', [])]
        
        if not article_ids:
            return {"score": 0.0, "label": "neutral", "confidence": 0.0}
        
        # Get articles with sentiment data
        articles = await db.news.find({
            '_id': {'$in': article_ids},
            'ai_analysis.sentiment': {'$exists': True}
        }, {
            'ai_analysis.sentiment': 1
        }).to_list(length=None)
        
        if not articles:
            return {"score": 0.0, "label": "neutral", "confidence": 0.0}
        
        # Calculate weighted average sentiment
        sentiments = []
        for art in articles:
            sentiment_data = art.get('ai_analysis', {}).get('sentiment', {})
            if sentiment_data and 'score' in sentiment_data:
                sentiments.append(sentiment_data['score'])
        
        if not sentiments:
            return {"score": 0.0, "label": "neutral", "confidence": 0.0}
        
        avg_sentiment = safe_mean(sentiments)
        confidence = 1.0 - safe_stdev(sentiments)
        
        # Determine label
        if avg_sentiment > 0.3:
            label = "positive"
        elif avg_sentiment < -0.3:
            label = "negative"
        else:
            label = "neutral"
        
        return {
            "score": round(avg_sentiment, 3),
            "label": label,
            "confidence": round(min(confidence, 1.0), 3),
            "sample_size": len(sentiments)
        }
        
    except Exception as e:
        logger.error(f"Error analyzing topic sentiment: {e}")
        return {"score": 0.0, "label": "neutral", "confidence": 0.0}

async def extract_topic_keywords(topic: Dict[str, Any], db: AsyncIOMotorDatabase) -> List[str]:
    """
    🎯 Extract consolidated keywords from all articles in topic
    """
    try:
        article_ids = [ObjectId(aid) for aid in topic.get('articles', [])]
        
        if not article_ids:
            return []
        
        # Get keywords from articles
        articles = await db.news.find({
            '_id': {'$in': article_ids},
            'ai_analysis.keywords': {'$exists': True}
        }, {
            'ai_analysis.keywords': 1
        }).to_list(length=None)
        
        # Aggregate keywords with frequency
        keyword_freq = {}
        for article in articles:
            keywords = article.get('ai_analysis', {}).get('keywords', [])
            for keyword in keywords:
                keyword_freq[keyword] = keyword_freq.get(keyword, 0) + 1
        
        # Sort by frequency and return top 10
        sorted_keywords = sorted(keyword_freq.items(), key=lambda x: x[1], reverse=True)
        return [kw[0] for kw in sorted_keywords[:10]]
        
    except Exception as e:
        logger.error(f"Error extracting topic keywords: {e}")
        return []

async def calculate_quality_score(topic: Dict[str, Any], db: AsyncIOMotorDatabase) -> float:
    """
    💎 Calculate overall quality score for topic
    """
    try:
        article_ids = [ObjectId(aid) for aid in topic.get('articles', [])]
        
        if not article_ids:
            return 0.0
        
        # Get quality scores from articles
        articles = await db.news.find({
            '_id': {'$in': article_ids}
        }, {
            'quality_score': 1,
            'ai_analysis': 1
        }).to_list(length=None)
        
        if not articles:
            return 0.5  # Default medium quality
        
        # Calculate weighted average quality
        quality_scores = []
        for article in articles:
            base_score = article.get('quality_score', 0.5)
            
            # Boost for AI analysis completeness
            ai_analysis = article.get('ai_analysis', {})
            completeness_boost = 0.0
            if ai_analysis.get('categories'):
                completeness_boost += 0.1
            if ai_analysis.get('sentiment'):
                completeness_boost += 0.1
            if ai_analysis.get('keywords'):
                completeness_boost += 0.1
            
            final_score = min(base_score + completeness_boost, 1.0)
            quality_scores.append(final_score)
        
        return round(safe_mean(quality_scores), 3)
        
    except Exception as e:
        logger.error(f"Error calculating quality score: {e}")
        return 0.5

async def find_related_topics(topic: Dict[str, Any], db: AsyncIOMotorDatabase, limit: int = 5) -> List[Dict[str, Any]]:
    """
    🔗 Find related topics based on categories and keywords
    """
    try:
        current_category = topic.get('category')
        
        if not current_category:
            return []
        
        # Find topics with same category or similar keywords
        related = await db.topics.find({
            '_id': {'$ne': topic['_id']},
            'is_active': True,
            '$or': [
                {'category': current_category},
                # Could add more sophisticated matching here
            ]
        }, {
            'title': 1,
            'category': 1,
            'article_count': 1,
            'updated_at': 1
        }).limit(limit).to_list(length=limit)
        
        return [convert_objectid_to_str(t) for t in related]
        
    except Exception as e:
        logger.error(f"Error finding related topics: {e}")
        return []

async def get_visual_indicators(topic: Dict[str, Any], trending_score: float, quality_score: float) -> Dict[str, Any]:
    """
    ✨ Get visual indicators for topic presentation
    """
    indicators = []
    
    # Trending indicator
    if trending_score > 0.7:
        indicators.append({"icon": "🔥", "label": "trending", "description": "Em alta"})
    elif trending_score > 0.5:
        indicators.append({"icon": "📈", "label": "growing", "description": "Crescendo"})
    
    # Quality indicator
    if quality_score > 0.8:
        indicators.append({"icon": "⭐", "label": "high-quality", "description": "Alta qualidade"})
    
    # Recent activity
    updated_recently = topic.get('updated_at', datetime.min)
    if isinstance(updated_recently, str):
        try:
            updated_recently = datetime.fromisoformat(updated_recently.replace('Z', '+00:00'))
        except ValueError:
            updated_recently = datetime.min
    
    if datetime.utcnow() - updated_recently < timedelta(hours=6):
        indicators.append({"icon": "⚡", "label": "breaking", "description": "Recente"})
    
    # Article count indicator
    article_count = topic.get('article_count', 0)
    if article_count > 10:
        indicators.append({"icon": "📰", "label": "comprehensive", "description": "Abrangente"})
    
    return {
        "indicators": indicators,
        "priority_level": "high" if trending_score > 0.6 or quality_score > 0.8 else "medium",
        "recommended": trending_score > 0.5 and quality_score > 0.6
    }

# 🚀 MAIN ENHANCED ENDPOINTS

@router.get("", response_model=TopicListResponse)
async def get_topics(
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db),
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of items to return"),
    country: Optional[str] = Query(None, description="Filter by country (e.g., 'BR' for Brazil)"),
    category: Optional[str] = Query(None, description="Filter by category name"),
    min_articles: Optional[int] = Query(None, ge=1, description="Minimum number of articles in topic"),
    max_articles: Optional[int] = Query(None, ge=1, description="Maximum number of articles in topic"),
    sort_by: str = Query("updated_at", description="Field to sort results by"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order"),
    include_analytics: bool = Query(True, description="Include advanced analytics"),
    include_intelligence: bool = Query(True, description="Include AI intelligence data"),
    include_visual_indicators: bool = Query(True, description="Include visual presentation indicators")
) -> TopicListResponse:
    """
    🔥 Get a list of topics with EPIC ENHANCEMENTS!
    
    This endpoint returns topics with advanced analytics, intelligence layer,
    and visual indicators for an amazing user experience!
    
    New Features:
    - 📈 Trending scores and growth metrics
    - 🧠 AI sentiment analysis and keywords
    - 🎨 Visual indicators and color coding
    - 💎 Quality scoring and content metrics
    - 🔗 Related topics suggestions
    """
    try:
        # Build the query
        query = {"is_active": True}
        
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
        
        # Get total count for pagination
        total = await db.topics.count_documents(query)
        
        # Get basic topics first
        valid_sort_fields = {"created_at", "updated_at", "last_updated", "article_count", "first_seen"}
        sort_field = sort_by if sort_by in valid_sort_fields else "updated_at"
        sort_order_int = -1 if sort_order.lower() == "desc" else 1
        
        cursor = db.topics.find(query).sort([(sort_field, sort_order_int)]).skip(skip).limit(limit)
        topics = await cursor.to_list(length=limit)
        
        # Convert ObjectId to string
        topics = [convert_objectid_to_str(topic) for topic in topics]
        
        # 🔥 EPIC ENHANCEMENTS START HERE!
        enhanced_topics = []
        
        for topic in topics:
            enhanced_topic = topic.copy()
            
            # 📊 Analytics Layer
            if include_analytics:
                trending_score = await calculate_trending_score(topic, db)
                quality_score = await calculate_quality_score(topic, db)
                
                # Calculate growth metrics
                now = datetime.utcnow()
                last_week = now - timedelta(days=7)
                article_ids = [ObjectId(aid) for aid in topic.get('articles', [])]
                
                recent_articles = await db.news.count_documents({
                    '_id': {'$in': article_ids},
                    'created_at': {'$gte': last_week}
                }) if article_ids else 0
                
                growth_rate = f"+{int((recent_articles / max(len(article_ids), 1)) * 100)}%" if article_ids else "+0%"
                
                # Get source diversity
                sources = await db.news.distinct('source.domain', {
                    '_id': {'$in': article_ids}
                }) if article_ids else []
                
                # Time since last update
                last_updated = topic.get('updated_at', datetime.utcnow())
                if isinstance(last_updated, str):
                    try:
                        last_updated = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
                    except ValueError:
                        last_updated = datetime.utcnow()
                
                time_diff = datetime.utcnow() - last_updated
                if time_diff.total_seconds() < 3600:
                    last_updated_str = f"{int(time_diff.total_seconds() / 60)}m ago"
                elif time_diff.total_seconds() < 86400:
                    last_updated_str = f"{int(time_diff.total_seconds() / 3600)}h ago"
                else:
                    last_updated_str = f"{time_diff.days}d ago"
                
                enhanced_topic["content_metrics"] = {
                    "article_count": topic.get('article_count', 0),
                    "source_diversity": len(sources),
                    "quality_score": quality_score,
                    "trending_score": trending_score,
                    "growth_rate": growth_rate,
                    "last_updated": last_updated_str,
                    "freshness_score": max(0, 1 - (time_diff.total_seconds() / 604800))  # Week-based freshness
                }
            
            # 🧠 Intelligence Layer
            if include_intelligence:
                sentiment = await analyze_topic_sentiment(topic, db)
                keywords = await extract_topic_keywords(topic, db)
                related_topics = await find_related_topics(topic, db, limit=3)
                
                # Enhanced summary
                facts_summary = topic.get('facts_summary', {})
                enhanced_summary = facts_summary.get('summary', topic.get('description', ''))
                
                enhanced_topic["intelligence"] = {
                    "summary": enhanced_summary,
                    "sentiment": sentiment,
                    "keywords": keywords,
                    "related_topics": [
                        {
                            "id": rt.get("id", str(rt.get("_id", ""))), 
                            "title": rt.get("title", "Untitled")
                        } for rt in related_topics
                    ],
                    "entities_count": len(keywords),
                    "confidence_score": sentiment.get('confidence', 0.0)
                }
            
            # 🎨 Enhanced Category Info
            category_id = topic.get('category', 'geral')
            category_info = CATEGORY_ENHANCEMENTS.get(category_id, {
                "name": category_id.replace('_', ' ').title(),
                "color": "#757575",
                "icon": "📰",
                "priority": "medium",
                "description": "Categoria geral"
            })
            
            enhanced_topic["category"] = {
                "id": category_id,
                **category_info
            }
            
            # ✨ Visual Indicators
            if include_visual_indicators:
                trending_score = enhanced_topic.get("content_metrics", {}).get("trending_score", 0.0)
                quality_score = enhanced_topic.get("content_metrics", {}).get("quality_score", 0.5)
                visual_data = await get_visual_indicators(topic, trending_score, quality_score)
                enhanced_topic["presentation"] = visual_data
            
            enhanced_topics.append(enhanced_topic)
        
        # Sort by trending score if requested
        if sort_by == "trending_score" and include_analytics:
            enhanced_topics.sort(
                key=lambda x: x.get("content_metrics", {}).get("trending_score", 0),
                reverse=(sort_order.lower() == "desc")
            )
        
        # Calculate pagination metadata
        has_more = (skip + limit) < total
        next_skip = skip + limit if has_more else None
        
        return TopicListResponse(
            data=enhanced_topics,
            pagination={
                "total": total,
                "skip": skip,
                "limit": limit,
                "has_more": has_more,
                "next_skip": next_skip,
                "enhancements_applied": {
                    "analytics": include_analytics,
                    "intelligence": include_intelligence,
                    "visual_indicators": include_visual_indicators
                }
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

@router.get("/{topic_id}", response_model=TopicResponse)
async def get_topic(
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db),
    topic_id: str = Path(..., description="The ID of the topic to retrieve"),
    include_articles: bool = Query(True, description="Include associated news articles"),
    include_article_content: bool = Query(False, description="Include full article content in the response")
) -> TopicResponse:
    """Get a single topic by ID with optional associated news articles."""
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
        
        # Get associated news articles if requested
        articles = []
        if include_articles and topic.get('articles'):
            article_ids = [ObjectId(aid) for aid in topic['articles']]
            
            # Build projection based on content inclusion
            projection = {
                'title': 1, 'description': 1, 'url': 1, 'source': 1,
                'published_at': 1, 'created_at': 1, 'updated_at': 1,
                'image_url': 1, 'categories': 1, 'language': 1, 'country': 1
            }
            
            if include_article_content:
                projection['content'] = 1
                projection['summary'] = 1
                projection['ai_analysis'] = 1
                projection['quality_score'] = 1
            
            # Fetch articles
            article_docs = await db.news.find(
                {'_id': {'$in': article_ids}},
                projection
            ).to_list(length=None)
            
            # Format articles for response
            for article in article_docs:
                article_data = convert_objectid_to_str(article)
                
                # Format dates
                for date_field in ['published_at', 'created_at', 'updated_at']:
                    if date_field in article_data and article_data[date_field]:
                        if isinstance(article_data[date_field], datetime):
                            article_data[date_field] = article_data[date_field].isoformat()
                
                # Format source
                if 'source' in article_data and isinstance(article_data['source'], str):
                    article_data['source'] = {
                        'name': article_data['source'],
                        'domain': article_data['source']
                    }
                
                # Add image if exists
                if article_data.get('image_url'):
                    article_data['image'] = {'url': article_data['image_url']}
                
                articles.append(article_data)
        
        # Create response
        response_data = topic.copy()
        if include_articles:
            response_data['articles'] = articles
        
        return TopicResponse(**response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting topic {topic_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get topic: {str(e)}"
        )

@router.get("/analytics", response_model=Dict[str, Any])
async def get_topics_analytics(
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db),
    days: int = Query(7, ge=1, le=30, description="Number of days to analyze"),
) -> Dict[str, Any]:
    """
    📊 Get comprehensive analytics dashboard for topics
    
    Returns insights about trending topics, category distribution,
    growth patterns, and quality metrics.
    """
    try:
        now = datetime.utcnow()
        since_date = now - timedelta(days=days)
        
        # Get all active topics
        topics = await db.topics.find({
            'is_active': True,
            'updated_at': {'$gte': since_date}
        }).to_list(length=None)
        
        if not topics:
            return {
                "total_topics": 0,
                "period_days": days,
                "message": "No topics found in the specified period"
            }
        
        # Calculate analytics
        total_topics = len(topics)
        total_articles = sum(t.get('article_count', 0) for t in topics)
        
        # Category distribution
        category_dist = {}
        for topic in topics:
            cat = topic.get('category', 'outros')
            category_dist[cat] = category_dist.get(cat, 0) + 1
        
        # Top categories with enhancements
        top_categories = []
        for cat_id, count in sorted(category_dist.items(), key=lambda x: x[1], reverse=True)[:5]:
            cat_info = CATEGORY_ENHANCEMENTS.get(cat_id, {"name": cat_id, "icon": "📰"})
            top_categories.append({
                "category": cat_info["name"],
                "icon": cat_info["icon"],
                "count": count,
                "percentage": round((count / total_topics) * 100, 1)
            })
        
        # Calculate trending topics
        trending_topics = []
        for topic in topics[:10]:  # Limit to top 10 for performance
            trending_score = await calculate_trending_score(topic, db)
            if trending_score > 0.3:  # Only include meaningful trending topics
                cat_info = CATEGORY_ENHANCEMENTS.get(topic.get('category', ''), {"icon": "📰"})
                trending_topics.append({
                    "id": str(topic['_id']),
                    "title": topic.get('title', 'Untitled'),
                    "category_icon": cat_info["icon"],
                    "trending_score": trending_score,
                    "article_count": topic.get('article_count', 0)
                })
        
        # Sort trending topics
        trending_topics.sort(key=lambda x: x['trending_score'], reverse=True)
        
        # Quality insights
        avg_articles_per_topic = round(total_articles / total_topics, 1) if total_topics > 0 else 0
        topics_with_facts = sum(1 for t in topics if t.get('facts_processed'))
        
        # Growth metrics
        new_topics_count = len([t for t in topics if t.get('created_at', now) >= since_date])
        updated_topics_count = len([t for t in topics if t.get('updated_at', now) >= since_date])
        
        return {
            "overview": {
                "total_topics": total_topics,
                "total_articles": total_articles,
                "avg_articles_per_topic": avg_articles_per_topic,
                "period_days": days,
                "analysis_timestamp": now.isoformat()
            },
            "trending": {
                "top_trending_topics": trending_topics[:5],
                "trending_threshold": 0.3,
                "total_trending": len([t for t in trending_topics if t['trending_score'] > 0.5])
            },
            "categories": {
                "distribution": top_categories,
                "total_categories": len(category_dist),
                "most_active": top_categories[0] if top_categories else None
            },
            "quality": {
                "topics_with_facts": topics_with_facts,
                "fact_processing_rate": round((topics_with_facts / total_topics) * 100, 1) if total_topics > 0 else 0,
                "content_richness": "high" if avg_articles_per_topic > 3 else "medium" if avg_articles_per_topic > 1 else "low"
            },
            "activity": {
                "new_topics": new_topics_count,
                "updated_topics": updated_topics_count,
                "activity_rate": round((updated_topics_count / total_topics) * 100, 1) if total_topics > 0 else 0
            }
        }
        
    except Exception as e:
        logger.error(f"Error generating topics analytics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate analytics: {str(e)}"
        )

@router.get("/categories/enhanced", response_model=Dict[str, Any])
async def get_enhanced_categories() -> Dict[str, Any]:
    """
    🎨 Get enhanced category information with visual indicators
    
    Returns all available categories with their visual enhancements,
    icons, colors, and priority levels.
    """
    return {
        "categories": CATEGORY_ENHANCEMENTS,
        "metadata": {
            "total_categories": len(CATEGORY_ENHANCEMENTS),
            "high_priority_categories": len([c for c in CATEGORY_ENHANCEMENTS.values() if c.get('priority') == 'high']),
            "visual_features": ["color_coding", "icons", "priority_levels", "descriptions"],
            "last_updated": "2025-06-15T00:00:00Z"
        }
    }

# 🔗 FACT EXTRACTION ENDPOINTS (if available)
if HAS_FACT_EXTRACTION:
    @router.get("/{topic_id}/facts", response_model=TopicFactsResponse)
    async def get_topic_facts(
        topic_id: str,
        request: Request,
        db: AsyncIOMotorDatabase = Depends(get_db),
        min_score: float = Query(0.3, ge=0.0, le=1.0, description="Minimum fact confidence score"),
        fact_types: Optional[str] = Query(None, description="Comma-separated list of fact types to filter"),
        limit: int = Query(50, ge=1, le=100, description="Maximum number of facts to return"),
        include_structured_data: bool = Query(False, description="Include structured extracted data")
    ) -> TopicFactsResponse:
        """
        Extract and return facts from all articles in a topic.
        
        This endpoint processes all articles within a topic and extracts
        structured facts using AI analysis.
        """
        try:
            # Validar ID do tópico
            if not ObjectId.is_valid(topic_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid topic ID format"
                )
            
            # Verificar se tópico existe
            topic = await db.topics.find_one(
                {'_id': ObjectId(topic_id), 'is_active': True}
            )
            if not topic:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Topic not found"
                )
            
            # Extrair fatos usando o sistema de extração
            all_facts = await fact_extraction_system.extract_facts_from_topic(db, topic_id)
            
            # Filtrar por score mínimo
            filtered_facts = [
                fact for fact in all_facts 
                if fact.get('score', 0) >= min_score
            ]
            
            # Filtrar por tipos se especificado
            if fact_types:
                requested_types = [t.strip().lower() for t in fact_types.split(',')]
                filtered_facts = [
                    fact for fact in filtered_facts 
                    if fact.get('type', '').lower() in requested_types
                ]
            
            # Limitar número de resultados
            final_facts = filtered_facts[:limit]
            
            # Remover dados estruturados se não solicitados
            if not include_structured_data:
                for fact in final_facts:
                    if 'extracted_data' in fact:
                        fact['extracted_data'] = {}
            
            # Buscar artigos do tópico para estatísticas
            article_ids = [ObjectId(aid) for aid in topic.get('articles', [])]
            articles = await db.news.find({'_id': {'$in': article_ids}}).to_list(length=None)
            
            # Gerar resumo dos fatos
            facts_summary = fact_extraction_system.get_facts_summary(filtered_facts)
            
            # Estatísticas dos tipos de fatos
            fact_types_count = {}
            for fact in filtered_facts:
                fact_type = fact.get('type', 'geral')
                fact_types_count[fact_type] = fact_types_count.get(fact_type, 0) + 1
            
            # Converter dados do tópico
            topic_info = convert_objectid_to_str(topic)
            topic_info.update({
                'facts_extraction_metadata': {
                    'extracted_at': datetime.utcnow().isoformat(),
                    'total_articles_analyzed': len(articles),
                    'extraction_filters': {
                        'min_score': min_score,
                        'fact_types_filter': fact_types,
                        'limit': limit
                    },
                    'facts_before_filtering': len(all_facts),
                    'facts_after_filtering': len(filtered_facts)
                }
            })
            
            return TopicFactsResponse(
                topic_info=topic_info,
                extracted_facts=[ExtractedFact(**fact) for fact in final_facts],
                total_facts=len(filtered_facts),
                fact_types=fact_types_count,
                source_articles=len(articles),
                extraction_summary=FactsSummary(**facts_summary)
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting facts for topic {topic_id}: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get topic facts: {str(e)}"
            )

# 🎯 HEALTH CHECK ENDPOINT
@router.get("/health", response_model=Dict[str, Any])
async def topics_health_check(
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db)
) -> Dict[str, Any]:
    """
    🏥 Health check endpoint for topics API
    
    Returns system status and basic metrics.
    """
    try:
        # Basic database connectivity test
        total_topics = await db.topics.count_documents({"is_active": True})
        
        # Test a simple aggregation
        recent_topics = await db.topics.count_documents({
            "is_active": True,
            "updated_at": {"$gte": datetime.utcnow() - timedelta(days=7)}
        })
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "database": "connected",
            "metrics": {
                "total_active_topics": total_topics,
                "recent_topics_7d": recent_topics
            },
            "features": {
                "analytics": True,
                "intelligence": True,
                "visual_indicators": True,
                "fact_extraction": HAS_FACT_EXTRACTION
            },
            "api_version": "2.0_epic"
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )