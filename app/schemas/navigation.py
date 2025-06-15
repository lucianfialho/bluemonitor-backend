"""Schemas for navigation and fact extraction."""

from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field

class LinkableTerm(BaseModel):
    """Schema for a linkable term in text."""
    term: str = Field(..., description="The linkable term")
    start_pos: int = Field(..., description="Start position in text")
    end_pos: int = Field(..., description="End position in text")
    target_topic: str = Field(..., description="Target topic name")
    topic_category: str = Field(..., description="Category of target topic")
    original_text: str = Field(..., description="Original text of the term")
    priority: int = Field(..., description="Priority level")

class NavigationMetadata(BaseModel):
    """Schema for navigation metadata."""
    current_topic: Optional[str] = Field(None, description="Current topic")
    has_navigation: bool = Field(..., description="Has navigation links")
    total_linkable_terms: int = Field(..., description="Total linkable terms")
    categories_found: List[str] = Field(default_factory=list, description="Categories found")
    most_common_category: Optional[str] = Field(None, description="Most common category")

class ExtractedData(BaseModel):
    """Schema for structured data extracted from facts."""
    percentages: Optional[List[float]] = Field(None, description="Percentages found")
    large_numbers: Optional[List[str]] = Field(None, description="Large numbers")
    years: Optional[List[str]] = Field(None, description="Years mentioned")
    ages: Optional[List[int]] = Field(None, description="Ages mentioned")
    laws: Optional[List[str]] = Field(None, description="Law numbers")
    institutions: Optional[List[str]] = Field(None, description="Institutions")

class ExtractedFact(BaseModel):
    """Schema for an extracted fact."""
    text: str = Field(..., description="The fact text")
    score: float = Field(..., description="Relevance score (0-1)")
    type: str = Field(..., description="Type of fact")
    extracted_data: ExtractedData = Field(default_factory=ExtractedData)
    source_article_id: str = Field(..., description="Source article ID")
    source_title: str = Field(..., description="Source article title") 
    source_url: Optional[str] = Field(None, description="Source article URL")
    source_date: Optional[datetime] = Field(None, description="Source article date")
    topic: str = Field(..., description="Topic name")
    topic_id: str = Field(..., description="Topic ID")
    length: int = Field(..., description="Text length")
    word_count: int = Field(..., description="Word count")

class FactsSummary(BaseModel):
    """Schema for facts summary."""
    total_facts: int = Field(..., description="Total number of facts")
    fact_types: Dict[str, int] = Field(..., description="Count by fact type")
    avg_score: float = Field(..., description="Average score")
    top_score: float = Field(..., description="Top score")
    has_statistics: bool = Field(..., description="Has statistical facts")
    has_research: bool = Field(..., description="Has research facts")
    has_legislation: bool = Field(..., description="Has legislation facts")
    facts_with_structured_data: int = Field(..., description="Facts with structured data")
    coverage_percentage: float = Field(..., description="Coverage percentage")

class EnhancedNewsResponse(BaseModel):
    """Schema for enhanced news with navigation."""
    data: Dict[str, Any] = Field(..., description="Enhanced news data")
    navigation: Dict[str, Any] = Field(..., description="Navigation metadata")
    linkable_terms: List[LinkableTerm] = Field(default_factory=list)
    related_facts: Optional[List[ExtractedFact]] = Field(None)

class TopicFactsResponse(BaseModel):
    """Schema for topic facts response."""
    topic_info: Dict[str, Any] = Field(..., description="Topic information")
    extracted_facts: List[ExtractedFact] = Field(..., description="Extracted facts")
    total_facts: int = Field(..., description="Total number of facts")
    fact_types: Dict[str, int] = Field(..., description="Count by fact type")
    source_articles: int = Field(..., description="Number of source articles")
    extraction_summary: FactsSummary = Field(..., description="Summary")