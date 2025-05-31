#!/usr/bin/env python3
"""
Script para verificar a associação entre tópicos e artigos no banco de dados.
"""
import asyncio
from pprint import pprint
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

async def check_topic_articles():
    """Verifica a associação entre tópicos e artigos no banco de dados."""
    try:
        async with mongodb_manager.get_db() as db:
            # Contar totais
            total_topics = await db.topics.count_documents({})
            total_news = await db.news.count_documents({})
            
            print(f"\n📊 ESTATÍSTICAS DO BANCO DE DADOS")
            print("=" * 50)
            print(f"Total de tópicos: {total_topics}")
            print(f"Total de notícias: {total_news}")
            
            # Verificar tópicos sem artigos
            topics_without_articles = await db.topics.count_documents({"articles": {"$size": 0}})
            print(f"\n📌 Tópicos sem artigos: {topics_without_articles} de {total_topics}")
            
            # Verificar notícias sem tópicos
            news_without_topics = await db.news.count_documents({"in_topic": False})
            print(f"📰 Notícias sem tópico: {news_without_topics} de {total_news}")
            
            # Mostrar exemplos de tópicos
            print("\n📋 EXEMPLOS DE TÓPICOS:")
            print("=" * 50)
            
            # Buscar alguns tópicos com seus artigos
            topics = await db.topics.aggregate([
                {"$match": {"articles.0": {"$exists": True}}},  # Apenas tópicos com artigos
                {"$limit": 3},
                {"$lookup": {
                    "from": "news",
                    "localField": "articles",
                    "foreignField": "_id",
                    "as": "articles_data"
                }}
            ]).to_list(length=3)
            
            if not topics:
                print("Nenhum tópico com artigos encontrado.")
                # Verificar se existem tópicos sem artigos
                topics = await db.topics.find({"articles.0": {"$exists": False}}).limit(3).to_list(length=3)
                if topics:
                    print("\n📌 Tópicos encontrados (sem artigos):")
                    for topic in topics:
                        print(f"\n📌 Título: {topic.get('title', 'Sem título')}")
                        print(f"   ID: {topic.get('_id')}")
                        print(f"   Artigos: {len(topic.get('articles', []))}")
                return
            
            for topic in topics:
                print(f"\n📌 Título: {topic.get('title', 'Sem título')}")
                print(f"   ID: {topic.get('_id')}")
                print(f"   Total de artigos: {len(topic.get('articles', []))}")
                
                # Mostrar alguns artigos deste tópico
                articles = topic.get('articles_data', [])
                if articles:
                    print("   📰 Artigos:")
                    for i, article in enumerate(articles[:3], 1):  # Limitar a 3 artigos por tópico
                        print(f"     {i}. {article.get('extracted_title', article.get('serpapi_title', 'Sem título'))}")
                        print(f"        Fonte: {article.get('source_name', 'Desconhecida')}")
                        print(f"        URL: {article.get('original_url', 'N/A')}")
                else:
                    print("   ℹ️  Nenhum artigo encontrado para este tópico.")
            
            # Verificar algumas notícias sem tópico
            print("\n📰 EXEMPLOS DE NOTÍCIAS SEM TÓPICO:")
            print("=" * 50)
            
            news_without_topic = await db.news.find({
                "in_topic": False,
                "original_url": {"$exists": True, "$ne": None}
            }).limit(3).to_list(length=3)
            
            if not news_without_topic:
                print("Todas as notícias estão associadas a tópicos.")
            else:
                for i, news in enumerate(news_without_topic, 1):
                    print(f"\n{i}. {news.get('extracted_title', news.get('serpapi_title', 'Sem título'))}")
                    print(f"   Fonte: {news.get('source_name', 'Desconhecida')}")
                    print(f"   URL: {news.get('original_url', 'N/A')}")
                    print(f"   Data: {news.get('publish_date', 'N/A')}")
    
    except Exception as e:
        logger.error(f"Erro ao verificar tópicos e artigos: {str(e)}", exc_info=True)

if __name__ == "__main__":
    print("🔍 Verificando associação entre tópicos e artigos...")
    asyncio.run(check_topic_articles())
