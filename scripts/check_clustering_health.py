#!/usr/bin/env python3
"""
Script para verificar a saúde do serviço de clusterização.
Verifica quando a última clusterização foi executada e se há erros recentes.
"""
import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta

# Adiciona o diretório raiz ao path para importações
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import mongodb_manager
from app.core.config import settings

# Configuração de logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format=settings.LOG_FORMAT,
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def check_clustering_health():
    """Verifica a saúde do serviço de clusterização."""
    try:
        # Conecta ao MongoDB
        await mongodb_manager.connect()
        db = mongodb_manager.get_db()
        
        # Verifica a última execução de clusterização
        last_run = await db.clustering_logs.find_one(
            {"type": "clustering_complete"},
            sort=[("timestamp", -1)]
        )
        
        if not last_run:
            logger.warning("⚠️ Nenhuma execução de clusterização encontrada")
            return 1
        
        last_run_time = last_run["timestamp"]
        time_since_last_run = datetime.utcnow() - last_run_time
        
        logger.info(f"🕒 Última clusterização: {last_run_time} (há {time_since_last_run})")
        
        # Verifica se a última execução foi bem-sucedida
        if last_run.get("status") != "success":
            logger.error(f"❌ Última execução falhou: {last_run.get('error', 'Erro desconhecido')}")
            return 1
        
        # Verifica se a última execução foi nas últimas 24 horas
        if time_since_last_run > timedelta(hours=24):
            logger.error("❌ A última execução foi há mais de 24 horas")
            return 1
            
        # Verifica por erros recentes
        error_count = await db.clustering_logs.count_documents({
            "type": "error",
            "timestamp": {"$gt": datetime.utcnow() - timedelta(hours=24)}
        })
        
        if error_count > 0:
            logger.warning(f"⚠️ Encontrados {error_count} erros nas últimas 24 horas")
            
            # Obtém os últimos erros
            errors = await db.clustering_logs.find(
                {"type": "error"},
                sort=[("timestamp", -1)],
                limit=3
            ).to_list(3)
            
            for error in errors:
                logger.error(f"Erro em {error['timestamp']}: {error.get('error', 'Erro desconhecido')}")
        
        logger.info("✅ Serviço de clusterização está saudável")
        return 0
        
    except Exception as e:
        logger.error(f"❌ Erro ao verificar a saúde do serviço: {str(e)}")
        return 1
    finally:
        await mongodb_manager.close()

if __name__ == "__main__":
    exit_code = asyncio.run(check_clustering_health())
    sys.exit(exit_code)
