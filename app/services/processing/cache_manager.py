"""
Gerenciador de cache para o sistema de processamento.
"""
import logging
from typing import Optional, List, Dict, Any
import asyncio

logger = logging.getLogger(__name__)

class CacheManager:
    """Gerenciador de cache simples."""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis = None
        self.cache_ttl = 3600 * 24  # 24 horas
        self._memory_cache = {}  # Cache em memória como fallback
    
    async def initialize(self) -> None:
        """Inicializa conexão com cache."""
        try:
            # Tentar usar Redis se disponível
            import aioredis
            self.redis = await aioredis.from_url(self.redis_url)
            await self.redis.ping()
            logger.info("Cache Redis inicializado")
        except Exception as e:
            logger.warning(f"Redis não disponível, usando cache em memória: {str(e)}")
            self.redis = self._memory_cache  # Fallback para dict em memória
    
    async def get_embedding(self, text_hash: str) -> Optional[List[float]]:
        """Obtém embedding do cache."""
        try:
            if isinstance(self.redis, dict):
                return self.redis.get(f"embedding:{text_hash}")
            
            # Redis real
            cached = await self.redis.get(f"embedding:{text_hash}")
            if cached:
                import pickle
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
            
            # Redis real
            import pickle
            serialized = pickle.dumps(embedding)
            await self.redis.setex(f"embedding:{text_hash}", self.cache_ttl, serialized)
        except Exception as e:
            logger.error(f"Erro ao salvar embedding no cache: {str(e)}")
    
    async def get_classification(self, article_hash: str) -> Optional[Dict[str, Any]]:
        """Obtém classificação do cache."""
        try:
            if isinstance(self.redis, dict):
                return self.redis.get(f"classification:{article_hash}")
            
            # Redis real
            cached = await self.redis.get(f"classification:{article_hash}")
            if cached:
                import pickle
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
            
            # Redis real
            import pickle
            serialized = pickle.dumps(classification)
            await self.redis.setex(f"classification:{article_hash}", self.cache_ttl, serialized)
        except Exception as e:
            logger.error(f"Erro ao salvar classificação no cache: {str(e)}")
    
    async def close(self) -> None:
        """Fecha conexão com cache."""
        if self.redis and hasattr(self.redis, 'close'):
            await self.redis.close()
