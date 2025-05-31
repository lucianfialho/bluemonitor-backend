#!/usr/bin/env python3
"""
Script para corrigir inconsistências no banco de dados.
"""
import asyncio
from pathlib import Path
import sys
from bson import ObjectId
from datetime import datetime, timedelta

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

async def fix_inconsistencies():
    """Corrige inconsistências no banco de dados."""
    try:
        async with mongodb_manager.get_db() as db:
            # 1. Corrigir tópicos com artigos inválidos
            topics = await db.topics.find({}).to_list(length=None)
            
            for topic in topics:
                topic_id = topic['_id']
                article_ids = topic.get('articles', [])
                valid_article_ids = []
                
                # Verificar cada artigo no tópico
                for article_id in article_ids:
                    try:
                        # Verificar se o artigo existe
                        article = await db.news.find_one({"_id": ObjectId(article_id)})
                        if article:
                            valid_article_ids.append(article_id)
                            
                            # Atualizar o artigo para marcar que está em um tópico
                            await db.news.update_one(
                                {"_id": ObjectId(article_id)},
                                {"$set": {"in_topic": True, "topic_id": topic_id}}
                            )
                        else:
                            logger.warning(f"Artigo não encontrado: {article_id} no tópico {topic_id}")
                    except Exception as e:
                        logger.error(f"Erro ao processar artigo {article_id}: {str(e)}")
                
                # Atualizar o tópico com apenas os IDs válidos
                if len(valid_article_ids) != len(article_ids):
                    logger.info(f"Atualizando tópico {topic_id}: {len(valid_article_ids)}/{len(article_ids)} artigos válidos")
                    await db.topics.update_one(
                        {"_id": topic_id},
                        {
                            "$set": {
                                "articles": valid_article_ids,
                                "article_count": len(valid_article_ids),
                                "updated_at": datetime.utcnow()
                            }
                        }
                    )
            
            # 2. Corrigir notícias marcadas incorretamente
            # Todas as notícias que estão em tópicos devem ter in_topic=True
            topics = await db.topics.find({}).to_list(length=None)
            for topic in topics:
                article_ids = [ObjectId(id_) for id_ in topic.get('articles', [])]
                if article_ids:
                    await db.news.update_many(
                        {"_id": {"$in": article_ids}},
                        {"$set": {"in_topic": True, "topic_id": topic['_id']}}
                    )
            
            # 3. Garantir que todas as notícias tenham in_topic definido
            await db.news.update_many(
                {"in_topic": {"$exists": False}},
                {"$set": {"in_topic": False}}
            )
            
            logger.info("✅ Inconsistências corrigidas com sucesso!")
    
    except Exception as e:
        logger.error(f"Erro ao corrigir inconsistências: {str(e)}", exc_info=True)
        raise
    finally:
        if 'db' in locals():
            await db.client.close()

if __name__ == "__main__":
    print("🔧 CORRIGINDO INCONSISTÊNCIAS NO BANCO DE DADOS")
    print("=" * 50)
    asyncio.run(fix_inconsistencies())
