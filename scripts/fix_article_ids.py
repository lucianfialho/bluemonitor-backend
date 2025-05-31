#!/usr/bin/env python3
"""
Script para corrigir os IDs dos artigos nos tópicos.
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

async def fix_article_ids():
    """Corrige os IDs dos artigos nos tópicos."""
    try:
        async with mongodb_manager.get_db() as db:
            # Buscar todos os tópicos
            topics = await db.topics.find({}).to_list(length=None)
            
            if not topics:
                print("ℹ️  Nenhum tópico encontrado no banco de dados.")
                return
            
            print(f"🔍 Encontrados {len(topics)} tópicos para verificação.")
            
            for topic in topics:
                topic_id = topic.get('_id')
                article_ids = topic.get('articles', [])
                
                if not article_ids:
                    print(f"ℹ️  Tópico '{topic.get('title', 'Sem título')}' não possui artigos.")
                    continue
                
                print(f"\n📌 Verificando tópico: {topic.get('title', 'Sem título')}")
                print(f"   ID: {topic_id}")
                print(f"   Artigos originais: {len(article_ids)}")
                
                # Lista para armazenar os IDs válidos
                valid_article_ids = []
                
                # Verificar cada artigo
                for article_id in article_ids:
                    # Verificar se o ID é um ObjectId válido
                    if isinstance(article_id, str) and len(article_id) == 24:
                        try:
                            obj_id = ObjectId(article_id)
                            article = await db.news.find_one({"_id": obj_id})
                            if article:
                                valid_article_ids.append(obj_id)
                                continue
                        except:
                            pass
                    
                    # Se chegou aqui, o ID não é válido ou o artigo não existe
                    print(f"   ❌ Artigo inválido/não encontrado: {article_id}")
                
                # Atualizar o tópico com os IDs válidos
                if len(valid_article_ids) != len(article_ids):
                    print(f"   ✅ Artigos válidos encontrados: {len(valid_article_ids)}/{len(article_ids)}")
                    
                    # Atualizar o tópico
                    await db.topics.update_one(
                        {"_id": topic_id},
                        {"$set": {"articles": valid_article_ids}}
                    )
                    print(f"   🔄 Tópico atualizado com sucesso!")
                else:
                    print("   ✅ Todos os artigos são válidos.")
            
            print("\n✅ Processo de correção concluído!")
    
    except Exception as e:
        logger.error(f"Erro ao corrigir IDs dos artigos: {str(e)}", exc_info=True)
        print(f"❌ Ocorreu um erro: {str(e)}")
    finally:
        if 'db' in locals():
            await db.client.close()

if __name__ == "__main__":
    print("🔧 INICIANDO CORREÇÃO DE IDs DE ARTIGOS")
    print("=" * 50)
    asyncio.run(fix_article_ids())
