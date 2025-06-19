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
from app.services.ai.navigation import navigation_system
from app.services.web_scraper import ArticleExtractor
from app.core.utils import parse_date_string

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
        """Process a single news item WITH AI PROCESSING.
        
        Args:
            news_item: News item data from SerpAPI.
            country: Country code.
            
        Returns:
            True if processed successfully, False otherwise.
        """
        mongodb_manager = MongoDBManager()
        
        try:
            await mongodb_manager.connect_to_mongodb()
            
            async with mongodb_manager.get_db() as db:
                # Verificar se o artigo já existe
                existing = await db.news.find_one({
                    "$or": [
                        {"url": news_item.get("link")},
                        {"title": news_item.get("title")}
                    ]
                })
                
                if existing:
                    logger.debug(f"Article already exists: {news_item.get('title', 'Unknown')}")
                    return True
                
                # Buscar conteúdo completo do artigo
                article_content = await self.fetch_article_content(news_item.get("link"))
                
                if not article_content:
                    logger.warning(f"Failed to fetch content for: {news_item.get('link')}")
                    return False
                
                # Preparar conteúdo para processamento AI
                content_for_ai = f"{article_content.get('title', '')}\n\n{article_content.get('content', '')}"
                
                if len(content_for_ai.strip()) < 50:
                    logger.warning(f"Content too short for AI processing: {len(content_for_ai)} chars")
                    return False
                
                # ✅ PROCESSAMENTO AI - ESTA É A PARTE QUE ESTAVA FALTANDO!
                logger.info(f"🧠 Processing with AI: {article_content.get('title', 'Unknown')[:50]}...")
                ai_result = await process_news_content(content_for_ai)
                
                # Verificar se o AI processamento foi bem-sucedido
                if not ai_result.get('embedding') or len(ai_result.get('embedding', [])) == 0:
                    logger.error(f"❌ AI processing failed to generate embedding for: {news_item.get('link')}")
                    # Continuar mesmo sem embedding, mas registrar o erro
                
                # Preparar documento para MongoDB
                news_doc = {
                    "title": article_content.get("title", news_item.get("title", "")),
                    "url": news_item.get("link"),
                    "original_url": news_item.get("link"),
                    "content": article_content.get("content", ""),
                    "description": article_content.get("description", news_item.get("snippet", "")),
                    "source": {
                        "name": article_content.get("source", ""),
                        "domain": article_content.get("domain", ""),
                        "favicon": article_content.get("favicon", "")
                    },
                    "publish_date": parse_date_string(news_item.get("date")),
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                    "country": country,
                    "language": "pt-br",
                    
                    # ✅ RESULTADOS DO PROCESSAMENTO AI
                    "ai_processed": True,
                    "individual_summary": ai_result.get("individual_summary", ""),
                    "embedding": ai_result.get("embedding", []),
                    "processing_errors": ai_result.get("processing_errors", []),
                    "processed_at": ai_result.get("processed_at", datetime.utcnow()),
                    
                    # Campos de status
                    "clustered": False,
                    "status": "active"
                }
                
                # Adicionar erros de processamento se houver
                if ai_result.get("processing_errors"):
                    news_doc["processing_error"] = f"AI processing had errors: {ai_result['processing_errors']}"
                
                # Inserir no banco de dados
                result = await db.news.insert_one(news_doc)
                
                logger.info(f"✅ Processed and saved: {news_doc['title'][:50]}...")
                logger.debug(f"   - Embedding dimensions: {len(ai_result.get('embedding', []))}")
                logger.debug(f"   - Summary length: {len(ai_result.get('individual_summary', ''))}")
                logger.debug(f"   - MongoDB ID: {result.inserted_id}")
                
                return True
                
        except Exception as e:
            logger.error(f"❌ Error processing article {news_item.get('link', 'unknown')}: {str(e)}", exc_info=True)
            return False
            
        finally:
            await mongodb_manager.close_mongodb_connection()  
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
    
    async def fetch_article_content(self, url: str) -> Optional[Dict[str, Any]]:
        """Fetch ONLY main article content, avoiding navigation and sidebar noise."""
        if not url:
            logger.warning("Empty URL provided for content fetching")
            return None
        try:
            logger.debug(f"Fetching content from: {url}")
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            }
            async with httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
                http2=False
            ) as client:
                try:
                    response = await client.get(url, headers=headers)
                    response.raise_for_status()
                except (httpx.HTTPError, httpx.RequestError) as e:
                    logger.warning(f"Request failed for {url}: {str(e)}")
                    return None
                html_content = response.text
                if not html_content or len(html_content) < 100:
                    logger.warning(f"Received very short content from {url}")
                    return None
                if not any(tag in html_content.lower() for tag in ['<html', '<body', '<div', '<p']):
                    logger.warning(f"Content doesn't appear to be HTML for {url}")
                    return None
                # Usa o extrator modular
                extractor = ArticleExtractor(html_content)
                article_data = extractor.extract_article_data()
                from urllib.parse import urlparse
                parsed_url = urlparse(url)
                domain = parsed_url.netloc
                article_data['domain'] = domain
                article_data['url'] = url
                article_data['source'] = domain
                logger.debug(f"Clean extraction results for {url}:")
                logger.debug(f"  Title: {len(article_data.get('title') or '')} chars")
                logger.debug(f"  Content: {len(article_data.get('content') or '')} chars")
                logger.debug(f"  Description: {len(article_data.get('description') or '')} chars")
                if article_data.get('content') and len(article_data['content']) > 4000:
                    logger.warning(f"Content might include navigation elements: {len(article_data['content'])} chars from {url}")
                return article_data
        except Exception as e:
            logger.error(f"Error fetching article content from {url}: {str(e)}", exc_info=True)
            return None

# Create a singleton instance
news_collector = NewsCollector()
