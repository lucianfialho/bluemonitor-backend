"""Topic clustering service for grouping related news articles."""
import logging
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
from datetime import datetime, timedelta
from bson import ObjectId
from sklearn.cluster import DBSCAN
from sklearn.metrics.pairwise import cosine_similarity

from app.core.config import settings
from app.core.database import mongodb_manager
from app.services.ai.processor import ai_processor

logger = logging.getLogger(__name__)

class TopicCluster:
    """Service for clustering news articles into topics."""
    
    def __init__(self):
        """Initialize the topic clustering service."""
        self.min_samples = 1  # Permite clusters menores
        self.eps = 0.9  # Aumentado para agrupar mais itens
        self.min_topic_size = 1  # Permite tópicos com apenas 1 artigo
        self.max_topic_age_days = 30  # Período maior para análise
        self.max_articles_to_process = 1000  # Aumentado para incluir mais artigos
        self.similarity_threshold = 0.4  # Reduzido para agrupar tópicos mais diversos
    
    async def cluster_recent_news(self, country: str = 'BR') -> None:
        """Cluster recent news articles into topics.
        
        Args:
            country: Country code to filter news (default: 'BR' for Brazil).
        """
        logger.info(f"Starting topic clustering for {country}...")
        
        try:
            # Get recent news that haven't been clustered yet
            async with mongodb_manager.get_db() as db:
                # Primeiro, verificar quantos artigos existem no total
                total_articles = await db.news.count_documents({})
                logger.info(f"Total de artigos no banco: {total_articles}")
                
                # Verificar quantos artigos têm embeddings
                with_embeddings = await db.news.count_documents({"embedding": {"$exists": True, "$ne": None}})
                logger.info(f"Artigos com embeddings: {with_embeddings}")
                
                # Verificar quantos artigos já estão em tópicos
                in_topic = await db.news.count_documents({"in_topic": True})
                logger.info(f"Artigos já em tópicos: {in_topic}")
                
                # Consulta mais abrangente para depuração
                query = {
                    "country_focus": country.upper(),
                    "embedding": {"$exists": True, "$ne": None},
                    "in_topic": {"$ne": True}
                }
                
                logger.info(f"Querying news with filter: {query}")
                count = await db.news.count_documents(query)
                logger.info(f"Found {count} articles matching the query")
                
                # Se ainda não encontrou, tentar sem o filtro de país para depuração
                if count == 0:
                    query = {"embedding": {"$exists": True, "$ne": None}}
                    count = await db.news.count_documents(query)
                    logger.info(f"Found {count} articles with embeddings (without country filter)")
                
                logger.debug(f"Querying news with filter: {query}")
                
                # Ordenar por data de publicação (mais recentes primeiro)
                recent_news = await db.news.find(query) \
                    .sort("publish_date", -1) \
                    .limit(self.max_articles_to_process) \
                    .to_list(length=None)
                logger.debug(f"Found {len(recent_news)} articles to process")
                
                if not recent_news:
                    logger.info("No new articles to cluster")
                    return
                
                logger.info(f"Found {len(recent_news)} new articles to cluster")
                
                # Get embeddings for clustering
                article_embeddings = []
                valid_articles = []
                
                for article in recent_news:
                    if 'embedding' in article and article['embedding']:
                        article_embeddings.append(article['embedding'])
                        valid_articles.append(article)
                
                if not valid_articles:
                    logger.warning("No valid embeddings found for clustering")
                    return
            
                # Convert to numpy array
                X = np.array(article_embeddings)
                
                # Cluster using DBSCAN with cosine distance
                from sklearn.preprocessing import normalize
                
                # Normalizar os vetores para terem norma 1 (melhora a clusterização com cosseno)
                X_normalized = normalize(X)
                
                # Usar um valor fixo de eps para consistência
                # Valores mais altos criam clusters maiores, valores mais baixos criam mais clusters
                dynamic_eps = self.eps
                
                # Ajustar dinamicamente com base no número de artigos
                n_articles = len(X_normalized)
                
                # Ajustar eps com base no número de artigos
                if n_articles > 100:
                    dynamic_eps = min(0.95, self.eps * 1.2)  # Agrupar mais itens
                elif n_articles > 50:
                    dynamic_eps = min(0.9, self.eps * 1.1)
                else:
                    dynamic_eps = self.eps
                
                logger.info(f"Clustering {n_articles} articles with eps={dynamic_eps:.2f}, min_samples={self.min_samples}")
                logger.info(f"Similarity threshold: {self.similarity_threshold}")
                
                # Usar DBSCAN com métrica de cosseno
                clustering = DBSCAN(
                    eps=dynamic_eps,
                    min_samples=self.min_samples,
                    metric='cosine',
                    n_jobs=-1
                ).fit(X_normalized)
                
                # Se não encontrou clusters, tentar com parâmetros mais relaxados
                n_clusters = len(set(clustering.labels_)) - (1 if -1 in clustering.labels_ else 0)
                if n_clusters == 0 and n_articles > 0:
                    logger.warning("Nenhum cluster encontrado, tentando com parâmetros mais relaxados...")
                    clustering = DBSCAN(
                        eps=min(0.95, dynamic_eps * 1.2),  # Aumentar ainda mais o raio
                        min_samples=max(1, self.min_samples - 1),  # Reduzir min_samples se possível
                        metric='cosine',
                        n_jobs=-1
                    ).fit(X_normalized)
                
                # Get cluster labels
                labels = clustering.labels_
            
                # Process clusters
                n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
                logger.info(f"Found {n_clusters} clusters and {list(labels).count(-1)} noise points")
                
                # Group articles by cluster
                clusters: Dict[int, List[Dict[str, Any]]] = {}
                for i, label in enumerate(labels):
                    if label not in clusters:
                        clusters[label] = []
                    clusters[label].append(valid_articles[i])
                
                # Process each cluster
                for label, articles in clusters.items():
                    if label == -1 or len(articles) < self.min_topic_size:
                        # Skip noise and small clusters, but mark them as processed
                        article_ids = [article["_id"] for article in articles]
                        await db.news.update_many(
                            {"_id": {"$in": article_ids}},
                            {"$set": {"in_topic": True}}
                        )
                        continue
                        
                    # Process the cluster into a topic
                    await self._process_topic(articles, country)
            
            logger.info(f"Completed topic clustering for {len(valid_articles)} articles")
                
        except Exception as e:
            logger.error(f"Error in topic clustering: {str(e)}", exc_info=True)
            raise

    def _parse_date_string(self, date_str: str) -> Optional[datetime]:
        """Parse a date string in various formats to a timezone-naive datetime.
        
        Args:
            date_str: The date string to parse.
            
        Returns:
            A timezone-naive datetime or None if parsing fails.
        """
        from datetime import datetime, timezone
        import re
        
        if not date_str or not isinstance(date_str, str):
            return None
            
        # Remove any leading/trailing whitespace
        date_str = date_str.strip()
        
        # Common date formats to try
        formats = [
            '%Y-%m-%dT%H:%M:%S%z',  # ISO format with timezone
            '%Y-%m-%dT%H:%M:%S',     # ISO format without timezone
            '%Y-%m-%d %H:%M:%S',     # SQL format
            '%d/%m/%Y %H:%M',        # Common Brazilian format with time
            '%d/%m/%Y | %Hh%M',      # Format seen in the logs
            '%d/%m/%Y',              # Just date
            '%Y-%m-%d',              # ISO date
        ]
        
        # Try each format
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                # If timezone-aware, convert to UTC and make naive
                if hasattr(dt, 'tzinfo') and dt.tzinfo is not None:
                    dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
                return dt
            except (ValueError, AttributeError):
                continue
                
        # Try to extract date from complex strings
        try:
            # Look for common date patterns
            date_match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', date_str)
            if date_match:
                date_part = date_match.group(1)
                return self._parse_date_string(date_part)
        except Exception:
            pass
            
        return None
    
    def _get_article_date(self, article: Dict[str, Any]) -> datetime:
        """Get the publish date from an article, with fallback to current date if not available.
        
        Args:
            article: The article dictionary.
            
        Returns:
            The article's publish date or current date if not available, as timezone-naive UTC datetime.
        """
        from datetime import datetime, timezone
        
        publish_date = article.get('publish_date')
        
        # If no date or empty, use current time
        if not publish_date:
            return datetime.utcnow().replace(tzinfo=None)
        
        # If already a datetime object
        if isinstance(publish_date, datetime):
            dt = publish_date
            # If timezone-aware, convert to UTC and make naive
            if dt.tzinfo is not None:
                dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
            return dt
        
        # If string, try to parse it
        if isinstance(publish_date, str):
            parsed_date = self._parse_date_string(publish_date)
            if parsed_date is not None:
                return parsed_date
        
        # If we get here, we couldn't parse the date
        logger.warning(f"Could not parse date: {publish_date}")
        return datetime.utcnow().replace(tzinfo=None)
    
    async def _process_topic(self, articles: List[Dict[str, Any]], country: str) -> None:
        """Process a cluster of articles into a topic.
        
        Args:
            articles: List of articles in the cluster.
            country: Country code.
        """
        if not articles:
            logger.warning("No articles provided to process")
            return
            
        logger.info(f"Processing {len(articles)} articles for topic creation")
        
        try:
            # Process each article individually
            for article in articles:
                try:
                    # Skip if already in a topic
                    if article.get('in_topic'):
                        continue
                        
                    # Try to find a similar existing topic
                    similar_topic = await self._find_similar_topic(article, country)
                    
                    if similar_topic:
                        # Add to existing topic
                        await self._update_existing_topic(similar_topic, [article])
                        logger.info(f"Added article to existing topic: {article.get('title', 'No title')}")
                    else:
                        # Create new topic with this article as the main one
                        await self._create_new_topic(article, [article], country)
                        logger.info(f"Created new topic for article: {article.get('title', 'No title')}")
                            
                except Exception as e:
                    logger.error(f"Error processing article {article.get('_id')}: {str(e)}", exc_info=True)
            
            # Tentar mesclar tópicos similares após processar todos os artigos
            logger.info("Tentando mesclar tópicos similares...")
            await self._merge_similar_topics(country)
            
        except Exception as e:
            logger.error(f"Error in topic processing: {str(e)}", exc_info=True)
            raise
    
    async def _merge_similar_topics(self, country: str) -> None:
        """Tenta mesclar tópicos similares."""
        try:
            async with mongodb_manager.get_db() as db:
                # Busca todos os tópicos ativos
                topics = await db.topics.find({
                    "country_focus": country.upper(),
                    "is_active": True
                }).to_list(length=100)
                
                if len(topics) <= 1:
                    return
                
                # Para cada par de tópicos, verifica se são similares
                for i in range(len(topics)):
                    for j in range(i + 1, len(topics)):
                        topic1 = topics[i]
                        topic2 = topics[j]
                        
                        # Calcula a similaridade entre os tópicos
                        if 'embedding' not in topic1 or 'embedding' not in topic2:
                            continue
                            
                        similarity = cosine_similarity(
                            np.array(topic1['embedding']).reshape(1, -1),
                            np.array(topic2['embedding']).reshape(1, -1)
                        )[0][0]
                        
                        # Se a similaridade for maior que o limiar, mescla os tópicos
                        if similarity > self.similarity_threshold:
                            logger.info(f"Mesclando tópicos com similaridade {similarity:.2f}")
                            
                            # Atualiza o tópico1 com os artigos do tópico2
                            await db.topics.update_one(
                                {"_id": topic1['_id']},
                                {
                                    "$addToSet": {"articles": {"$each": topic2['articles']}},
                                    "$set": {
                                        "updated_at": datetime.utcnow(),
                                        "article_count": len(topic1['articles']) + len(topic2['articles'])
                                    }
                                }
                            )
                            
                            # Marca o tópico2 como inativo
                            await db.topics.update_one(
                                {"_id": topic2['_id']},
                                {"$set": {"is_active": False}}
                            )
                            
                            # Atualiza os artigos para apontar para o tópico1
                            await db.news.update_many(
                                {"topic_id": topic2['_id']},
                                {"$set": {"topic_id": topic1['_id']}}
                            )
                            
        except Exception as e:
            logger.error(f"Erro ao mesclar tópicos: {str(e)}", exc_info=True)
                
        except Exception as e:
            logger.error(f"Error processing topic: {str(e)}", exc_info=True)
    
    async def _find_similar_topic(
        self, 
        article: Dict[str, Any], 
        country: str
    ) -> Optional[Dict[str, Any]]:
        """Find a similar existing topic for the given article using semantic similarity.
        
        Args:
            article: The article to find a topic for.
            country: Country code.
            
        Returns:
            A matching topic document or None if not found.
        """
        try:
            if 'embedding' not in article or not article['embedding']:
                return None
                
            article_embedding = np.array(article['embedding']).reshape(1, -1)
            
            async with mongodb_manager.get_db() as db:
                # Buscar tópicos recentes (últimos 30 dias)
                min_date = datetime.utcnow() - timedelta(days=30)
                logger.info(f"Buscando tópicos desde {min_date}")
                
                recent_topics = await db.topics.find({
                    "country_focus": country.upper(),
                    "created_at": {
                        "$gte": min_date
                    },
                    "embedding": {"$exists": True, "$ne": None}
                }).to_list(length=100)
                
                if not recent_topics:
                    return None
                
                # Preparar embeddings dos tópicos
                topic_embeddings = []
                valid_topics = []
                
                for topic in recent_topics:
                    if 'embedding' in topic and topic['embedding'] is not None:
                        # Garantir que o embedding seja um array numpy 1D
                        emb = np.array(topic['embedding']).flatten()
                        if emb.shape[0] > 0:  # Verifica se o embedding não está vazio
                            topic_embeddings.append(emb)
                            valid_topics.append(topic)
                
                if not topic_embeddings:
                    return None
                
                # Converter para array numpy 2D (n_samples, n_features)
                topic_embeddings = np.vstack(topic_embeddings)
                
                # Garantir que o embedding do artigo tenha a mesma dimensionalidade
                article_embedding = article_embedding.reshape(1, -1)[:, :topic_embeddings.shape[1]]
                
                # Calcular similaridade de cosseno
                similarities = cosine_similarity(
                    article_embedding,
                    topic_embeddings
                )[0]
                
                # Encontrar o tópico mais similar acima do limiar
                max_similarity_idx = np.argmax(similarities)
                max_similarity = similarities[max_similarity_idx]
                
                logger.debug(f"Similaridade máxima encontrada: {max_similarity:.4f}")
                
                # Se a similaridade for maior que o limiar, retorna o tópico
                if max_similarity > self.similarity_threshold:
                    similar_topic = recent_topics[max_similarity_idx]
                    logger.info(f"Tópico similar encontrado: {similar_topic.get('title')} (similaridade: {max_similarity:.2f})")
                    return similar_topic
                
                return None
                
        except Exception as e:
            logger.error(f"Error finding similar topic: {str(e)}", exc_info=True)
            return None
    
    async def _update_existing_topic(
        self, 
        topic: Dict[str, Any], 
        articles: List[Dict[str, Any]]
    ) -> None:
        """Update an existing topic with new articles.
        
        Args:
            topic: The existing topic document.
            articles: New articles to add to the topic.
            
        Raises:
            ValueError: If the topic document is invalid or articles list is empty.
        """
        if not topic or '_id' not in topic:
            logger.error("Cannot update topic: invalid topic document")
            return
            
        if not articles:
            logger.warning("No articles provided to update topic")
            return
            
        logger.info(f"Updating topic {topic.get('_id')} with {len(articles)} new articles")
        
        try:
            async with mongodb_manager.get_db() as db:
                # Get existing article IDs and URLs to avoid duplicates
                existing_articles = topic.get('articles', [])
                
                # Se articles for uma lista de IDs, buscar os documentos completos
                if existing_articles and isinstance(existing_articles[0], str):
                    existing_articles = await db.news.find({
                        "_id": {"$in": [ObjectId(id_) for id_ in existing_articles]}
                    }).to_list(length=100)
                
                # Extrair URLs e IDs dos artigos existentes
                existing_article_urls = set(article.get('original_url', '') for article in existing_articles)
                existing_article_ids = set(str(article.get('_id', '')) for article in existing_articles)
                
                # Filtrar artigos que já estão no tópico
                new_articles = [
                    article for article in articles 
                    if article.get('original_url') not in existing_article_urls 
                    and str(article.get('_id', '')) not in existing_article_ids
                ]
                
                if not new_articles:
                    logger.info("No new articles to add to the topic")
                    return
                
                logger.info(f"Adding {len(new_articles)} new articles to topic {topic['_id']}")
                
                # Get existing article IDs
                existing_article_ids = set(str(id_) for id_ in topic.get('articles', []))
                
                # Get new article IDs that aren't already in the topic
                new_article_ids = []
                for article in articles:
                    if not article or '_id' not in article:
                        continue
                    article_id = str(article['_id'])
                    if article_id not in existing_article_ids:
                        new_article_ids.append(article_id)
                
                if not new_article_ids:
                    logger.info("No new articles to add to topic")
                    return
                    
                updated_article_ids = list(existing_article_ids.union(new_article_ids))
                
                # Get unique source names from new articles
                new_sources = set()
                for article in articles:
                    source = article.get('source_name')
                    if source:
                        new_sources.add(source)
                
                # Prepare update operations
                update_data = {
                    "$set": {
                        "articles": updated_article_ids,
                        "updated_at": datetime.utcnow(),
                        "article_count": len(updated_article_ids),
                        "last_updated": datetime.utcnow()
                    }
                }
                
                if new_sources:
                    update_data["$addToSet"] = {
                        "sources": {"$each": list(new_sources)}
                    }
                
                # Update topic
                result = await db.topics.update_one(
                    {"_id": topic['_id']},
                    update_data
                )
                
                if result.modified_count == 0:
                    logger.warning(f"No changes made to topic {topic['_id']}")
                
                # Update articles to mark them as processed
                article_ids = [article["_id"] for article in articles if "_id" in article]
                if article_ids:
                    update_result = await db.news.update_many(
                        {"_id": {"$in": article_ids}},
                        {"$set": {"in_topic": True, "topic_id": topic['_id']}}
                    )
                    logger.info(f"Updated {update_result.modified_count} articles with topic ID {topic['_id']}")
                
                logger.info(f"Successfully updated topic {topic['_id']} with {len(new_article_ids)} new articles")
                
        except Exception as e:
            logger.error(f"Error updating topic: {str(e)}", exc_info=True)
            raise
    
    async def _create_new_topic(
        self, 
        main_article: Dict[str, Any], 
        articles: List[Dict[str, Any]],
        country: str
    ) -> None:
        """Create a new topic from a cluster of articles.
        
        Args:
            main_article: The main article for the topic.
            articles: All articles in the topic.
            country: Country code.
            
        Raises:
            ValueError: If articles list is empty or main_article is not in articles.
        """
        if not articles:
            raise ValueError("Cannot create topic: no articles provided")
            
        # Ensure main_article is in the articles list
        if not any(str(a.get('_id')) == str(main_article.get('_id')) for a in articles):
            articles.insert(0, main_article)
            
        logger.info(f"Creating new topic with main article: {main_article.get('title')}")
        
        try:
            async with mongodb_manager.get_db() as db:
                # Check if any of these articles already belong to another topic
                article_ids = [str(article.get('_id')) for article in articles if article.get('_id')]
                
                # Find any existing topics that already contain these articles
                existing_topics = await db.topics.find({
                    "articles._id": {"$in": article_ids},
                    "is_active": True
                }).to_list(length=10)
                
                # If we found existing topics, add to the most similar one instead of creating a new one
                if existing_topics:
                    logger.info(f"Found {len(existing_topics)} existing topics with these articles")
                    # For now, just pick the first one - we'll improve this later
                    await self._update_existing_topic(existing_topics[0], articles)
                    return
                
                # Generate a summary for the topic using available content
                combined_content = []
                for article in articles:
                    title = article.get('extracted_title', article.get('serpapi_title', ''))
                    summary = article.get('summary', article.get('serpapi_snippet', ''))
                    if title or summary:
                        combined_content.append(f"{title}\n{summary}")
                
                combined_text = "\n\n".join(combined_content)
                topic_summary = ""
                
                if combined_text:
                    try:
                        topic_summary = await ai_processor.summarize_text(combined_text, max_length=200)
                        logger.debug(f"Generated topic summary: {topic_summary[:100]}...")
                    except Exception as e:
                        logger.error(f"Error generating topic summary: {str(e)}", exc_info=True)
                        # Fallback to first few sentences of the main article summary
                        topic_summary = main_article.get('summary', main_article.get('serpapi_snippet', ''))[:200]
                
                # Create topic document
                topic_doc = {
                    "name": main_article.get('extracted_title', 'Sem título'),
                    "title": main_article.get('extracted_title', 'Sem título'),
                    "summary": topic_summary,
                    "articles": [str(a['_id']) for a in articles],
                    "article_count": len(articles),
                    "sources": list({a.get('source_name', '') for a in articles if a.get('source_name')}),
                    "country_focus": country.upper(),
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                    "is_active": True,
                    "embedding": main_article.get('embedding'),
                    "main_article_id": str(main_article.get('_id', '')),
                    "first_seen": self._get_article_date(main_article),
                    "last_updated": datetime.utcnow()
                }
                
                # Save topic
                result = await db.topics.insert_one(topic_doc)
                topic_id = result.inserted_id
                
                # Update articles to mark them as processed
                await db.news.update_many(
                    {"_id": {"$in": [article["_id"] for article in articles]}},
                    {"$set": {"in_topic": True, "topic_id": topic_id}}
                )
                
                logger.info(f"Created new topic {topic_id} with {len(articles)} articles")
                
        except Exception as e:
            logger.error(f"Error creating new topic: {str(e)}", exc_info=True)
            raise

# Create a singleton instance
topic_cluster = TopicCluster()
