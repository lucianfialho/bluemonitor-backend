"""News validation service."""
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

from fastapi import HTTPException, status

from app.schemas.news import NewsCreate, NewsUpdate

class NewsValidator:
    """Service for validating news data."""
    
    @staticmethod
    def validate_news_data(news_data: Dict[str, Any], is_update: bool = False) -> Tuple[bool, Optional[Dict[str, Any]], Optional[HTTPException]]:
        """Validate news data before saving to the database.
        
        Args:
            news_data: Dictionary with news data to validate
            is_update: Whether this is an update operation (some fields may be optional)
            
        Returns:
            Tuple of (is_valid, cleaned_data, error)
        """
        try:
            # Set default values for required fields if not provided
            now = datetime.utcnow()
            
            # Ensure required fields have proper defaults
            if not is_update:
                # For new documents, set created_at and updated_at
                news_data.setdefault('created_at', now)
                news_data.setdefault('updated_at', now)
            else:
                # For updates, only update updated_at if not provided
                if 'updated_at' not in news_data:
                    news_data['updated_at'] = now
            
            # Ensure published_at is a datetime
            if 'published_at' in news_data and isinstance(news_data['published_at'], str):
                try:
                    news_data['published_at'] = datetime.fromisoformat(
                        news_data['published_at'].replace('Z', '+00:00')
                    )
                except (ValueError, AttributeError):
                    news_data['published_at'] = now
            
            # Ensure created_at is a datetime
            if 'created_at' in news_data and isinstance(news_data['created_at'], str):
                try:
                    news_data['created_at'] = datetime.fromisoformat(
                        news_data['created_at'].replace('Z', '+00:00')
                    )
                except (ValueError, AttributeError):
                    news_data['created_at'] = now
            
            # Ensure updated_at is a datetime
            if 'updated_at' in news_data and isinstance(news_data['updated_at'], str):
                try:
                    news_data['updated_at'] = datetime.fromisoformat(
                        news_data['updated_at'].replace('Z', '+00:00')
                    )
                except (ValueError, AttributeError):
                    news_data['updated_at'] = now
            
            # If this is a new document, validate required fields
            if not is_update:
                # Create a NewsCreate object to validate required fields
                news_create = NewsCreate(**news_data)
                cleaned_data = news_create.dict()
            else:
                # For updates, only validate fields that are provided
                cleaned_data = news_data
            
            return True, cleaned_data, None
            
        except Exception as e:
            error_msg = f"Invalid news data: {str(e)}"
            return False, None, HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "error": "validation_error",
                    "message": error_msg,
                    "details": str(e)
                }
            )

# Create a singleton instance
news_validator = NewsValidator()
