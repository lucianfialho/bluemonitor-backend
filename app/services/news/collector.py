"""News collection service."""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple, Union

import httpx
from bs4 import BeautifulSoup
from fastapi import HTTPException

from app.core.config import settings
from app.core.database import MongoDBManager
from app.services.ai.processor import process_news_content
from app.schemas.news import NewsCreate

logger = logging.getLogger(__name__)

class NewsCollector:
    """Service for collecting news from various sources."""
    
    def __init__(self):
        """Initialize the news collector."""
        # Configurações da API
        self.serpapi_key = settings.SERPAPI_KEY
        self.serpapi_url = settings.SERPAPI_ENDPOINT
        self.max_articles = settings.MAX_NEWS_ARTICLES_PER_QUERY
        
        # Log das configurações carregadas
        logger.debug(f"Configurações carregadas:")
        logger.debug(f"SERPAPI_KEY: {'*' * 8}{self.serpapi_key[-4:] if self.serpapi_key else 'N/A'}")
        logger.debug(f"SERPAPI_ENDPOINT: {self.serpapi_url}")
        logger.debug(f"MAX_NEWS_ARTICLES_PER_QUERY: {self.max_articles}")
        
    def _parse_publish_date(self, date_str: Any, default: Optional[datetime] = None) -> datetime:
        """Parse a date string to a datetime object.
        
        Args:
            date_str: The date string to parse (can be str, datetime, or None)
            default: Default datetime to return if parsing fails
            
        Returns:
            datetime: The parsed datetime or default if parsing fails
        """
        if not date_str:
            return default or datetime.utcnow()
            
        # If already a datetime, return it
        if isinstance(date_str, datetime):
            return date_str
            
        # If it's a date, convert to datetime
        if hasattr(date_str, 'strftime') and not isinstance(date_str, str):
            return datetime.combine(date_str, datetime.min.time())
            
        # Handle string dates
        if not isinstance(date_str, str):
            return default or datetime.utcnow()
            
        # Handle relative dates like "2 days ago"
        if 'ago' in date_str.lower():
            try:
                # Extract the number and unit (e.g., "2" and "days" from "2 days ago")
                parts = date_str.lower().split()
                if len(parts) >= 2 and parts[0].isdigit() and 'day' in parts[1]:
                    days_ago = int(parts[0])
                    return datetime.utcnow() - timedelta(days=days_ago)
                elif len(parts) >= 2 and parts[0].isdigit() and 'week' in parts[1]:
                    weeks_ago = int(parts[0])
                    return datetime.utcnow() - timedelta(weeks=weeks_ago)
                elif len(parts) >= 2 and parts[0].isdigit() and 'month' in parts[1]:
                    months_ago = int(parts[0])
                    # Approximate month as 30 days
                    return datetime.utcnow() - timedelta(days=months_ago * 30)
                elif len(parts) >= 2 and parts[0].isdigit() and 'year' in parts[1]:
                    years_ago = int(parts[0])
                    # Approximate year as 365 days
                    return datetime.utcnow() - timedelta(days=years_ago * 365)
            except Exception as e:
                logger.warning(f"Error parsing relative date '{date_str}': {str(e)}")
                return default or datetime.utcnow()
            
        # Try common date formats
        date_formats = [
            '%Y-%m-%dT%H:%M:%S%z',  # ISO 8601 with timezone
            '%Y-%m-%dT%H:%M:%S',     # ISO 8601 without timezone
            '%Y-%m-%d %H:%M:%S',     # SQL datetime
            '%Y-%m-%d',              # Date only
            '%d/%m/%Y %H:%M:%S',     # Common in Brazil
            '%d/%m/%Y',              # Common in Brazil (date only)
            '%a, %d %b %Y %H:%M:%S %z',  # RFC 822 with timezone
            '%a, %d %b %Y %H:%M:%S GMT',  # RFC 822 GMT
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        # If we get here, parsing failed
        logger.warning(f"Failed to parse date string: {date_str}")
        return default or datetime.utcnow()
        
    async def fetch_news_links(self, query: str, country: str = 'BR') -> List[Dict[str, Any]]:
        """Fetch news links from SerpAPI.
        
        Args:
            query: Search query.
            country: Country code (default: 'BR' for Brazil).
            
        Returns:
            List of news items with basic information.
        """
        # Configure request parameters
        params = {'q': query}
        
        # Configure headers
        headers = {
            'X-API-KEY': self.serpapi_key,
            'Content-Type': 'application/json'
        }
        
        # Log request for debugging
        logger.debug(f"Sending request to: {self.serpapi_url}")
        logger.debug(f"Headers: {headers}")
        logger.debug(f"Params: {params}")
        
        try:
            async with httpx.AsyncClient() as client:
                # Make POST request to news endpoint
                response = await client.post(
                    self.serpapi_url,
                    json=params,
                    headers=headers,
                    timeout=30.0
                )
                
                # Log response for debugging
                logger.debug(f"Status code: {response.status_code}")
                logger.debug(f"Response headers: {dict(response.headers)}")
                
                # Check for errors
                response.raise_for_status()
                
                # Extract data from response
                data = response.json()
                
                # Log received data for debugging
                logger.debug(f"API response: {data}")
                
                # Extract news items from response
                news_items = []
                if isinstance(data, dict):
                    if 'news' in data:
                        news_items = data['news']
                    elif 'news_results' in data:
                        news_items = data['news_results']
                    elif 'organic' in data:
                        news_items = data['organic']
                
                logger.info(f"Fetched {len(news_items)} news items for query: {query}")
                return news_items
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from SerpAPI (status {e.response.status_code}): {str(e)}")
            if hasattr(e, 'response') and hasattr(e.response, 'text'):
                logger.error(f"Response content: {e.response.text}")
            return []
        except Exception as e:
            logger.error(f"Error fetching news from SerpAPI: {str(e)}", exc_info=True)
            return []
    
    async def process_single_news(self, news_item: Dict[str, Any], country: str) -> bool:
        """Process a single news item.
        
        Args:
            news_item: News item data from SerpAPI.
            country: Country code.
            
        Returns:
            bool: True if the news item was processed successfully, False otherwise.
        """
        try:
            # Validate news_item is a dictionary
            if not isinstance(news_item, dict):
                logger.error(f"news_item is not a dictionary: {type(news_item)}")
                return False
                
            url = news_item.get('link') if hasattr(news_item, 'get') else None
            if not url:
                logger.warning("No URL found in news_item")
                return False
            
            # Check if news already exists
            mongodb_manager = None
            try:
                mongodb_manager = MongoDBManager()
                await mongodb_manager.connect_to_mongodb()
                
                async with mongodb_manager.get_db() as db:
                    existing = await db.news.find_one({"original_url": url})
                    if existing:
                        logger.debug(f"News already exists: {url}")
                        return False
            except Exception as db_error:
                logger.error(f"Error checking if news exists in database: {str(db_error)}", exc_info=True)
                return False
            finally:
                if mongodb_manager:
                    await mongodb_manager.close_mongodb_connection()
            
            # Process the news item
            logger.info(f"Processing news item: {url}")
            
            # Create a new MongoDBManager instance for saving
            mongodb_manager = MongoDBManager()
            try:
                await mongodb_manager.connect_to_mongodb()
                
                # Parse publish date with fallback to current time
                publish_date = self._parse_publish_date(
                    news_item.get('date') or news_item.get('publish_date'),
                    default=datetime.utcnow()
                )
                
                # Safely get source information
                source_name = ''
                source_domain = ''
                
                if isinstance(news_item, dict):
                    # Handle case where source is a dictionary
                    if isinstance(news_item.get('source'), dict):
                        source_name = news_item['source'].get('name', '')
                        source_domain = news_item.get('source_domain', '')
                    # Handle case where source is a string
                    elif isinstance(news_item.get('source'), str):
                        source_name = news_item['source']
                        source_domain = url.split('//')[-1].split('/')[0] if url else ''
                    
                    # Prepare news document
                    news_doc = {
                        'original_url': url,
                        'title': news_item.get('title', 'Sem título'),
                        'description': news_item.get('snippet', ''),
                        'source_name': source_name,
                        'source_domain': source_domain or url.split('//')[-1].split('/')[0] if url else '',
                        'published_at': publish_date,
                        'collection_date': datetime.utcnow(),
                        'country_focus': country.upper(),
                        'in_topic': False,
                        'metadata': {
                            'has_favicon': bool(news_item.get('favicon')),
                            'has_description': bool(news_item.get('snippet')),
                            'source': source_name
                        }
                    }
                else:
                    # If news_item is not a dictionary, create a minimal document
                    logger.warning(f"Unexpected news_item type: {type(news_item)}")
                    news_doc = {
                        'original_url': url,
                        'title': str(news_item)[:200],  # Truncate if too long
                        'description': '',
                        'source_name': 'Unknown',
                        'source_domain': url.split('//')[-1].split('/')[0] if url else 'unknown',
                        'published_at': publish_date,
                        'collection_date': datetime.utcnow(),
                        'country_focus': country.upper(),
                        'in_topic': False,
                        'metadata': {
                            'has_favicon': False,
                            'has_description': False,
                            'source': 'Unknown'
                        }
                    }
                
                # Save to database
                async with mongodb_manager.get_db() as db:
                    result = await db.news.insert_one(news_doc)
                    logger.info(f"Saved news with ID: {result.inserted_id}")
                    
                return True
                
            except Exception as e:
                logger.error(f"Error saving news to database: {str(e)}", exc_info=True)
                return False
                
            finally:
                if mongodb_manager:
                    await mongodb_manager.close_mongodb_connection()
                    
        except Exception as e:
            logger.error(f"Unexpected error in process_single_news: {str(e)}", exc_info=True)
            return False
    
    async def process_news_batch(self, query: str, country: str = 'BR') -> Dict[str, Any]:
        """Process a batch of news for a given query.
        
        Args:
            query: Search query.
            country: Country code (default: 'BR' for Brazil).
            
        Returns:
            Dictionary with processing results:
            {
                'total_processed': int,
                'successful': int,
                'failed': int,
                'errors': List[str]
            }
        """
        logger.info(f"Starting news collection for query: {query}")
        
        # Initialize results
        results = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'errors': []
        }
        
        try:
            # Fetch news links
            news_items = await self.fetch_news_links(query, country)
            if not news_items:
                logger.warning(f"No news items found for query: {query}")
                return results
                
            logger.info(f"Found {len(news_items)} news items to process")
            
            # Process each news item with semaphore to limit concurrency
            semaphore = asyncio.Semaphore(10)  # Limit to 10 concurrent requests
            
            async def process_with_semaphore(item):
                async with semaphore:
                    try:
                        success = await self.process_single_news(item, country)
                        return success, None
                    except Exception as e:
                        error_msg = f"Error processing {item.get('link', 'unknown')}: {str(e)}"
                        logger.error(error_msg, exc_info=True)
                        return False, error_msg
            
            # Process items in batches
            batch_size = 20
            for i in range(0, len(news_items), batch_size):
                batch = news_items[i:i + batch_size]
                batch_tasks = []
                
                for item in batch:
                    if 'link' in item:
                        batch_tasks.append(process_with_semaphore(item))
                
                # Process batch
                batch_results = await asyncio.gather(
                    *batch_tasks,
                    return_exceptions=True
                )
                
                # Process results
                for result in batch_results:
                    if isinstance(result, Exception):
                        results['failed'] += 1
                        results['errors'].append(str(result))
                    else:
                        success, error = result
                        if success:
                            results['successful'] += 1
                        else:
                            results['failed'] += 1
                            if error:
                                results['errors'].append(error)
                
                results['total_processed'] += len(batch_tasks)
                logger.info(f"Processed batch: {results}")
            
            logger.info(f"Completed processing {results['total_processed']} news items for query: {query}")
            return results
            
        except Exception as e:
            error_msg = f"Unexpected error in process_news_batch: {str(e)}"
            logger.error(error_msg, exc_info=True)
            results['errors'].append(error_msg)
            results['failed'] = len(news_items) - results['successful']
            return results

# Create a singleton instance
news_collector = NewsCollector()
