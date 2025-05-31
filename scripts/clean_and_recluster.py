#!/usr/bin/env python3
"""
Script para limpar tópicos corrompidos e executar novamente a clusterização.
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
from app.services.ai.topic_cluster import TopicCluster
import logging

# Configurar logging
configure_logging()
logger = logging.getLogger(__name__)

async def clean_corrupted_topics():
    """Remove tópicos que não têm artigos válidos."""
    try:
        async with mongodb_manager.get_db() as db:
            # Encontrar todos os tópicos
            topics = await db.topics.find({}).to_list(length=None)
            
            print(f"🔍 Verificando {len(topics)} tópicos...")
            
            # Lista para armazenar IDs de tópicos corrompidos
            corrupted_topic_ids = []
            
            for topic in topics:
                topic_id = topic.get('_id')
                article_ids = topic.get('articles', [])
                
                if not article_ids:
                    print(f"  ⚠️  Tópico sem artigos: {topic.get('title', 'Sem título')} (ID: {topic_id})")
                    corrupted_topic_ids.append(topic_id)
                    continue
                
                # Verificar se os artigos existem
                valid_articles = 0
                for article_id in article_ids:
                    article = await db.news.find_one({"_id": article_id})
                    if not article and isinstance(article_id, str):
                        try:
                            article = await db.news.find_one({"_id": ObjectId(article_id)})
                        except:
                            pass
                    
                    if article:
                        valid_articles += 1
                
                if valid_articles == 0 and article_ids:
                    print(f"  ⚠️  Tópico com {len(article_ids)} artigos inválidos: {topic.get('title', 'Sem título')} (ID: {topic_id})")
                    corrupted_topic_ids.append(topic_id)
            
            # Remover tópicos corrompidos
            if corrupted_topic_ids:
                print(f"\n🗑️  Removendo {len(corrupted_topic_ids)} tópicos corrompidos...")
                result = await db.topics.delete_many({"_id": {"$in": corrupted_topic_ids}})
                print(f"✅ {result.deleted_count} tópicos removidos com sucesso!")
                return True
            else:
                print("✅ Nenhum tópico corrompido encontrado.")
                return False
    
    except Exception as e:
        logger.error(f"Erro ao limpar tópicos corrompidos: {str(e)}", exc_info=True)
        return False

async def reset_articles_for_reclustering(days=7):
    """Marca artigos para serem reprocessados na clusterização."""
    try:
        from datetime import datetime, timedelta
        
        print(f"\n🔄 Marcando artigos dos últimos {days} dias para reprocessamento...")
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        async with mongodb_manager.get_db() as db:
            # Atualizar artigos recentes para serem processados novamente
            result = await db.news.update_many(
                {
                    "processed_at": {"$exists": True},
                    "publish_date": {"$gte": cutoff_date.isoformat()}
                },
                {"$unset": {"in_topic": "", "topic_id": ""}, "$set": {"processed_at": None}}
            )
            
            print(f"✅ {result.modified_count} artigos marcados para reprocessamento.")
            return result.modified_count > 0
    
    except Exception as e:
        logger.error(f"Erro ao marcar artigos para reprocessamento: {str(e)}", exc_info=True)
        return False

async def run_clustering():
    """Executa o processo de clusterização."""
    try:
        print("\n🔍 Iniciando clusterização de artigos...")
        
        cluster = TopicCluster()
        await cluster.cluster_recent_news()
        
        print("✅ Clusterização concluída com sucesso!")
        return True
    except Exception as e:
        logger.error(f"Erro durante a clusterização: {str(e)}", exc_info=True)
        return False

async def main():
    """Função principal."""
    print("🛠️  INÍCIO DA LIMPEZA E RECLUSTERIZAÇÃO")
    print("=" * 50)
    
    try:
        # Passo 1: Limpar tópicos corrompidos
        print("\n1️⃣  VERIFICANDO TÓPICOS CORROMPIDOS")
        print("-" * 50)
        await clean_corrupted_topics()
        
        # Passo 2: Marcar artigos para reprocessamento
        print("\n2️⃣  MARCADO ARTIGOS PARA REPROCESSAMENTO")
        print("-" * 50)
        days = 7  # Número de dias para incluir na reclusterização
        await reset_articles_for_reclustering(days=days)
        
        # Passo 3: Executar clusterização
        print("\n3️⃣  EXECUTANDO CLUSTERIZAÇÃO")
        print("-" * 50)
        await run_clustering()
        
        print("\n✅ PROCESSO CONCLUÍDO COM SUCESSO!")
        
    except Exception as e:
        logger.error(f"Erro durante o processo: {str(e)}", exc_info=True)
        print("\n❌ OCORREU UM ERRO DURANTE O PROCESSO. VERIFIQUE OS LOGS PARA MAIS DETALHES.")

if __name__ == "__main__":
    asyncio.run(main())
