#!/usr/bin/env python3
"""
Script para verificar a existência dos artigos no banco de dados.
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

async def verify_articles():
    """Verifica a existência dos artigos no banco de dados."""
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
            
            article_ids = topic.get('articles', [])
            if not article_ids:
                print("ℹ️  Nenhum artigo neste tópico.")
                return
            
            print("\n🔍 Verificando artigos...")
            print("=" * 50)
            
            valid_articles = 0
            invalid_articles = 0
            
            for i, article_id in enumerate(article_ids, 1):
                try:
                    # Tentar encontrar o artigo pelo ID
                    article = await db.news.find_one({"_id": ObjectId(article_id)})
                    
                    if article:
                        valid_articles += 1
                        status = "✅ VÁLIDO"
                    else:
                        invalid_articles += 1
                        status = "❌ NÃO ENCONTRADO"
                    
                    print(f"{i}. {article_id} - {status}")
                    
                except Exception as e:
                    invalid_articles += 1
                    print(f"{i}. {article_id} - ❌ ERRO: {str(e)}")
            
            print("\n📊 RESUMO:")
            print("=" * 50)
            print(f"Total de artigos: {len(article_ids)}")
            print(f"Artigos válidos: {valid_articles}")
            print(f"Artigos inválidos/não encontrados: {invalid_articles}")
            
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
        logger.error(f"Erro ao verificar artigos: {str(e)}", exc_info=True)
        print(f"❌ Ocorreu um erro: {str(e)}")
    finally:
        if 'db' in locals():
            await db.client.close()

if __name__ == "__main__":
    print("🔍 VERIFICAÇÃO DE ARTIGOS")
    print("=" * 50)
    asyncio.run(verify_articles())
