"""Pydantic models for topic-related endpoints."""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, HttpUrl

class TopicBase(BaseModel):
    """Base model for a topic."""
    name: str = Field(..., description="The name/title of the topic")
    title: str = Field(..., description="The display title of the topic")
    summary: Optional[str] = Field(None, description="A brief summary of the topic")
    category: str = Field(..., description="The main category of the topic")
    keywords: List[str] = Field(default_factory=list, description="List of keywords associated with the topic")
    article_count: int = Field(0, description="Number of articles in this topic")
    sources: List[str] = Field(default_factory=list, description="List of news sources in this topic")
    country_focus: str = Field(..., description="Country code this topic is focused on")
    created_at: datetime = Field(..., description="When the topic was created")
    updated_at: datetime = Field(..., description="When the topic was last updated")
    last_updated: datetime = Field(..., description="When the topic was last updated with new articles")
    is_active: bool = Field(True, description="Whether the topic is currently active")
    main_article_id: Optional[str] = Field(None, description="ID of the main article for this topic")
    first_seen: Optional[datetime] = Field(None, description="When the first article in this topic was published")
    language: str = Field("pt", description="Language of the topic content")

class TopicResponse(TopicBase):
    """Response model for a single topic."""
    id: str = Field(..., description="Unique identifier for the topic")
    articles: List[Dict[str, Any]] = Field(default_factory=list, description="List of articles in this topic")

class TopicListResponse(BaseModel):
    """Response model for a list of topics with pagination."""
    data: List[Dict[str, Any]] = Field(..., description="List of topics")
    pagination: Dict[str, Any] = Field(..., description="Pagination metadata")

class TopicFilters(BaseModel):
    """Query parameters for filtering topics."""
    country: Optional[str] = None
    category: Optional[str] = None
    has_articles: Optional[bool] = None
    min_articles: Optional[int] = None
    max_articles: Optional[int] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "country": "BR",
                "category": "Saúde",
                "min_articles": 2
            }
        }
