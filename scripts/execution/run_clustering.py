#!/usr/bin/env python3
"""
Script para executar a clusterização de notícias.
Pode ser usado como um job agendado (cron job) ou executado manualmente.
"""
import asyncio
import logging
import os
import sys
from datetime import datetime

# Adiciona o diretório raiz ao path para importações
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.ai.topic_cluster import TopicCluster
from app.core.database import mongodb_manager
from app.core.config import settings

# Configuração de logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format=settings.LOG_FORMAT,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("clustering.log")
    ]
)
logger = logging.getLogger(__name__)

async def run_clustering():
    """Executa o processo de clusterização."""
    logger.info("🚀 Iniciando processo de clusterização")
    start_time = datetime.now()
    
    try:
        # Inicializa o gerenciador do MongoDB
        await mongodb_manager.connect()
        
        # Executa a clusterização
        cluster = TopicCluster()
        await cluster.cluster_recent_news()
        
        # Fecha a conexão com o MongoDB
        await mongodb_manager.close()
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info(f"✅ Clusterização concluída com sucesso em {duration:.2f} segundos")
        return 0
        
    except Exception as e:
        logger.error(f"❌ Erro durante a clusterização: {str(e)}", exc_info=True)
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(run_clustering())
    sys.exit(exit_code)
