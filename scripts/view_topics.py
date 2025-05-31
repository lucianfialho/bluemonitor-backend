#!/usr/bin/env python3
"""
Script para visualizar tópicos e suas notícias com resumos.
"""
import asyncio
from datetime import datetime
from typing import List, Dict, Any
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

async def get_topics_with_articles() -> List[Dict[str, Any]]:
    """Obtém todos os tópicos com seus artigos."""
    try:
        async with mongodb_manager.get_db() as db:
            # Buscar tópicos ordenados por data de criação (mais recentes primeiro)
            topics = await db.topics.aggregate([
                {"$sort": {"created_at": -1}},
                {
                    "$lookup": {
                        "from": "news",
                        "localField": "articles",
                        "foreignField": "_id",
                        "as": "articles_data"
                    }
                },
                {
                    "$addFields": {
                        "article_count": {"$size": "$articles_data"},
                        "sources": {
                            "$reduce": {
                                "input": "$articles_data.source_name",
                                "initialValue": [],
                                "in": {
                                    "$cond": [
                                        {"$in": ["$$this", "$$value"]},
                                        "$$value",
                                        {"$concatArrays": ["$$value", ["$$this"]]}
                                    ]
                                }
                            }
                        },
                        # Garantir que articles_data seja uma lista vazia se for None
                        "articles_data": {
                            "$ifNull": ["$articles_data", []]
                        }
                    }
                }
            ]).to_list(length=50)  # Limitar a 50 tópicos
            
            return topics
            
    except Exception as e:
        logger.error(f"Erro ao buscar tópicos: {str(e)}", exc_info=True)
        return []

async def display_topic(topic: Dict[str, Any], index: int) -> None:
    """Exibe um tópico e seus artigos de forma formatada."""
    try:
        # Formatar data
        created_at = topic.get('created_at', datetime.utcnow())
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        date_str = created_at.strftime('%d/%m/%Y %H:%M')
        
        # Exibir cabeçalho do tópico
        print("\n" + "=" * 100)
        print(f"📌 TÓPICO {index + 1}: {topic.get('title', 'Sem título')}")
        print("=" * 100)
        print(f"🆔 ID: {topic.get('_id')}")
        print(f"📅 Criado em: {date_str}")
        print(f"📰 Número de artigos: {topic.get('article_count', 0)}")
        print(f"🏷️  Fontes: {', '.join(source for source in topic.get('sources', []) if source) or 'Nenhuma'}")
        
        # Exibir resumo do tópico
        summary = topic.get('summary', 'Sem resumo disponível.')
        print("\n📝 RESUMO:")
        print("-" * 50)
        print(summary)
        print("-" * 50)
        
        # Exibir artigos do tópico
        articles = topic.get('articles_data', [])
        if not articles:
            print("\nℹ️  Nenhum artigo encontrado neste tópico.")
            return
            
        print(f"\n📰 ARTIGOS ({len(articles)}):")
        for i, article in enumerate(articles, 1):
            print(f"\n  {i}. {article.get('extracted_title', article.get('serpapi_title', 'Sem título'))}")
            
            # Exibir fonte e data
            source = article.get('source_name', 'Fonte desconhecida')
            date = article.get('publish_date', 'Data desconhecida')
            print(f"     📅 {date} | 📰 {source}")
            
            # Exibir URL
            url = article.get('original_url', 'Sem URL')
            print(f"     🔗 {url}")
            
            # Exibir resumo do artigo, se disponível
            article_summary = article.get('summary') or article.get('serpapi_snippet')
            if article_summary:
                print(f"     📝 {article_summary[:200]}...")
    
    except Exception as e:
        logger.error(f"Erro ao exibir tópico: {str(e)}", exc_info=True)

async def main():
    """Função principal para exibir tópicos e notícias."""
    try:
        print("\n" + "=" * 100)
        print("📰 ANÁLISE DE TÓPICOS E NOTÍCIAS")
        print("=" * 100)
        
        # Obter tópicos com artigos
        topics = await get_topics_with_articles()
        
        if not topics:
            print("\nℹ️  Nenhum tópico encontrado no banco de dados.")
            return
            
        print(f"\n🔍 Encontrados {len(topics)} tópicos:\n")
        
        # Exibir cada tópico
        for i, topic in enumerate(topics):
            await display_topic(topic, i)
            print("\n" + "-" * 100 + "\n")
        
        print("\n" + "=" * 100)
        print("✅ ANÁLISE CONCLUÍDA")
        print("=" * 100)
        
    except Exception as e:
        logger.error(f"Erro durante a execução: {str(e)}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())
