#!/usr/bin/env python3
"""
Script para testar o pipeline completo de coleta e agrupamento de notícias.
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Adiciona o diretório raiz ao PATH para garantir que os imports funcionem
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.services.news.collector import news_collector
from app.services.ai.topic_cluster import topic_cluster
from app.core.database import mongodb_manager
from app.core.config import settings
from app.core.logging import configure_logging
import logging

# Configurar logging
configure_logging()
logger = logging.getLogger(__name__)

async def test_news_collection(query: str = 'autismo', country: str = 'BR') -> int:
    """Testa o processo de coleta de notícias.
    
    Args:
        query: Termo de busca para notícias.
        country: Código do país para a busca.
        
    Returns:
        Número de artigos coletados.
    """
    logger.info(f"🚀 Iniciando teste de coleta de notícias para '{query}' no país '{country}'...")
    
    try:
        # Executar a coleta de notícias
        await news_collector.process_news_batch(query, country)
        
        # Verificar quantos artigos foram salvos
        async with mongodb_manager.get_db() as db:
            count = await db.news.count_documents({})
            logger.info(f"✅ Coleta concluída. Total de artigos no banco: {count}")
            
            # Verificar artigos recentes
            recent_articles = await db.news.find().sort("collection_date", -1).limit(5).to_list(length=5)
            logger.info("\n📰 Últimos artigos coletados:")
            for i, article in enumerate(recent_articles, 1):
                logger.info(f"  {i}. {article.get('extracted_title', 'Sem título')}")
                logger.info(f"     📅 {article.get('publish_date', 'Sem data')} | 📰 {article.get('source_name', 'Fonte desconhecida')}")
                logger.info(f"     🔗 {article.get('original_url', 'Sem URL')}")
        
        return count
        
    except Exception as e:
        logger.error(f"❌ Erro durante a coleta de notícias: {str(e)}", exc_info=True)
        return 0

async def test_topic_clustering(country: str = 'BR') -> int:
    """Testa o processo de agrupamento de notícias em tópicos.
    
    Args:
        country: Código do país para filtrar as notícias.
        
    Returns:
        Número de tópicos criados/atualizados.
    """
    logger.info("\n🚀 Iniciando teste de agrupamento de tópicos...")
    
    try:
        # Executar o agrupamento de tópicos
        await topic_cluster.cluster_recent_news(country)
        
        # Verificar quantos tópicos existem
        async with mongodb_manager.get_db() as db:
            topic_count = await db.topics.count_documents({})
            logger.info(f"✅ Agrupamento concluído. Total de tópicos: {topic_count}")
            
            # Verificar tópicos recentes
            recent_topics = await db.topics.find().sort("created_at", -1).limit(3).to_list(length=3)
            logger.info("\n📚 Últimos tópicos criados:")
            
            for i, topic in enumerate(recent_topics, 1):
                logger.info(f"  {i}. {topic.get('title', 'Sem título')}")
                logger.info(f"     📝 {topic.get('summary', 'Sem resumo')[:100]}...")
                logger.info(f"     📰 Artigos: {topic.get('article_count', 0)} | 🏷️  Fontes: {', '.join(topic.get('sources', []))}")
                logger.info(f"     🆔 {topic.get('_id')}")
            
            # Verificar artigos em tópicos
            if topic_count > 0:
                logger.info("\n🔍 Verificando artigos em tópicos...")
                topics_with_articles = await db.topics.aggregate([
                    {"$match": {"article_count": {"$gt": 0}}},
                    {"$project": {"title": 1, "article_count": 1, "sources": 1, "created_at": 1}},
                    {"$sort": {"created_at": -1}},
                    {"$limit": 3}
                ]).to_list(length=3)
                
                for topic in topics_with_articles:
                    logger.info(f"  📌 {topic.get('title')} - {topic.get('article_count')} artigos")
                    logger.info(f"     🏷️  Fontes: {', '.join(topic.get('sources', []))}")
                    
                    # Verificar alguns artigos deste tópico
                    articles = await db.news.find(
                        {"topic_id": topic.get('_id')}, 
                        {"extracted_title": 1, "source_name": 1, "publish_date": 1, "_id": 0}
                    ).limit(2).to_list(length=2)
                    
                    for j, article in enumerate(articles, 1):
                        logger.info(f"     {j}. {article.get('extracted_title', 'Sem título')}")
                        logger.info(f"        📅 {article.get('publish_date', 'Sem data')} | 📰 {article.get('source_name', 'Fonte desconhecida')}")
        
        return topic_count
        
    except Exception as e:
        logger.error(f"❌ Erro durante o agrupamento de tópicos: {str(e)}", exc_info=True)
        return 0

async def main():
    """Função principal para testar o pipeline de notícias."""
    try:
        logger.info("=" * 80)
        logger.info("🔍 INÍCIO DO TESTE DE PIPELINE DE NOTÍCIAS")
        logger.info("=" * 80)
        
        # Testar coleta de notícias
        query = 'autismo'
        country = 'BR'
        
        # Executar coleta
        article_count = await test_news_collection(query, country)
        
        if article_count == 0:
            logger.error("❌ Nenhum artigo foi coletado. Verifique os logs para mais detalhes.")
            return
        
        # Executar agrupamento de tópicos
        topic_count = await test_topic_clustering(country)
        
        logger.info("\n" + "=" * 80)
        logger.info("✅ TESTE DE PIPELINE CONCLUÍDO")
        logger.info(f"   Artigos coletados: {article_count}")
        logger.info(f"   Tópicos criados/atualizados: {topic_count}")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"❌ Erro durante a execução do teste: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
