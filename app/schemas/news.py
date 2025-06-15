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
    url: Optional[HttpUrl] = Field(None, description="The URL of the original article")
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
# ========================================
# ESTENDER NewsSource existente
# ========================================

class EnhancedNewsSource(NewsSource):
    """Extended NewsSource with reliability scoring."""
    reliability_score: float = Field(0.7, ge=0.0, le=1.0, description="Source reliability score (0-1)")

# ========================================
# ESTENDER Sentiment existente  
# ========================================

class EnhancedSentiment(Sentiment):
    """Extended Sentiment with confidence scoring."""
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Confidence in sentiment analysis")

# ========================================
# NOVOS MODELOS PARA METADATA ENRIQUECIDO
# ========================================

class NewsQualityMetadata(BaseModel):
    """Quality and processing metadata for news items."""
    has_full_content: bool = Field(False, description="Whether article has full content")
    content_length: int = Field(0, description="Length of content in characters")
    title_length: int = Field(0, description="Length of title in characters")
    auto_generated_description: bool = Field(False, description="Whether description was auto-generated")
    data_quality_score: float = Field(0.0, ge=0.0, le=1.0, description="Overall data quality score")
    reading_time_estimate: int = Field(0, description="Estimated reading time in seconds")
    is_recent: bool = Field(False, description="Whether article is recent (last 7 days)")
    source_reliability: float = Field(0.5, ge=0.0, le=1.0, description="Source reliability score")
    has_image: bool = Field(False, description="Whether article has an image")
    has_valid_url: bool = Field(False, description="Whether article has valid URL")
    processing_enhanced: bool = Field(False, description="Whether enhanced processing was applied")

class ContentStatistics(BaseModel):
    """Statistics about content collection."""
    total_articles: int = Field(0, description="Total number of articles")
    with_images: int = Field(0, description="Articles with images")
    with_descriptions: int = Field(0, description="Articles with descriptions")
    with_valid_urls: int = Field(0, description="Articles with valid URLs")
    recent_articles: int = Field(0, description="Recent articles (last 7 days)")
    unique_sources: int = Field(0, description="Number of unique sources")

class QualityDistribution(BaseModel):
    """Distribution of quality scores."""
    high: int = Field(0, description="High quality articles (score >= 0.8)")
    medium: int = Field(0, description="Medium quality articles (0.5-0.8)")
    low: int = Field(0, description="Low quality articles (< 0.5)")

class DataQualityMetrics(BaseModel):
    """Overall data quality metrics."""
    average_score: float = Field(0.0, ge=0.0, le=1.0, description="Average quality score")
    complete_articles: int = Field(0, description="Articles with complete content")
    missing_content: int = Field(0, description="Articles missing content")
    quality_distribution: QualityDistribution = Field(default_factory=QualityDistribution)

class PerformanceMetrics(BaseModel):
    """API performance metrics."""
    aggregation_time: float = Field(0.0, description="Database aggregation time (seconds)")
    processing_time: float = Field(0.0, description="Data processing time (seconds)")
    stats_time: float = Field(0.0, description="Statistics calculation time (seconds)")

class ImprovementSuggestions(BaseModel):
    """Suggestions for data improvement."""
    data_quality: List[str] = Field(default_factory=list, description="Data quality issues")
    content_gaps: List[str] = Field(default_factory=list, description="Content gaps identified")
    recommended_actions: List[str] = Field(default_factory=list, description="Recommended actions")

# ========================================
# ESTENDER NewsItemResponse existente
# ========================================

class EnhancedNewsItemResponse(NewsItemResponse):
    """Enhanced NewsItemResponse with quality metadata."""
    # Herda todos os campos existentes e adiciona:
    quality_metadata: Optional[NewsQualityMetadata] = Field(None, description="Quality and processing metadata")
    
    # Sobrescrever source para usar versão enhanced
    source: EnhancedNewsSource = Field(..., description="Enhanced source information")
    
    # Sobrescrever sentiment para usar versão enhanced  
    sentiment: Optional[EnhancedSentiment] = Field(None, description="Enhanced sentiment analysis")

# ========================================
# ESTENDER PAGINAÇÃO EXISTENTE
# ========================================

class EnhancedPagination(BaseModel):
    """Enhanced pagination with additional metadata."""
    total: int = Field(..., description="Total number of items")
    skip: int = Field(..., description="Number of items skipped")
    limit: int = Field(..., description="Maximum items returned")
    has_more: bool = Field(..., description="Whether more items available")
    next_skip: Optional[int] = Field(None, description="Skip value for next page")
    page: int = Field(..., description="Current page number (1-indexed)")
    total_pages: int = Field(..., description="Total number of pages")
    showing: int = Field(..., description="Number of items actually returned")

# ========================================
# METADATA PARA LISTAGEM ENHANCED
# ========================================

