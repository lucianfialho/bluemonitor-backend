#!/usr/bin/env python3
"""
Script para corrigir a associação entre tópicos e artigos no banco de dados.
"""
import asyncio
from pprint import pprint
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
from app.services.ai.topic_cluster import TopicCluster
import logging

# Configurar logging
configure_logging()
logger = logging.getLogger(__name__)

class TopicFixer:
    def __init__(self):
        self.topic_cluster = TopicCluster()
    
    async def check_topic_integrity(self, topic):
        """Verifica a integridade de um tópico, contando quantos artigos são válidos."""
        async with mongodb_manager.get_db() as db:
            article_ids = topic.get('articles', [])
            if not article_ids:
                return 0, 0  # Tópico vazio
            
            # Contar quantos artigos existem
            valid_count = 0
            for article_id in article_ids:
                try:
                    # Tentar encontrar o artigo com o ID como está
                    article = await db.news.find_one({"_id": article_id})
                    if not article and isinstance(article_id, str):
                        # Tentar converter para ObjectId se for string
                        try:
                            obj_id = ObjectId(article_id)
                            article = await db.news.find_one({"_id": obj_id})
                        except:
                            pass
                    
                    if article:
                        valid_count += 1
                except Exception as e:
                    logger.warning(f"Erro ao verificar artigo {article_id}: {str(e)}")
            
            return len(article_ids), valid_count
    
    async def find_and_remove_broken_topics(self):
        """Encontra e remove tópicos que não têm artigos válidos."""
        async with mongodb_manager.get_db() as db:
            topics = await db.topics.find({}).to_list(length=None)
            broken_topics = []
            
            print(f"\n🔍 Verificando {len(topics)} tópicos...")
            
            for topic in topics:
                total_articles, valid_articles = await self.check_topic_integrity(topic)
                if valid_articles == 0 and total_articles > 0:
                    broken_topics.append({
                        'topic_id': topic['_id'],
                        'title': topic.get('title', 'Sem título'),
                        'total_articles': total_articles
                    })
            
            print(f"\n⚠️  Encontrados {len(broken_topics)} tópicos corrompidos (com {sum(t['total_articles'] for t in broken_topics)} artigos inválidos no total).")
            
            if broken_topics:
                print("\n📋 Tópicos corrompidos:")
                for i, topic in enumerate(broken_topics, 1):
                    print(f"   {i}. {topic['title']} (ID: {topic['topic_id']}) - {topic['total_articles']} artigos inválidos")
                
                # Perguntar ao usuário se deseja remover
                confirm = input("\n❓ Deseja remover estes tópicos corrompidos? (s/n): ").strip().lower()
                
                if confirm == 's':
                    # Remover tópicos corrompidos
                    for topic in broken_topics:
                        await db.topics.delete_one({"_id": topic['topic_id']})
                    print(f"✅ {len(broken_topics)} tópicos corrompidos removidos com sucesso!")
                    return True
                else:
                    print("❌ Operação cancelada pelo usuário.")
                    return False
            else:
                print("✅ Nenhum tópico corrompido encontrado.")
                return True
    
    async def recluster_articles(self, days=7):
        """Reagrupa artigos dos últimos N dias em tópicos."""
        try:
            print(f"\n🔄 Iniciando reagrupamento de artigos dos últimos {days} dias...")
            
            # Calcular data de corte
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Marcar todos os artigos recentes como não processados
            async with mongodb_manager.get_db() as db:
                result = await db.news.update_many(
                    {
                        "processed_at": {"$exists": True},
                        "publish_date": {"$gte": cutoff_date.isoformat()}
                    },
                    {"$unset": {"in_topic": "", "topic_id": ""}, "$set": {"processed_at": None}}
                )
                
                print(f"✅ {result.modified_count} artigos marcados para reprocessamento.")
            
            # Executar clusterização
            print("\n🔍 Iniciando clusterização de artigos...")
            await self.topic_cluster.cluster_recent_news()
            
            print("\n✅ Clusterização concluída com sucesso!")
            return True
            
        except Exception as e:
            logger.error(f"Erro durante o reagrupamento: {str(e)}", exc_info=True)
            return False

async def main():
    """Função principal."""
    print("🛠️  INÍCIO DA CORREÇÃO DE TÓPICOS")
    print("=" * 50)
    
    fixer = TopicFixer()
    
    try:
        # Passo 1: Encontrar e remover tópicos corrompidos
        success = await fixer.find_and_remove_broken_topics()
        
        if not success:
            print("\n❌ Operação interrompida.")
            return
        
        # Passo 2: Perguntar se deseja reagrupar artigos
        confirm = input("\n❓ Deseja reagrupar os artigos em tópicos? (s/n): ").strip().lower()
        
        if confirm == 's':
            days = input("   Quantos dias de artigos deseja incluir? (padrão: 7): ").strip()
            days = int(days) if days.isdigit() else 7
            
            await fixer.recluster_articles(days=days)
        
        print("\n✅ Processo de correção concluído com sucesso!")
        
    except Exception as e:
        logger.error(f"Erro durante a correção: {str(e)}", exc_info=True)
        print("\n❌ Ocorreu um erro durante a correção. Verifique os logs para mais detalhes.")

if __name__ == "__main__":
    asyncio.run(main())
