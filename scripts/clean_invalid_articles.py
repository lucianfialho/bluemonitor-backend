#!/usr/bin/env python3
"""
Script para limpar artigos inválidos do banco de dados.
Remove artigos sem URL ou com URL None.
"""
import asyncio
import sys
from pathlib import Path
from typing import List, Dict, Any

# Adiciona o diretório raiz ao PATH para garantir que os imports funcionem
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.core.database import mongodb_manager
from app.core.config import settings
from app.core.logging import configure_logging
import logging

# Configurar logging
configure_logging()
logger = logging.getLogger(__name__)

async def clean_invalid_articles() -> Dict[str, int]:
    """Remove artigos inválidos do banco de dados.
    
    Returns:
        Dict com estatísticas da operação.
    """
    stats = {
        'total_articles': 0,
        'invalid_articles': 0,
        'articles_without_url': 0,
        'articles_with_none_url': 0,
        'deleted_count': 0
    }
    
    try:
        async with mongodb_manager.get_db() as db:
            # Contar total de artigos
            stats['total_articles'] = await db.news.count_documents({})
            
            # Encontrar artigos sem URL ou com URL None
            query = {
                "$or": [
                    {"url": {"$exists": False}},
                    {"url": None},
                    {"url": ""}
                ]
            }
            
            # Contar artigos inválidos
            stats['invalid_articles'] = await db.news.count_documents(query)
            stats['articles_without_url'] = await db.news.count_documents({"url": {"$exists": False}})
            stats['articles_with_none_url'] = await db.news.count_documents({"url": None})
            stats['articles_with_empty_url'] = await db.news.count_documents({"url": ""})
            
            # Remover artigos inválidos
            if stats['invalid_articles'] > 0:
                result = await db.news.delete_many(query)
                stats['deleted_count'] = result.deleted_count
                logger.info(f"Removidos {result.deleted_count} artigos inválidos do banco de dados.")
            else:
                logger.info("Nenhum artigo inválido encontrado para remoção.")
                
            return stats
            
    except Exception as e:
        logger.error(f"Erro ao limpar artigos inválidos: {str(e)}", exc_info=True)
        raise

async def main():
    """Função principal para execução do script."""
    try:
        logger.info("🚀 Iniciando limpeza de artigos inválidos...")
        stats = await clean_invalid_articles()
        
        # Exibir relatório
        logger.info("\n📊 RELATÓRIO DE LIMPEZA")
        logger.info("=" * 80)
        logger.info(f"Total de artigos no banco: {stats['total_articles']}")
        logger.info(f"Artigos inválidos encontrados: {stats['invalid_articles']}")
        logger.info(f"  - Sem campo 'url': {stats['articles_without_url']}")
        logger.info(f"  - Com URL None: {stats['articles_with_none_url']}")
        logger.info(f"  - Com URL vazio: {stats['articles_with_empty_url']}")
        logger.info(f"\n✅ Artigos removidos: {stats['deleted_count']}")
        
        if stats['deleted_count'] > 0:
            logger.warning("\n⚠️  Recomendação: Execute o processo de coleta de notícias novamente para preencher o banco com dados válidos.")
        
        logger.info("\n✅ Limpeza concluída com sucesso!")
        
    except Exception as e:
        logger.error(f"❌ Erro durante a execução do script: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
