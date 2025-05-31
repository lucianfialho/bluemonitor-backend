#!/usr/bin/env python3
"""
Script para resetar o estado de clusterização das notícias.
"""
import asyncio
from pathlib import Path
import sys
from bson import ObjectId

# Adiciona o diretório raiz ao PATH para garantir que os imports funcionem
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.core.database import mongodb_manager
from app.core.logging import configure_logging
import logging

# Configurar logging
configure_logging()
logger = logging.getLogger(__name__)

async def reset_clustering():
    """Reseta o estado de clusterização das notícias."""
    try:
        async with mongodb_manager.get_db() as db:
            # 1. Remover todos os tópicos existentes
            result = await db.topics.delete_many({})
            logger.info(f"Removidos {result.deleted_count} tópicos")
            
            # 2. Marcar todas as notícias como não processadas
            result = await db.news.update_many(
                {},
                {"$set": {"in_topic": False, "topic_id": None}}
            )
            logger.info(f"Atualizadas {result.modified_count} notícias")
            
            logger.info("✅ Clusterização resetada com sucesso!")
    
    except Exception as e:
        logger.error(f"Erro ao resetar clusterização: {str(e)}", exc_info=True)
        raise
    finally:
        if 'db' in locals():
            await db.client.close()

if __name__ == "__main__":
    print("🔄 RESETANDO CLUSTERIZAÇÃO DE NOTÍCIAS")
    print("=" * 50)
    asyncio.run(reset_clustering())
