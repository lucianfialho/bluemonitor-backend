"""
Sistema otimizado para processamento em lote de milhares de notícias.

Este arquivo deve ser salvo como: app/services/processing/batch_processor.py
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional, AsyncGenerator, Callable
from datetime import datetime, timedelta
import numpy as np
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import multiprocessing as mp
from functools import partial
import time
import psutil
from collections import deque
import aioredis
import pickle

logger = logging.getLogger(__name__)

@dataclass
class BatchConfig:
    """Configuração para processamento em lote."""
    batch_size: int = 100
    max_concurrent_batches: int = 4
    chunk_size: int = 10
    timeout_seconds: int = 300
    memory_threshold_gb: float = 4.0
    cpu_threshold_percent: float = 80.0
    retry_failed_items: bool = True
    max_retries: int = 3

@dataclass
class ProcessingMetrics:
    """Métricas de processamento."""
    total_items: int = 0
    processed_items: int = 0
    failed_items: int = 0
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    processing_times: List[float] = field(default_factory=list)
    memory_usage: List[float] = field(default_factory=list)
    cpu_usage: List[float] = field(default_factory=list)
    
    @property
    def success_rate(self) -> float:
        """Taxa de sucesso."""
        if self.total_items == 0:
            return 0.0
        return (self.processed_items / self.total_items) * 100
    
    @property
    def avg_processing_time(self) -> float:
        """Tempo médio de processamento."""
        return np.mean(self.processing_times) if self.processing_times else 0.0
    
    @property
    def total_duration(self) -> float:
        """Duração total em segundos."""
        if not self.end_time:
            return (datetime.utcnow() - self.start_time).total_seconds()
        return (self.end_time - self.start_time).total_seconds()

class ResourceMonitor:
    """Monitor de recursos do sistema."""
    
    def __init__(self, check_interval: float = 1.0):
        self.check_interval = check_interval
        self.monitoring = False
        self.metrics_history = deque(maxlen=100)
    
    async def start_monitoring(self) -> None:
        """Inicia monitoramento."""
        self.monitoring = True
        while self.monitoring:
            metrics = {
                'timestamp': datetime.utcnow(),
                'memory_percent': psutil.virtual_memory().percent,
                'memory_gb': psutil.virtual_memory().used / (1024**3),
                'cpu_percent': psutil.cpu_percent(interval=0.1),
                'disk_percent': psutil.disk_usage('/').percent
            }
            self.metrics_history.append(metrics)
            await asyncio.sleep(self.check_interval)
    
    def stop_monitoring(self) -> None:
        """Para monitoramento."""
        self.monitoring = False
    
    def get_current_metrics(self) -> Dict[str, float]:
        """Obtém métricas atuais."""
        if not self.metrics_history:
            return {}
        return self.metrics_history[-1]
    
    def should_throttle(self, config: BatchConfig) -> bool:
        """Verifica se deve reduzir processamento."""
        current = self.get_current_metrics()
        
        memory_gb = current.get('memory_gb', 0)
        cpu_percent = current.get('cpu_percent', 0)
        
        return (
            memory_gb > config.memory_threshold_gb or 
            cpu_percent > config.cpu_threshold_percent
        )

class CacheManager:
    """Gerenciador de cache para embeddings e resultados."""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis = None
        self.cache_ttl = 3600 * 24  # 24 horas
    
    async def initialize(self) -> None:
        """Inicializa conexão Redis."""
        try:
            self.redis = await aioredis.from_url(self.redis_url)
            await self.redis.ping()
            logger.info("Cache Redis inicializado")
        except Exception as e:
            logger.warning(f"Redis não disponível, usando cache em memória: {str(e)}")
            self.redis = {}  # Fallback para dict em memória
    
    async def get_embedding(self, text_hash: str) -> Optional[List[float]]:
        """Obtém embedding do cache."""
        try:
            if isinstance(self.redis, dict):
                return self.redis.get(f"embedding:{text_hash}")
            
            cached = await self.redis.get(f"embedding:{text_hash}")
            if cached:
                return pickle.loads(cached)
            return None
        except Exception as e:
            logger.error(f"Erro ao obter embedding do cache: {str(e)}")
            return None
    
    async def set_embedding(self, text_hash: str, embedding: List[float]) -> None:
        """Salva embedding no cache."""
        try:
            if isinstance(self.redis, dict):
                self.redis[f"embedding:{text_hash}"] = embedding
                return
            
            serialized = pickle.dumps(embedding)
            await self.redis.setex(f"embedding:{text_hash}", self.cache_ttl, serialized)
        except Exception as e:
            logger.error(f"Erro ao salvar embedding no cache: {str(e)}")
    
    async def get_classification(self, article_hash: str) -> Optional[Dict[str, Any]]:
        """Obtém classificação do cache."""
        try:
            if isinstance(self.redis, dict):
                return self.redis.get(f"classification:{article_hash}")
            
            cached = await self.redis.get(f"classification:{article_hash}")
            if cached:
                return pickle.loads(cached)
            return None
        except Exception as e:
            logger.error(f"Erro ao obter classificação do cache: {str(e)}")
            return None
    
    async def set_classification(self, article_hash: str, classification: Dict[str, Any]) -> None:
        """Salva classificação no cache."""
        try:
            if isinstance(self.redis, dict):
                self.redis[f"classification:{article_hash}"] = classification
                return
            
            serialized = pickle.dumps(classification)
            await self.redis.setex(f"classification:{article_hash}", self.cache_ttl, serialized)
        except Exception as e:
            logger.error(f"Erro ao salvar classificação no cache: {str(e)}")

class BatchProcessor:
    """Processador otimizado para lotes de notícias."""
    
    def __init__(
        self,
        config: BatchConfig,
        cache_manager: Optional[CacheManager] = None
    ):
        self.config = config
        self.cache_manager = cache_manager
        self.resource_monitor = ResourceMonitor()
        self.metrics = ProcessingMetrics()
        self.failed_items = deque()
        
        # Pool de threads para I/O bound operations
        self.thread_pool = ThreadPoolExecutor(
            max_workers=min(32, (mp.cpu_count() or 1) + 4)
        )
        
        # Pool de processos para CPU intensive operations
        self.process_pool = ProcessPoolExecutor(
            max_workers=min(mp.cpu_count() or 1, self.config.max_concurrent_batches)
        )
    
    async def process_articles_batch(
        self,
        articles: List[Dict[str, Any]],
        processing_func: Callable,
        progress_callback: Optional[Callable] = None
    ) -> ProcessingMetrics:
        """
        Processa lote de artigos de forma otimizada.
        
        Args:
            articles: Lista de artigos para processar
            processing_func: Função de processamento
            progress_callback: Callback para progresso
            
        Returns:
            Métricas de processamento
        """
        self.metrics = ProcessingMetrics()
        self.metrics.total_items = len(articles)
        
        try:
            # Inicializar cache se disponível
            if self.cache_manager:
                await self.cache_manager.initialize()
            
            # Iniciar monitoramento
            monitor_task = asyncio.create_task(self.resource_monitor.start_monitoring())
            
            # Dividir em lotes
            batches = self._create_batches(articles)
            logger.info(f"Processando {len(articles)} artigos em {len(batches)} lotes")
            
            # Processar lotes com controle de concorrência
            semaphore = asyncio.Semaphore(self.config.max_concurrent_batches)
            
            async def process_single_batch(batch_articles):
                async with semaphore:
                    return await self._process_batch_with_monitoring(
                        batch_articles, processing_func, progress_callback
                    )
            
            # Executar todos os lotes
            batch_tasks = [process_single_batch(batch) for batch in batches]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Consolidar resultados
            self._consolidate_results(batch_results)
            
            # Processar itens que falharam (retry)
            if self.config.retry_failed_items and self.failed_items:
                await self._retry_failed_items(processing_func)
            
            self.metrics.end_time = datetime.utcnow()
            
            # Parar monitoramento
            self.resource_monitor.stop_monitoring()
            monitor_task.cancel()
            
            return self.metrics
            
        except Exception as e:
            logger.error(f"Erro no processamento em lote: {str(e)}")
            self.metrics.end_time = datetime.utcnow()
            self.resource_monitor.stop_monitoring()
            if 'monitor_task' in locals():
                monitor_task.cancel()
            raise
    
    def _create_batches(self, articles: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """Cria lotes otimizados baseados no tamanho e recursos."""
        # Ajustar tamanho do lote baseado nos recursos disponíveis
        available_memory_gb = psutil.virtual_memory().available / (1024**3)
        cpu_count = mp.cpu_count() or 1
        
        # Calcular tamanho ideal do lote
        ideal_batch_size = min(
            self.config.batch_size,
            max(10, int(available_memory_gb * 25)),  # ~25 artigos por GB
            len(articles) // max(1, cpu_count)
        )
        
        batches = []
        for i in range(0, len(articles), ideal_batch_size):
            batch = articles[i:i + ideal_batch_size]
            batches.append(batch)
        
        return batches
    
    async def _process_batch_with_monitoring(
        self,
        batch_articles: List[Dict[str, Any]],
        processing_func: Callable,
        progress_callback: Optional[Callable]
    ) -> Dict[str, Any]:
        """Processa um lote com monitoramento de recursos."""
        batch_start = time.time()
        batch_results = {
            'processed': 0,
            'failed': 0,
            'results': [],
            'errors': []
        }
        
        try:
            # Verificar se deve usar cache
            cached_results = []
            items_to_process = []
            
            if self.cache_manager:
                for article in batch_articles:
                    article_hash = self._get_article_hash(article)
                    cached = await self.cache_manager.get_classification(article_hash)
                    
                    if cached:
                        cached_results.append(cached)
                    else:
                        items_to_process.append(article)
            else:
                items_to_process = batch_articles
            
            # Processar itens não cachados
            if items_to_process:
                # Dividir em chunks menores para melhor controle
                chunks = self._create_chunks(items_to_process)
                
                for chunk in chunks:
                    # Verificar recursos antes de processar chunk
                    if self.resource_monitor.should_throttle(self.config):
                        logger.info("Throttling devido ao uso de recursos")
                        await asyncio.sleep(2)  # Pausa para recuperação
                    
                    chunk_results = await self._process_chunk(chunk, processing_func)
                    batch_results['results'].extend(chunk_results['results'])
                    batch_results['processed'] += chunk_results['processed']
                    batch_results['failed'] += chunk_results['failed']
                    batch_results['errors'].extend(chunk_results['errors'])
                    
                    # Salvar no cache se disponível
                    if self.cache_manager:
                        await self._cache_chunk_results(chunk, chunk_results['results'])
                    
                    # Callback de progresso
                    if progress_callback:
                        await progress_callback(chunk_results['processed'])
            
            # Adicionar resultados cachados
            batch_results['results'].extend(cached_results)
            batch_results['processed'] += len(cached_results)
            
            # Registrar métricas do lote
            batch_time = time.time() - batch_start
            self.metrics.processing_times.append(batch_time)
            
            current_metrics = self.resource_monitor.get_current_metrics()
            self.metrics.memory_usage.append(current_metrics.get('memory_gb', 0))
            self.metrics.cpu_usage.append(current_metrics.get('cpu_percent', 0))
            
            return batch_results
            
        except Exception as e:
            logger.error(f"Erro no processamento do lote: {str(e)}")
            batch_results['errors'].append(str(e))
            batch_results['failed'] = len(batch_articles)
            return batch_results
    
    def _create_chunks(self, articles: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """Cria chunks menores para processamento granular."""
        chunks = []
        for i in range(0, len(articles), self.config.chunk_size):
            chunk = articles[i:i + self.config.chunk_size]
            chunks.append(chunk)
        return chunks
    
    async def _process_chunk(
        self,
        chunk: List[Dict[str, Any]],
        processing_func: Callable
    ) -> Dict[str, Any]:
        """Processa um chunk de artigos."""
        chunk_results = {
            'processed': 0,
            'failed': 0,
            'results': [],
            'errors': []
        }
        
        # Processar itens do chunk concorrentemente
        tasks = []
        for article in chunk:
            task = asyncio.create_task(self._process_single_article(article, processing_func))
            tasks.append(task)
        
        # Aguardar conclusão com timeout
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=self.config.timeout_seconds
            )
            
            for result in results:
                if isinstance(result, Exception):
                    chunk_results['failed'] += 1
                    chunk_results['errors'].append(str(result))
                else:
                    chunk_results['processed'] += 1
                    chunk_results['results'].append(result)
                    
        except asyncio.TimeoutError:
            logger.error(f"Timeout no processamento do chunk ({self.config.timeout_seconds}s)")
            chunk_results['failed'] = len(chunk)
            chunk_results['errors'].append("Timeout no processamento")
        
        return chunk_results
    
    async def _process_single_article(
        self,
        article: Dict[str, Any],
        processing_func: Callable
    ) -> Dict[str, Any]:
        """Processa um único artigo."""
        try:
            # Verificar se função é async
            if asyncio.iscoroutinefunction(processing_func):
                result = await processing_func(article)
            else:
                # Executar em thread pool para funções síncronas
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    self.thread_pool, 
                    processing_func, 
                    article
                )
            
            return {
                'article_id': article.get('_id'),
                'result': result,
                'processing_time': time.time(),
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Erro no processamento do artigo {article.get('_id')}: {str(e)}")
            
            # Adicionar à lista de falhas para retry
            self.failed_items.append({
                'article': article,
                'error': str(e),
                'attempt': 1
            })
            
            raise e
    
    def _get_article_hash(self, article: Dict[str, Any]) -> str:
        """Gera hash único para o artigo."""
        content = article.get('extracted_content', '')
        url = article.get('original_url', '')
        return str(hash(f"{content[:100]}{url}"))
    
    async def _cache_chunk_results(
        self,
        chunk: List[Dict[str, Any]],
        results: List[Dict[str, Any]]
    ) -> None:
        """Salva resultados do chunk no cache."""
        try:
            for article, result in zip(chunk, results):
                if result.get('success'):
                    article_hash = self._get_article_hash(article)
                    await self.cache_manager.set_classification(article_hash, result)
        except Exception as e:
            logger.error(f"Erro ao salvar no cache: {str(e)}")
    
    def _consolidate_results(self, batch_results: List[Any]) -> None:
        """Consolida resultados de todos os lotes."""
        for result in batch_results:
            if isinstance(result, Exception):
                logger.error(f"Erro em lote: {str(result)}")
                continue
            
            if isinstance(result, dict):
                self.metrics.processed_items += result.get('processed', 0)
                self.metrics.failed_items += result.get('failed', 0)
    
    async def _retry_failed_items(self, processing_func: Callable) -> None:
        """Reprocessa itens que falharam."""
        retry_count = 0
        
        while self.failed_items and retry_count < self.config.max_retries:
            retry_count += 1
            logger.info(f"Tentativa de retry {retry_count}/{self.config.max_retries} para {len(self.failed_items)} itens")
            
            failed_to_retry = list(self.failed_items)
            self.failed_items.clear()
            
            for failed_item in failed_to_retry:
                if failed_item['attempt'] >= self.config.max_retries:
                    continue
                
                try:
                    await asyncio.sleep(0.1)  # Pequena pausa entre retries
                    await self._process_single_article(failed_item['article'], processing_func)
                    self.metrics.processed_items += 1
                    
                except Exception as e:
                    failed_item['attempt'] += 1
                    failed_item['error'] = str(e)
                    self.failed_items.append(failed_item)
    
    async def cleanup(self) -> None:
        """Limpa recursos."""
        self.thread_pool.shutdown(wait=True)
        self.process_pool.shutdown(wait=True)
        
        if self.cache_manager and hasattr(self.cache_manager.redis, 'close'):
            await self.cache_manager.redis.close()

class OptimizedNewsProcessor:
    """Processador otimizado específico para notícias."""
    
    def __init__(self, mongodb_manager, ai_processor):
        self.db_manager = mongodb_manager
        self.ai_processor = ai_processor
        self.cache_manager = CacheManager()
        
        # Configuração otimizada para notícias
        self.config = BatchConfig(
            batch_size=50,  # Menor para notícias (conteúdo extenso)
            max_concurrent_batches=3,
            chunk_size=5,
            timeout_seconds=600,  # Maior timeout para processamento de IA
            memory_threshold_gb=6.0,
            cpu_threshold_percent=85.0
        )
        
        self.batch_processor = BatchProcessor(self.config, self.cache_manager)
    
    async def process_news_collection(
        self,
        collection_size: int = 1000,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Processa coleção de notícias de forma otimizada.
        
        Args:
            collection_size: Número máximo de notícias para processar
            progress_callback: Callback para atualizações de progresso
            
        Returns:
            Estatísticas do processamento
        """
        try:
            # Buscar notícias não processadas
            articles = await self._get_unprocessed_articles(collection_size)
            
            if not articles:
                return {
                    'status': 'no_articles',
                    'message': 'Nenhuma notícia para processar'
                }
            
            logger.info(f"Iniciando processamento de {len(articles)} notícias")
            
            # Definir função de processamento
            async def process_article(article):
                return await self._process_single_news_article(article)
            
            # Executar processamento em lote
            metrics = await self.batch_processor.process_articles_batch(
                articles, process_article, progress_callback
            )
            
            # Gerar relatório
            report = self._generate_processing_report(metrics)
            
            return report
            
        except Exception as e:
            logger.error(f"Erro no processamento da coleção: {str(e)}")
            raise
        finally:
            await self.batch_processor.cleanup()
    
    async def _get_unprocessed_articles(self, limit: int) -> List[Dict[str, Any]]:
        """Busca artigos não processados."""
        try:
            async with self.db_manager.get_db() as db:
                query = {
                    "$or": [
                        {"embedding": {"$exists": False}},
                        {"embedding": None},
                        {"embedding": []},
                        {"processed_at": {"$exists": False}}
                    ]
                }
                
                cursor = db.news.find(query).limit(limit)
                articles = await cursor.to_list(length=limit)
                
                return articles
                
        except Exception as e:
            logger.error(f"Erro ao buscar artigos: {str(e)}")
            return []
    
    async def _process_single_news_article(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """Processa um único artigo de notícia."""
        try:
            start_time = time.time()
            
            # Extrair conteúdo
            content = article.get('extracted_content', '')
            if not content:
                content = article.get('serpapi_snippet', '')
            
            if not content:
                raise ValueError("Nenhum conteúdo encontrado para processar")
            
            # Verificar cache de embedding
            content_hash = str(hash(content))
            embedding = await self.cache_manager.get_embedding(content_hash)
            
            if not embedding:
                # Gerar embedding
                embedding = await self.ai_processor.get_embedding(content)
                
                if embedding:
                    # Salvar no cache
                    await self.cache_manager.set_embedding(content_hash, embedding)
            
            # Gerar resumo se necessário
            summary = article.get('summary')
            if not summary and len(content) > 200:
                summary = await self.ai_processor.summarize_text(content, max_length=150)
            
            # Atualizar artigo no banco
            update_data = {
                'embedding': embedding,
                'processed_at': datetime.utcnow(),
                'processing_time': time.time() - start_time
            }
            
            if summary:
                update_data['summary'] = summary
            
            async with self.db_manager.get_db() as db:
                await db.news.update_one(
                    {'_id': article['_id']},
                    {'$set': update_data}
                )
            
            return {
                'article_id': str(article['_id']),
                'embedding_generated': bool(embedding),
                'summary_generated': bool(summary),
                'processing_time': time.time() - start_time,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Erro no processamento do artigo {article.get('_id')}: {str(e)}")
            raise
    
    def _generate_processing_report(self, metrics: ProcessingMetrics) -> Dict[str, Any]:
        """Gera relatório de processamento."""
        return {
            'status': 'completed',
            'total_articles': metrics.total_items,
            'processed_successfully': metrics.processed_items,
            'failed_articles': metrics.failed_items,
            'success_rate': metrics.success_rate,
            'total_duration_seconds': metrics.total_duration,
            'avg_processing_time': metrics.avg_processing_time,
            'performance_metrics': {
                'avg_memory_usage_gb': np.mean(metrics.memory_usage) if metrics.memory_usage else 0,
                'peak_memory_usage_gb': max(metrics.memory_usage) if metrics.memory_usage else 0,
                'avg_cpu_usage_percent': np.mean(metrics.cpu_usage) if metrics.cpu_usage else 0,
                'peak_cpu_usage_percent': max(metrics.cpu_usage) if metrics.cpu_usage else 0
            },
            'throughput': {
                'articles_per_second': metrics.processed_items / max(metrics.total_duration, 1),
                'articles_per_minute': (metrics.processed_items / max(metrics.total_duration, 1)) * 60
            }
        }
    
    async def estimate_processing_time(self, article_count: int) -> Dict[str, float]:
        """Estima tempo de processamento para um número de artigos."""
        # Métricas base (podem ser calibradas com dados históricos)
        base_time_per_article = 2.0  # segundos por artigo
        embedding_time = 0.5  # tempo adicional para embedding
        summary_time = 0.3   # tempo adicional para resumo
        
        # Ajustes baseados em recursos
        cpu_factor = min(2.0, mp.cpu_count() / 4.0) if mp.cpu_count() else 1.0
        memory_gb = psutil.virtual_memory().total / (1024**3)
        memory_factor = min(1.5, memory_gb / 8.0)
        
        # Cálculo otimista, realista e pessimista
        base_total = article_count * base_time_per_article
        optimistic = base_total / (cpu_factor * memory_factor)
        realistic = base_total / cpu_factor
        pessimistic = base_total * 1.5
        
        return {
            'optimistic_seconds': optimistic,
            'realistic_seconds': realistic,
            'pessimistic_seconds': pessimistic,
            'optimistic_minutes': optimistic / 60,
            'realistic_minutes': realistic / 60,
            'pessimistic_minutes': pessimistic / 60
        }

# Exemplo de integração com sistema existente
async def integrate_with_existing_system():
    """Exemplo de integração com o sistema BlueMonitor existente."""
    
    # Mock dos componentes existentes
    class MockMongoDB:
        async def get_db(self):
            return self
        
        async def find(self, query):
            return self
        
        async def limit(self, n):
            return self
        
        async def to_list(self, length):
            # Simular artigos
            return [
                {
                    '_id': f'article_{i}',
                    'extracted_content': f'Conteúdo do artigo {i}',
                    'source_name': 'Fonte Teste'
                }
                for i in range(100)
            ]
        
        async def update_one(self, query, update):
            return type('Result', (), {'modified_count': 1})()
    
    class MockAIProcessor:
        async def get_embedding(self, text):
            # Simular delay de processamento
            await asyncio.sleep(0.1)
            return [0.1] * 384  # Embedding fake
        
        async def summarize_text(self, text, max_length=150):
            await asyncio.sleep(0.05)
            return text[:max_length] + "..."
    
    # Inicializar componentes
    mongodb_manager = MockMongoDB()
    ai_processor = MockAIProcessor()
    
    # Criar processador otimizado
    processor = OptimizedNewsProcessor(mongodb_manager, ai_processor)
    
    # Callback de progresso
    async def progress_callback(processed_count):
        print(f"Processados: {processed_count} artigos")
    
    # Processar notícias
    print("Iniciando processamento otimizado...")
    start_time = time.time()
    
    result = await processor.process_news_collection(
        collection_size=100,
        progress_callback=progress_callback
    )
    
    end_time = time.time()
    
    print(f"\nResultados do processamento:")
    print(f"Status: {result['status']}")
    print(f"Total processado: {result['processed_successfully']}/{result['total_articles']}")
    print(f"Taxa de sucesso: {result['success_rate']:.1f}%")
    print(f"Tempo total: {end_time - start_time:.2f}s")
    print(f"Throughput: {result['throughput']['articles_per_second']:.2f} artigos/s")

if __name__ == "__main__":
    asyncio.run(integrate_with_existing_system())