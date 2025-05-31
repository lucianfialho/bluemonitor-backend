#!/usr/bin/env python3
"""
Script para verificar os IDs dos artigos nos tópicos.
"""
import asyncio
from pprint import pprint
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

async def check_article_ids():
    """Verifica os IDs dos artigos nos tópicos."""
    try:
        async with mongodb_manager.get_db() as db:
            # Buscar todos os tópicos
            topics = await db.topics.find({}).to_list(length=10)  # Limitar a 10 para teste
            
            print(f"🔍 Verificando {len(topics)} tópicos...\n")
            
            for topic in topics:
                topic_id = topic.get('_id')
                article_ids = topic.get('articles', [])
                
                print(f"\n📌 TÓPICO: {topic.get('title', 'Sem título')}")
                print(f"   ID: {topic_id}")
                print(f"   Total de artigos: {len(article_ids)}")
                
                if not article_ids:
                    print("   ℹ️  Nenhum artigo neste tópico.")
                    continue
                
                # Verificar os primeiros 3 artigos
                for i, article_id in enumerate(article_ids[:3], 1):
                    print(f"\n   🔍 Verificando artigo {i}...")
                    print(f"      ID do artigo: {article_id}")
                    print(f"      Tipo do ID: {type(article_id).__name__}")
                    
                    # Tentar encontrar o artigo
                    try:
                        # Primeiro, tentar com o ID como está
                        article = await db.news.find_one({"_id": article_id})
                        
                        if article:
                            print(f"      ✅ Artigo encontrado!")
                            print(f"         Título: {article.get('extracted_title', article.get('serpapi_title', 'Sem título'))}")
                            print(f"         Fonte: {article.get('source_name', 'Desconhecida')}")
                            print(f"         URL: {article.get('original_url', 'N/A')}")
                        else:
                            # Tentar converter para ObjectId se for string
                            if isinstance(article_id, str):
                                try:
                                    obj_id = ObjectId(article_id)
                                    article = await db.news.find_one({"_id": obj_id})
                                    if article:
                                        print(f"      ✅ Artigo encontrado (após conversão para ObjectId)!")
                                        print(f"         Título: {article.get('extracted_title', article.get('serpapi_title', 'Sem título'))}")
                                        print(f"         Fonte: {article.get('source_name', 'Desconhecida')}")
                                        print(f"         URL: {article.get('original_url', 'N/A')}")
                                    else:
                                        print("      ❌ Artigo não encontrado, mesmo após conversão para ObjectId.")
                                except Exception as e:
                                    print(f"      ❌ Erro ao converter ID para ObjectId: {str(e)}")
                            else:
                                print("      ❌ Artigo não encontrado.")
                    
                    except Exception as e:
                        print(f"      ❌ Erro ao buscar artigo: {str(e)}")
                
                # Verificar se há mais artigos não mostrados
                if len(article_ids) > 3:
                    print(f"   ℹ️  +{len(article_ids) - 3} artigos não mostrados neste tópico.")
    
    except Exception as e:
        logger.error(f"Erro ao verificar IDs de artigos: {str(e)}", exc_info=True)

if __name__ == "__main__":
    print("🔍 Verificando IDs de artigos nos tópicos...")
    asyncio.run(check_article_ids())
