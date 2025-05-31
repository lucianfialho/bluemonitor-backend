#!/usr/bin/env python3
"""
Script para verificar o tópico existente.
"""
import asyncio
from pathlib import Path
import sys

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

async def check_topic():
    """Verifica o tópico existente."""
    try:
        async with mongodb_manager.get_db() as db:
            # Buscar o tópico
            topic = await db.topics.find_one({})
            
            if not topic:
                print("ℹ️  Nenhum tópico encontrado no banco de dados.")
                return
            
            print(f"📌 Tópico: {topic.get('title', 'Sem título')}")
            print(f"🆔 ID: {topic.get('_id')}")
            print(f"📅 Criado em: {topic.get('created_at')}")
            print(f"📰 Total de artigos: {len(topic.get('articles', []))}")
            
            # Verificar se há artigos
            article_ids = topic.get('articles', [])
            if not article_ids:
                print("ℹ️  Nenhum artigo neste tópico.")
                return
            
            # Mostrar os primeiros 5 artigos
            print("\n📰 PRIMEIROS 5 ARTIGOS:")
            print("=" * 50)
            
            for i, article_id in enumerate(article_ids[:5], 1):
                article = await db.news.find_one({"_id": article_id})
                if not article:
                    print(f"{i}. ❌ Artigo não encontrado (ID: {article_id})")
                    continue
                
                title = article.get('extracted_title', article.get('serpapi_title', 'Sem título'))
                source = article.get('source_name', 'Fonte desconhecida')
                url = article.get('original_url', 'N/A')
                
                print(f"{i}. {title}")
                print(f"   📰 Fonte: {source}")
                print(f"   🔗 URL: {url}\n")
            
            # Verificar notícias sem tópico
            news_without_topic = await db.news.count_documents({"in_topic": {"$ne": True}})
            print(f"\n📰 NOTÍCIAS SEM TÓPICO: {news_without_topic}")
            
            if news_without_topic > 0:
                print("\n📝 Executando clusterização para incluir notícias restantes...")
                from app.services.ai.topic_cluster import TopicCluster
                cluster = TopicCluster()
                await cluster.cluster_recent_news()
                print("✅ Clusterização concluída!")
    
    except Exception as e:
        logger.error(f"Erro ao verificar tópico: {str(e)}", exc_info=True)
        print(f"❌ Ocorreu um erro: {str(e)}")
    finally:
        await mongodb_manager.close()

if __name__ == "__main__":
    print("🔍 Verificando tópico existente...")
    asyncio.run(check_topic())
