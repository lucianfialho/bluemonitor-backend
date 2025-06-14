"""Pydantic models for news-related endpoints."""
from datetime import datetime
from typing import Any, Dict, List, Optional, Union, Literal
from enum import Enum
from pydantic import BaseModel, Field, HttpUrl, validator, AnyHttpUrl, conint, conlist

class Sentiment(BaseModel):
    """Sentiment analysis results for a news article."""
    score: float = Field(..., ge=-1.0, le=1.0, description="Sentiment score from -1 (negative) to 1 (positive)")
    label: str = Field(..., description="Sentiment label (e.g., 'positive', 'negative', 'neutral')")

class NewsImage(BaseModel):
    """Image associated with a news article."""
    url: HttpUrl = Field(..., description="URL of the image")
    width: Optional[int] = Field(None, description="Width of the image in pixels")
    height: Optional[int] = Field(None, description="Height of the image in pixels")
    caption: Optional[str] = Field(None, description="Image caption or alt text")

class NewsSource(BaseModel):
    """Source information for a news article."""
    id: Optional[str] = Field(None, description="Unique identifier for the news source")
    name: str = Field(..., description="Name of the news source")
    domain: Optional[str] = Field(None, description="Domain of the news source")
    favicon: Optional[HttpUrl] = Field(None, description="URL of the source's favicon")

class NewsMetrics(BaseModel):
    """Engagement metrics for a news article."""
    views: int = Field(0, description="Number of times the article was viewed")
    shares: int = Field(0, description="Number of times the article was shared")
    engagement_rate: float = Field(0.0, ge=0.0, le=1.0, description="Engagement rate (0 to 1)")
    avg_read_time: int = Field(0, description="Average read time in seconds")
    last_viewed_at: Optional[datetime] = Field(None, description="When the article was last viewed")

class NewsItemBase(BaseModel):
    """Base model for a news article."""
    id: str = Field(..., description="Unique identifier for the news article")
    title: str = Field(..., description="The title of the news article")
    description: Optional[str] = Field(None, description="A short description or summary of the article")
    content: Optional[str] = Field(None, description="The full content of the article")
    url: HttpUrl = Field(..., description="The URL of the original article")
    image_url: Optional[HttpUrl] = Field(None, description="URL of the main image for the article")
    published_at: Optional[datetime] = Field(None, description="When the article was published")
    source: NewsSource = Field(..., description="Source information for the article")
    authors: List[str] = Field(default_factory=list, description="List of authors of the article")
    language: str = Field("pt", description="Language of the article content")
    categories: List[str] = Field(
        default_factory=list, 
        description="Categories this article belongs to (e.g., 'Saúde', 'Educação', 'Tecnologia')"
    )
    topic_id: Optional[str] = Field(
        None,
        description="ID of the topic this article belongs to, if any"
    )
    topic_category: Optional[str] = Field(
        None,
        description="Main category of the topic this article belongs to, if any"
    )
    sentiment: Optional[Sentiment] = Field(None, description="Sentiment analysis of the article")
    keywords: List[str] = Field(default_factory=list, description="Keywords extracted from the article")
    entities: List[Dict[str, Any]] = Field(
        default_factory=list, 
        description="Named entities mentioned in the article"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Additional metadata about the article"
    )

class NewsItemResponse(NewsItemBase):
    """News article response model with additional metadata."""
    created_at: datetime = Field(..., description="When the article was added to the system")
    updated_at: datetime = Field(..., description="When the article was last updated")

class RelatedNewsItem(BaseModel):
    """Minimal news item for related articles."""
    id: str = Field(..., description="Unique identifier for the news article")
    title: str = Field(..., description="Title of the news article")
    url: HttpUrl = Field(..., description="URL to the original article")
    published_at: datetime = Field(..., description="When the article was published")
    source_name: str = Field(..., description="Name of the news source")
    image_url: Optional[HttpUrl] = Field(None, description="URL of the main image")

class NewsResponse(BaseModel):
    """Response model for a single news article with related content and metrics."""
    data: NewsItemResponse = Field(..., description="The requested news article")
    related_news: Optional[List[RelatedNewsItem]] = Field(
        None, 
        description="List of related news articles"
    )
    metrics: Optional[NewsMetrics] = Field(
        None, 
        description="Engagement metrics for the article"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Response metadata"
    )

class NewsListResponse(BaseModel):
    """Response model for a list of news articles with pagination."""
    data: List[NewsItemResponse] = Field(..., description="List of news articles")
    pagination: Dict[str, Any] = Field(
        ..., 
        description="Pagination information"
    )

class NewsCreate(BaseModel):
    """Model for creating a new news article."""
    title: str = Field(..., min_length=5, max_length=500)
    description: Optional[str] = Field(None, max_length=2000)
    content: Optional[str] = None
    url: HttpUrl
    source_name: str = Field(..., max_length=200)
    source_domain: str = Field(..., max_length=200)
    published_at: datetime
    image_url: Optional[HttpUrl] = None
    topics: List[str] = Field(default_factory=list)
    language: str = "pt"
    country: str = "BR"

class NewsUpdate(BaseModel):
    """Model for updating an existing news article."""
    title: Optional[str] = Field(None, min_length=5, max_length=500)
    description: Optional[str] = Field(None, max_length=2000)
    content: Optional[str] = None
    topics: Optional[List[str]] = None
    sentiment_score: Optional[float] = Field(None, ge=-1.0, le=1.0)
    sentiment_label: Optional[str] = None

class NewsFilters(BaseModel):
    """Query parameters for filtering news articles."""
    q: Optional[str] = Field(
        None,
        description="Search query to filter articles by content, title, or description"
    )
    source: Optional[str] = Field(
        None,
        description="Filter by source domain or source name"
    )
    category: Optional[str] = Field(
        None,
        description="Filter by category name (e.g., 'Saúde', 'Educação')"
    )
    topic_id: Optional[str] = Field(
        None,
        description="Filter by topic ID to get all articles in a specific topic"
    )
    has_topic: Optional[bool] = Field(
        None,
        description="Filter articles that have (true) or don't have (false) an associated topic"
    )
    from_date: Optional[datetime] = Field(
        None,
        description="Filter articles published on or after this date"
    )
    to_date: Optional[datetime] = Field(
        None,
        description="Filter articles published on or before this date"
    )
    language: Optional[str] = Field(
        None,
        description="Filter by language code (e.g., 'pt', 'en')"
    )
    sort_by: str = Field(
        "published_at",
        description="Field to sort results by (published_at, title, source_name, etc.)"
    )
    sort_order: str = Field(
        "desc",
        description="Sort order: 'asc' for ascending, 'desc' for descending"
    )
    include_content: bool = Field(
        False,
        description="Whether to include the full article content in the response"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "autismo",
                "sources": ["g1.com.br", "uol.com.br"],
                "topics": ["saúde", "educação"],
                "start_date": "2023-01-01T00:00:00Z",
                "end_date": "2023-01-31T23:59:59Z",
                "language": "pt",
                "country": "BR",
                "has_image": True,
                "min_sentiment": 0.3,
                "max_sentiment": 1.0
            }
        }
