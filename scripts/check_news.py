#!/usr/bin/env python3
"""
Script para verificar notícias e tópicos no banco de dados.
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

async def check_news():
    """Verifica notícias e tópicos no banco de dados."""
    try:
        async with mongodb_manager.get_db() as db:
            # Contar totais
            total_news = await db.news.count_documents({})
            news_without_topic = await db.news.count_documents({"in_topic": {"$ne": True}})
            total_topics = await db.topics.count_documents({})
            
            print(f"📊 ESTATÍSTICAS DO BANCO DE DADOS")
            print("=" * 50)
            print(f"Total de notícias: {total_news}")
            print(f"Notícias sem tópico: {news_without_topic}")
            print(f"Total de tópicos: {total_topics}")
            
            # Verificar notícias sem tópico
            if news_without_topic > 0:
                print("\n📰 NOTÍCIAS SEM TÓPICO:")
                print("-" * 50)
                
                news = await db.news.find({"in_topic": {"$ne": True}}) \
                    .sort("publish_date", -1) \
                    .limit(5) \
                    .to_list(length=5)
                
                for i, article in enumerate(news, 1):
                    title = article.get('extracted_title', article.get('serpapi_title', 'Sem título'))
                    source = article.get('source_name', 'Fonte desconhecida')
                    url = article.get('original_url', 'N/A')
                    date = article.get('publish_date', 'Data desconhecida')
                    
                    print(f"{i}. {title}")
                    print(f"   📰 Fonte: {source}")
                    print(f"   📅 Data: {date}")
                    print(f"   🔗 URL: {url}")
                    print()
            
            # Verificar tópicos
            topics = await db.topics.find({}) \
                .sort("created_at", -1) \
                .to_list(length=10)
            
            if not topics:
                print("\nℹ️  Nenhum tópico encontrado.")
                return
            
            print(f"\n📋 TÓPICOS EXISTENTES (últimos 10):")
            print("=" * 50)
            
            for i, topic in enumerate(topics, 1):
                title = topic.get('title', 'Sem título')
                topic_id = topic.get('_id')
                created_at = topic.get('created_at', 'Data desconhecida')
                article_count = len(topic.get('articles', []))
                sources = ", ".join(topic.get('sources', []))
                
                print(f"{i}. {title}")
                print(f"   🆔 ID: {topic_id}")
                print(f"   📅 Criado em: {created_at}")
                print(f"   📰 Artigos: {article_count}")
                print(f"   📡 Fontes: {sources}")
                
                # Mostrar alguns artigos deste tópico
                article_ids = topic.get('articles', [])[:3]  # Limitar a 3 artigos
                if article_ids:
                    print("   📰 Artigos:")
                    for j, article_id in enumerate(article_ids, 1):
                        article = await db.news.find_one({"_id": ObjectId(article_id)})
                        if article:
                            title = article.get('extracted_title', article.get('serpapi_title', 'Sem título'))
                            source = article.get('source_name', 'Fonte desconhecida')
                            print(f"      {j}. {title}")
                            print(f"         📰 Fonte: {source}")
                        else:
                            print(f"      {j}. ❌ Artigo não encontrado (ID: {article_id})")
                    
                    if len(topic.get('articles', [])) > 3:
                        print(f"      ... e mais {len(topic.get('articles', [])) - 3} artigos.")
                
                print()  # Linha em branco entre tópicos
    
    except Exception as e:
        logger.error(f"Erro ao verificar notícias: {str(e)}", exc_info=True)
        print(f"❌ Ocorreu um erro: {str(e)}")
    finally:
        # Fechar a conexão com o banco de dados
        if hasattr(db, 'client') and db.client is not None:
            db.client.close()
        logger.info("✅ Verificação concluída!")

if __name__ == "__main__":
    print("🔍 VERIFICANDO NOTÍCIAS E TÓPICOS")
    print("=" * 50)
    asyncio.run(check_news())
