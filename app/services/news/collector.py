"""News collection service."""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

import httpx
from bs4 import BeautifulSoup

from app.core.config import settings
from app.core.database import mongodb_manager
from app.services.ai.processor import process_news_content

logger = logging.getLogger(__name__)

class NewsCollector:
    """Service for collecting news from various sources."""
    
    def __init__(self):
        """Initialize the news collector."""
        self.serpapi_url = settings.SERPAPI_ENDPOINT
        self.serpapi_key = settings.SERPAPI_KEY
        self.max_articles = settings.MAX_NEWS_ARTICLES_PER_QUERY
        
    async def fetch_news_links(self, query: str, country: str = 'BR') -> List[Dict[str, Any]]:
        """Fetch news links from SerpAPI.
        
        Args:
            query: Search query.
            country: Country code (default: 'BR' for Brazil).
            
        Returns:
            List of news items with basic information.
        """
        params = {
            'api_key': self.serpapi_key,
            'q': query,
            'gl': country.lower(),
            'hl': 'pt-br',
            'num': self.max_articles,
            'tbm': 'nws',
            'date_restrict': 'w'  # Last week
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(self.serpapi_url, json=params)
                response.raise_for_status()
                data = response.json()
                
                # Use 'news' instead of 'news_results' to match the API response
                news_items = data.get('news', [])
                logger.info(f"Fetched {len(news_items)} news items for query: {query}")
                return news_items
                
        except Exception as e:
            logger.error(f"Error fetching news from SerpAPI: {str(e)}")
            return []
    
    async def fetch_article_content(self, url: str) -> Optional[Dict[str, Any]]:
        """Fetch and extract article content from a URL.
        
        Args:
            url: The URL of the article.
            
        Returns:
            Dictionary with extracted content or None if extraction fails.
        """
        logger.info(f"Fetching content from URL: {url}")
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
            }
            
            try:
                # Tenta com HTTP/2 primeiro, se disponível
                try:
                    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, http2=True) as client:
                        logger.debug(f"Making HTTP/2 request to: {url}")
                        response = await client.get(url, headers=headers)
                        response.raise_for_status()
                except Exception as http2_error:
                    # Se falhar, tenta com HTTP/1.1
                    logger.debug(f"HTTP/2 request failed, falling back to HTTP/1.1: {str(http2_error)}")
                    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, http2=False) as client:
                        logger.debug(f"Making HTTP/1.1 request to: {url}")
                        response = await client.get(url, headers=headers)
                        response.raise_for_status()
                        
                        logger.debug(f"Response status: {response.status_code}")
                        
                        # Try to detect encoding
                        content_type = response.headers.get('content-type', '').lower()
                        if 'charset=' in content_type:
                            encoding = content_type.split('charset=')[-1].split(';')[0].strip()
                        else:
                            encoding = 'utf-8'  # Default to UTF-8
                        
                        logger.debug(f"Detected encoding: {encoding}")
                        
                        # Parse the HTML
                        try:
                            html_content = response.text
                            soup = BeautifulSoup(html_content, 'lxml')
                        except Exception as parse_error:
                            logger.error(f"Error parsing HTML from {url}: {str(parse_error)}")
                            return None
                        
                        # Extract title
                        title = 'No title'
                        if soup.title and soup.title.string:
                            title = soup.title.string.strip()
                        
                        logger.debug(f"Extracted title: {title}")
                        
                        # Try to find the main content
                        article = None
                        
                        # Try common article selectors
                        selectors = [
                            'article',
                            'main',
                            'div.article',
                            'div.post',
                            'div.content',
                            'div.main-content',
                            'div.entry-content',
                            'div.story',
                            'div.article-body'
                        ]
                        
                        for selector in selectors:
                            article = soup.select_one(selector)
                            if article:
                                logger.debug(f"Found content with selector: {selector}")
                                break
                        
                        # If still no article, try to find the main content by text density
                        if not article:
                            logger.debug("No article found with common selectors, trying to find main content")
                            article = soup.body or soup
                        
                        # Extract text from paragraphs
                        paragraphs = article.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li'])
                        content_parts = []
                        
                        for p in paragraphs:
                            text = p.get_text(strip=True)
                            if text and len(text) > 10:  # Skip very short paragraphs
                                # Add double newlines before headings for better readability
                                if p.name and p.name.startswith('h'):
                                    content_parts.append('\n\n' + text + '\n' + '=' * len(text) + '\n')
                                else:
                                    content_parts.append(text)
                        
                        content = '\n'.join(content_parts).strip()
                        
                        if not content:
                            logger.warning(f"No content extracted from {url}")
                            return None
                        
                        logger.debug(f"Extracted {len(content)} characters of content")
                        
                        # Try to extract publish date
                        publish_date = None
                        
                        # Try various ways to find the publish date
                        date_selectors = [
                            'time[datetime]',
                            'meta[property="article:published_time"]',
                            'meta[property="og:published_time"]',
                            'meta[name="publish_date"]',
                            'meta[name="pubdate"]',
                            'meta[itemprop="datePublished"]',
                            'span.date',
                            'div.date',
                            'span.published',
                            'time.published'
                        ]
                        
                        for selector in date_selectors:
                            try:
                                if 'meta' in selector:
                                    meta = soup.select_one(selector)
                                    if meta and 'content' in meta.attrs:
                                        publish_date = meta['content']
                                        break
                                else:
                                    time_el = soup.select_one(selector)
                                    if time_el and 'datetime' in time_el.attrs:
                                        publish_date = time_el['datetime']
                                        break
                                    elif time_el:
                                        publish_date = time_el.get_text(strip=True)
                                        break
                            except Exception as date_error:
                                logger.debug(f"Error extracting date with selector {selector}: {str(date_error)}")
                        
                        if publish_date:
                            logger.debug(f"Extracted publish date: {publish_date}")
                        
                        return {
                            'title': title,
                            'content': content,
                            'publish_date': publish_date,
                            'url': url,
                            'source': url.split('/')[2] if '/' in url else url
                        }
                    
            except httpx.HTTPStatusError as http_err:
                logger.error(f"HTTP error {http_err.response.status_code} while fetching {url}")
                return None
                
            except (httpx.RequestError, httpx.TimeoutException) as req_err:
                logger.error(f"Request error while fetching {url}: {str(req_err)}")
                return None
                
        except Exception as e:
            logger.error(f"Unexpected error while processing {url}: {str(e)}", exc_info=True)
            return None
    
    async def process_news_batch(self, query: str, country: str = 'BR') -> None:
        """Process a batch of news for a given query.
        
        Args:
            query: Search query.
            country: Country code (default: 'BR' for Brazil).
        """
        logger.info(f"Starting news collection for query: {query}")
        
        # Fetch news links
        news_items = await self.fetch_news_links(query, country)
        
        # Process each news item
        tasks = []
        for item in news_items:
            if 'link' in item:
                tasks.append(self.process_single_news(item, country))
        
        # Run tasks concurrently
        await asyncio.gather(*tasks, return_exceptions=True)
        
        logger.info(f"Completed processing {len(tasks)} news items for query: {query}")
    
    async def process_single_news(self, news_item: Dict[str, Any], country: str) -> None:
        """Process a single news item.
        
        Args:
            news_item: News item data from SerpAPI.
            country: Country code.
        """
        try:
            # Validate news_item is a dictionary
            if not isinstance(news_item, dict):
                logger.error(f"news_item is not a dictionary: {type(news_item)}")
                return
                
            url = news_item.get('link') if hasattr(news_item, 'get') else None
            if not url:
                logger.warning("No URL found in news_item")
                return
            
            # Check if news already exists
            try:
                async with mongodb_manager.get_db() as db:
                    existing = await db.news.find_one({"original_url": url})
                    if existing:
                        logger.debug(f"News already exists: {url}")
                        return
            except Exception as db_error:
                logger.error(f"Error checking if news exists in database: {str(db_error)}")
                return
            
            # Fetch and process article content
            logger.info(f"Fetching article content from: {url}")
            try:
                article_data = await self.fetch_article_content(url)
                
                # Validate article_data
                if not article_data:
                    logger.warning(f"No article data returned for URL: {url}")
                    return
                    
                if not isinstance(article_data, dict):
                    logger.error(f"Article data is not a dictionary: {type(article_data)}")
                    return
                    
                if 'content' not in article_data:
                    logger.error(f"No 'content' key in article data for URL: {url}")
                    return
                    
                # Ensure content is a non-empty string
                content_text = str(article_data.get('content', '')).strip()
                if not content_text:
                    logger.warning(f"Empty content for URL: {url}")
                    return
                    
                # Process with AI (summarization and embedding)
                logger.info(f"Processing content with AI for URL: {url}")
                
                # Safely get values with proper error handling
                def safe_get(data, key, default=''):
                    if not isinstance(data, dict):
                        return default
                    return data.get(key, default)
                
                # Prepare base news document before AI processing
                news_doc = {
                    'original_url': url,
                    'serpapi_title': safe_get(news_item, 'title'),
                    'extracted_title': safe_get(article_data, 'title', 'No title'),
                    'source_name': safe_get(safe_get(news_item, 'source', {}), 'name'),
                    'serpapi_snippet': safe_get(news_item, 'snippet'),
                    'extracted_content': content_text,
                    'publish_date': safe_get(article_data, 'publish_date'),
                    'collection_date': datetime.utcnow(),
                    'country_focus': country.upper(),
                    'query_source': safe_get(news_item, 'query'),
                    'in_topic': False  # Initialize as not in any topic
                }
                
                # Try to process with AI
                try:
                    processed_data = await process_news_content(content_text)
                    
                    # Add processed data if available
                    if processed_data and isinstance(processed_data, dict):
                        news_doc.update({
                            'summary': processed_data.get('individual_summary', ''),
                            'embedding': processed_data.get('embedding', []),
                            'processed_at': processed_data.get('processed_at', datetime.utcnow()),
                            'language': processed_data.get('language', 'pt-br')
                        })
                except Exception as ai_error:
                    error_msg = f"AI processing failed: {str(ai_error)}"
                    logger.error(f"Error processing article with AI for URL {url}: {error_msg}", exc_info=True)
                    # Add error information to the document
                    news_doc['processing_error'] = error_msg
                    
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Error processing article data for URL {url}: {error_msg}", exc_info=True)
                
                # Create a minimal document with the error
                news_doc = {
                    'original_url': url,
                    'serpapi_title': safe_get(news_item, 'title'),
                    'extracted_title': safe_get(article_data, 'title', 'No title') if isinstance(article_data, dict) else 'No title',
                    'source_name': safe_get(safe_get(news_item, 'source', {}), 'name'),
                    'serpapi_snippet': safe_get(news_item, 'snippet'),
                    'extracted_content': safe_get(article_data, 'content', '') if isinstance(article_data, dict) else str(article_data)[:1000],
                    'publish_date': safe_get(article_data, 'publish_date') if isinstance(article_data, dict) else None,
                    'collection_date': datetime.utcnow(),
                    'country_focus': country.upper(),
                    'query_source': safe_get(news_item, 'query'),
                    'processing_error': f"Article processing failed: {error_msg}",
                    'in_topic': False  # Initialize as not in any topic
                }
            
            # Save to database
            try:
                async with mongodb_manager.get_db() as db:
                    result = await db.news.insert_one(news_doc)
                    logger.info(f"Saved news: {url} (ID: {result.inserted_id})")
            except Exception as db_error:
                logger.error(f"Error saving news to database: {str(db_error)}", exc_info=True)
            
        except Exception as e:
            logger.error(f"Unexpected error processing news {url}: {str(e)}", exc_info=True)

# Create a singleton instance
news_collector = NewsCollector()
