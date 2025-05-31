#!/usr/bin/env python3
"""
Script para verificar o estado final dos tópicos e artigos.
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

async def check_final_state():
    """Verifica o estado final dos tópicos e artigos."""
    try:
        async with mongodb_manager.get_db() as db:
            # Contar totais
            total_topics = await db.topics.count_documents({})
            total_news = await db.news.count_documents({})
            
            print("📊 ESTADO FINAL DO BANCO DE DADOS")
            print("=" * 50)
            print(f"Total de tópicos: {total_topics}")
            print(f"Total de notícias: {total_news}")
            
            # Mostrar tópicos
            topics = await db.topics.find({}).to_list(length=10)
            
            if not topics:
                print("\nℹ️  Nenhum tópico encontrado no banco de dados.")
                return
            
            print("\n📋 TÓPICOS EXISTENTES:")
            print("=" * 50)
            
            for topic in topics:
                print(f"\n📌 Tópico: {topic.get('title', 'Sem título')}")
                print(f"   ID: {topic.get('_id')}")
                print(f"   Data de criação: {topic.get('created_at')}")
                print(f"   Número de artigos: {len(topic.get('articles', []))}")
                
                # Mostrar alguns artigos deste tópico
                article_ids = topic.get('articles', [])[:3]  # Limitar a 3 artigos por tópico
                
                if article_ids:
                    print("   📰 Artigos:")
                    for i, article_id in enumerate(article_ids, 1):
                        article = await db.news.find_one({"_id": article_id})
                        if not article and isinstance(article_id, str):
                            try:
                                article = await db.news.find_one({"_id": ObjectId(article_id)})
                            except:
                                pass
                        
                        if article:
                            title = article.get('extracted_title', article.get('serpapi_title', 'Sem título'))
                            source = article.get('source_name', 'Fonte desconhecida')
                            url = article.get('original_url', 'N/A')
                            print(f"     {i}. {title}")
                            print(f"        📰 Fonte: {source}")
                            print(f"        🔗 URL: {url}")
                        else:
                            print(f"     {i}. ❌ Artigo não encontrado (ID: {article_id})")
                    
                    # Mostrar contagem se houver mais artigos
                    if len(topic.get('articles', [])) > 3:
                        print(f"     ... e mais {len(topic.get('articles', [])) - 3} artigos.")
                else:
                    print("   ℹ️  Nenhum artigo neste tópico.")
            
            # Verificar notícias sem tópico
            news_without_topic = await db.news.count_documents({"in_topic": {"$ne": True}})
            print(f"\n📰 NOTÍCIAS SEM TÓPICO: {news_without_topic}")
            
            # Mostrar algumas notícias sem tópico
            if news_without_topic > 0:
                print("\n📰 EXEMPLOS DE NOTÍCIAS SEM TÓPICO:")
                print("-" * 50)
                
                news = await db.news.find({"in_topic": {"$ne": True}}).limit(3).to_list(length=3)
                
                for i, article in enumerate(news, 1):
                    title = article.get('extracted_title', article.get('serpapi_title', 'Sem título'))
                    source = article.get('source_name', 'Fonte desconhecida')
                    url = article.get('original_url', 'N/A')
                    print(f"{i}. {title}")
                    print(f"   📰 Fonte: {source}")
                    print(f"   🔗 URL: {url}")
                    print()
            
            print("\n✅ Verificação concluída com sucesso!")
    
    except Exception as e:
        logger.error(f"Erro ao verificar o estado final: {str(e)}", exc_info=True)
        print("❌ Ocorreu um erro durante a verificação. Consulte os logs para mais detalhes.")

if __name__ == "__main__":
    print("🔍 Verificando o estado final dos tópicos e artigos...")
    asyncio.run(check_final_state())