class EnhancedListMetadata(BaseModel):
    """Enhanced metadata for list responses."""
    query_time: float = Field(..., description="Total query time in seconds")
    performance: PerformanceMetrics = Field(default_factory=PerformanceMetrics)
    data_quality: DataQualityMetrics = Field(default_factory=DataQualityMetrics)
    content_stats: ContentStatistics = Field(default_factory=ContentStatistics)
    filters_applied: List[str] = Field(default_factory=list, description="Summary of applied filters")
    source_distribution: Dict[str, int] = Field(default_factory=dict, description="Articles by source")

# ========================================
# RESPONSES ENHANCED (MANTENDO COMPATIBILIDADE)
# ========================================

class EnhancedNewsListResponse(BaseModel):
    """Enhanced list response - backwards compatible with NewsListResponse."""
    data: List[EnhancedNewsItemResponse] = Field(..., description="List of enhanced news articles")
    pagination: EnhancedPagination = Field(..., description="Enhanced pagination")
    metadata: Optional[EnhancedListMetadata] = Field(None, description="Enhanced metadata")
    suggestions: Optional[ImprovementSuggestions] = Field(None, description="Improvement suggestions")

class EnhancedNewsResponse(BaseModel):
    """Enhanced single news response - backwards compatible with NewsResponse."""
    data: EnhancedNewsItemResponse = Field(..., description="Enhanced news article")
    related_news: Optional[List[RelatedNewsItem]] = Field(None, description="Related articles")
    metrics: Optional[NewsMetrics] = Field(None, description="Engagement metrics")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Response metadata")

# ========================================
# FILTROS ENHANCED (ESTENDENDO NewsFilters)
# ========================================

class EnhancedNewsFilters(NewsFilters):
    """Enhanced filters extending existing NewsFilters."""
    # Herda todos os filtros existentes e adiciona:
    min_quality: Optional[float] = Field(None, ge=0.0, le=1.0, description="Minimum quality score")
    include_suggestions: bool = Field(True, description="Include improvement suggestions")
    enhanced_processing: bool = Field(True, description="Apply enhanced data processing")

# ========================================
# HELPER CLASSES PARA COMPATIBILIDADE
# ========================================

class NewsItemCompatibilityHelper:
    """Helper to convert between standard and enhanced news items."""
    
    @staticmethod
    def to_enhanced(standard_item: NewsItemResponse, quality_metadata: Optional[NewsQualityMetadata] = None) -> EnhancedNewsItemResponse:
        """Convert standard NewsItemResponse to enhanced version."""
        # Converter source
        enhanced_source = EnhancedNewsSource(
            **standard_item.source.dict(),
            reliability_score=0.7  # Default value
        )
        
        # Converter sentiment se existe
        enhanced_sentiment = None
        if standard_item.sentiment:
            enhanced_sentiment = EnhancedSentiment(
                **standard_item.sentiment.dict(),
                confidence=0.8  # Default confidence
            )
        
        # Criar enhanced item
        return EnhancedNewsItemResponse(
            **standard_item.dict(exclude={'source', 'sentiment'}),
            source=enhanced_source,
            sentiment=enhanced_sentiment,
            quality_metadata=quality_metadata
        )
    
    @staticmethod
    def to_standard(enhanced_item: EnhancedNewsItemResponse) -> NewsItemResponse:
        """Convert enhanced NewsItemResponse back to standard version."""
        # Converter source de volta
        standard_source = NewsSource(
            **enhanced_item.source.dict(exclude={'reliability_score'})
        )
        
        # Converter sentiment de volta
        standard_sentiment = None
        if enhanced_item.sentiment:
            standard_sentiment = Sentiment(
                **enhanced_item.sentiment.dict(exclude={'confidence'})
            )
        
        # Criar standard item
        return NewsItemResponse(
            **enhanced_item.dict(exclude={'source', 'sentiment', 'quality_metadata'}),
            source=standard_source,
            sentiment=standard_sentiment
        )

# ========================================
# VALIDADORES PARA COMPATIBILIDADE
# ========================================

def ensure_backwards_compatibility():
    """Ensure enhanced models are backwards compatible."""
    # Test que EnhancedNewsItemResponse é compatível com NewsItemResponse
    try:
        # Criar um item standard
        standard_source = NewsSource(id="test", name="Test", domain="test.com")
        standard_item = NewsItemResponse(
            id="test",
            title="Test",
            url="http://test.com",
            source=standard_source,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Converter para enhanced
        enhanced = NewsItemCompatibilityHelper.to_enhanced(standard_item)
        
        # Converter de volta
        back_to_standard = NewsItemCompatibilityHelper.to_standard(enhanced)
        
        print("✅ Backwards compatibility verified")
        return True
        
    except Exception as e:
        print(f"❌ Backwards compatibility failed: {e}")
        return False