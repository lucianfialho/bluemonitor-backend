#!/usr/bin/env python3
"""
Script para verificar tópicos e notícias duplicadas no banco de dados.
"""
import asyncio
import sys
import os
from pathlib import Path
from typing import Dict, List, Set, Any
from collections import defaultdict

# Adiciona o diretório raiz ao PATH para garantir que os imports funcionem
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.core.database import mongodb_manager
from app.core.config import settings
from app.core.logging import configure_logging
import logging

# Configurar logging
configure_logging()
logger = logging.getLogger(__name__)

async def get_all_topics() -> List[Dict]:
    """Busca todos os tópicos no banco de dados."""
    async with mongodb_manager.get_db() as db:
        topics = await db.topics.find({"is_active": True}).to_list(length=None)
        return topics

async def get_articles_for_topic(topic_id: str) -> List[Dict]:
    """Busca todos os artigos de um tópico específico."""
    async with mongodb_manager.get_db() as db:
        topic = await db.topics.find_one({"_id": topic_id})
        if not topic:
            return []
            
        article_ids = topic.get("articles", [])
        if not article_ids:
            return []
            
        articles = await db.news.find({"_id": {"$in": article_ids}}).to_list(length=None)
        return articles

async def find_duplicate_articles() -> Dict[str, List[Dict]]:
    """Encontra artigos duplicados baseados na URL."""
    async with mongodb_manager.get_db() as db:
        # Agrupa artigos por URL
        pipeline = [
            {"$group": {
                "_id": "$url",
                "count": {"$sum": 1},
                "articles": {"$push": "$$ROOT"}
            }},
            {"$match": {"count": {"$gt": 1}}}
        ]
        
        duplicates = await db.news.aggregate(pipeline).to_list(length=None)
        return {d["_id"]: d["articles"] for d in duplicates}

async def check_topics():
    """Verifica tópicos e notícias duplicadas."""
    logger.info("🔍 Verificando tópicos e notícias duplicadas...")
    
    try:
        # Buscar todos os tópicos
        topics = await get_all_topics()
        logger.info(f"📊 Total de tópicos ativos: {len(topics)}")
    except Exception as e:
        logger.error(f"Erro ao buscar tópicos: {str(e)}")
        return
    
    # Estatísticas por tópico
    topic_stats = []
    all_article_ids = set()
    duplicate_article_count = 0
    
    for topic in topics:
        topic_id = topic["_id"]
        articles = await get_articles_for_topic(topic_id)
        
        # Verificar artigos duplicados neste tópico
        url_count = defaultdict(int)
        for article in articles:
            url_count[article.get('url', '')] += 1
        
        duplicate_urls = {url: count for url, count in url_count.items() if count > 1}
        
        # Estatísticas
        stats = {
            "topic_id": str(topic_id),
            "title": topic.get("title", "Sem título"),
            "article_count": len(articles),
            "duplicate_urls": duplicate_urls,
            "duplicate_count": sum(1 for count in url_count.values() if count > 1)
        }
        topic_stats.append(stats)
        
        # Verificar se há artigos duplicados entre tópicos
        for article in articles:
            article_id = str(article["_id"])
            if article_id in all_article_ids:
                duplicate_article_count += 1
            all_article_ids.add(article_id)
    
    # Encontrar URLs duplicadas no banco de dados
    duplicate_urls = await find_duplicate_articles()
    
    # Exibir relatório
    logger.info("\n📈 ESTATÍSTICAS DOS TÓPICOS")
    logger.info("=" * 80)
    
    if not topic_stats:
        logger.warning("⚠️  Nenhum tópico ativo encontrado no banco de dados.")
        return
    
    for i, stats in enumerate(topic_stats, 1):
        logger.info(f"\n📌 TÓPICO {i}/{len(topic_stats)}")
        logger.info(f"   Título: {stats['title']}")
        logger.info(f"   ID: {stats['topic_id']}")
        logger.info(f"   📚 Total de artigos: {stats['article_count']}")
        
        # Mostrar os primeiros 3 artigos como amostra
        topic_articles = await get_articles_for_topic(stats['topic_id'])
        if topic_articles:
            logger.info("\n   📰 Amostra de artigos:")
            for j, article in enumerate(topic_articles[:3], 1):
                title = article.get('title', 'Sem título')
                source = article.get('source_name', 'Fonte desconhecida')
                date = article.get('publish_date', 'Data desconhecida')
                logger.info(f"      {j}. {title}")
                logger.info(f"         📅 {date} | 📰 {source}")
        
        if stats['duplicate_count'] > 0:
            logger.warning(f"\n   ⚠️  ATENÇÃO: {stats['duplicate_count']} URLs duplicadas encontradas neste tópico")
    
    # Análise de duplicatas
    logger.info("\n🔍 ANÁLISE DE DUPLICATAS")
    logger.info("=" * 80)
    
    if duplicate_urls:
        logger.warning(f"⚠️  ENCONTRADAS {len(duplicate_urls)} URLs DUPLICADAS NO BANCO DE DADOS")
        logger.warning("   Estas são notícias idênticas armazenadas múltiplas vezes.")
        
        # Mostrar apenas as 5 primeiras duplicatas para não sobrecarregar o log
        for i, (url, articles) in enumerate(duplicate_urls.items(), 1):
            if i > 5:  # Limitar a 5 exemplos
                remaining = len(duplicate_urls) - 5
                logger.warning(f"\n   ...e mais {remaining} URLs duplicadas não mostradas.")
                break
                
            logger.warning(f"\n   🔗 URL DUPLICADA {i}:")
            logger.warning(f"      {url}")
            logger.warning(f"      Aparece em {len(articles)} documentos diferentes:")
            
            for j, article in enumerate(articles[:3], 1):  # Mostrar até 3 ocorrências
                title = article.get('title', 'Sem título')
                source = article.get('source_name', 'Fonte desconhecida')
                date = article.get('publish_date', 'Data desconhecida')
                logger.warning(f"      {j}. {title}")
                logger.warning(f"         📅 {date} | 📰 {source} | 🆔 {article['_id']}")
            
            if len(articles) > 3:
                logger.warning(f"      ...e mais {len(articles) - 3} ocorrências")
    else:
        logger.info("✅ Nenhuma URL duplicada encontrada no banco de dados.")
    
    # Estatísticas finais
    logger.info("\n📊 ESTATÍSTICAS GERAIS")
    logger.info("=" * 80)
    logger.info(f"   📂 Total de tópicos ativos: {len(topic_stats)}")
    logger.info(f"   📰 Total de artigos únicos em tópicos: {len(all_article_ids)}")
    logger.info(f"   🔄 Artigos presentes em múltiplos tópicos: {duplicate_article_count}")
    
    # Recomendações
    logger.info("\n💡 RECOMENDAÇÕES")
    logger.info("=" * 80)
    if duplicate_urls:
        logger.warning("   ⚠️  Recomendação: Considere implementar uma limpeza de duplicatas")
        logger.warning("       para remover notícias idênticas do banco de dados.")
    else:
        logger.info("   ✅ O banco de dados está limpo, sem duplicatas detectadas.")
    
    if duplicate_article_count > 0:
        logger.warning(f"   ⚠️  {duplicate_article_count} artigos aparecem em múltiplos tópicos.")
        logger.warning("       Verifique se esta duplicação é intencional.")

def main():
    """Função principal para execução do script."""
    try:
        logger.info("🚀 Iniciando verificação de tópicos e notícias duplicadas...")
        asyncio.run(check_topics())
        logger.info("✅ Verificação concluída com sucesso!")
    except Exception as e:
        logger.error(f"❌ Erro durante a execução do script: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
