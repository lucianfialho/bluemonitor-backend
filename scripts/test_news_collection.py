"""Teste completo da coleta de notícias."""
import asyncio
import logging
from datetime import datetime, timedelta
from pprint import pprint

from app.core.database import MongoDBManager
from app.services.news.collector import news_collector

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_news_collection():
    """Testa todo o fluxo de coleta de notícias."""
    logger.info("Iniciando teste de coleta de notícias...")
    
    # 1. Testar busca de notícias
    query = "tecnologia"
    logger.info(f"Buscando notícias para: {query}")
    
    # 2. Executar coleta
    results = await news_collector.process_news_batch(query)
    
    # 3. Verificar resultados
    logger.info("\n=== Resultados da Coleta ===")
    logger.info(f"Total processado: {results['total_processed']}")
    logger.info(f"Sucesso: {results['successful']}")
    logger.info(f"Falhas: {results['failed']}")
    
    if results['errors']:
        logger.warning("\n=== Erros Encontrados ===")
        for error in results['errors']:
            logger.error(f"- {error}")
    
    # 4. Verificar notícias salvas no banco de dados
    logger.info("\n=== Verificando notícias no banco de dados ===")
    db_manager = MongoDBManager()
    
    try:
        await db_manager.connect_to_mongodb()
        
        # Encontrar as notícias mais recentes
        async with db_manager.get_db() as db:
            # Encontrar as últimas 10 notícias salvas
            latest_news = await db.news.find().sort('collection_date', -1).limit(10).to_list(length=10)
            
            if not latest_news:
                logger.error("Nenhuma notícia encontrada no banco de dados!")
                return False
            
            logger.info(f"Encontradas {len(latest_news)} notícias no banco de dados:")
            
            # Verificar cada notícia
            for i, news in enumerate(latest_news, 1):
                logger.info(f"\n--- Notícia {i} ---")
                logger.info(f"Título: {news.get('title', 'Sem título')}")
                logger.info(f"Fonte: {news.get('source_name', 'Desconhecida')}")
                logger.info(f"URL: {news.get('original_url', 'N/A')}")
                logger.info(f"Data de publicação: {news.get('published_at', 'N/A')}")
                logger.info(f"Data de coleta: {news.get('collection_date', 'N/A')}")
                
                # Verificar campos obrigatórios
                required_fields = ['title', 'original_url', 'published_at', 'collection_date']
                missing_fields = [field for field in required_fields if not news.get(field)]
                
                if missing_fields:
                    logger.warning(f"Campos obrigatórios ausentes: {', '.join(missing_fields)}")
                else:
                    logger.info("✓ Todos os campos obrigatórios estão presentes")
                
                # Verificar se as datas são válidas
                try:
                    pub_date = news.get('published_at')
                    if isinstance(pub_date, str):
                        pub_date = datetime.fromisoformat(pub_date.replace('Z', '+00:00'))
                    
                    if not isinstance(pub_date, datetime):
                        logger.warning("⚠ Data de publicação não é um objeto datetime")
                    elif pub_date > datetime.utcnow() + timedelta(days=1):
                        logger.warning(f"⚠ Data de publicação no futuro: {pub_date}")
                    
                    coll_date = news.get('collection_date')
                    if isinstance(coll_date, str):
                        coll_date = datetime.fromisoformat(coll_date.replace('Z', '+00:00'))
                    
                    if not isinstance(coll_date, datetime):
                        logger.warning("⚠ Data de coleta não é um objeto datetime")
                    elif coll_date > datetime.utcnow() + timedelta(minutes=5):
                        logger.warning(f"⚠ Data de coleta no futuro: {coll_date}")
                    
                    if isinstance(pub_date, datetime) and isinstance(coll_date, datetime):
                        if pub_date > coll_date + timedelta(days=1):
                            logger.warning(f"⚠ Data de publicação ({pub_date}) é posterior à data de coleta ({coll_date})")
                except Exception as e:
                    logger.error(f"Erro ao validar datas: {str(e)}")
            
            # Verificar se há duplicatas
            urls = [n.get('original_url') for n in latest_news if n.get('original_url')]
            if len(urls) != len(set(urls)):
                logger.warning("⚠ URLs duplicadas encontradas nas notícias recentes")
            
            # Verificar estrutura dos dados
            sample_news = latest_news[0]
            logger.info("\n=== Estrutura da primeira notícia ===")
            logger.info(f"Campos: {', '.join(sample_news.keys())}")
            
            # Verificar se os campos esperados estão presentes
            expected_fields = [
                'title', 'description', 'original_url', 'source_name', 
                'source_domain', 'published_at', 'collection_date', 
                'country_focus', 'in_topic', 'metadata'
            ]
            
            missing_expected = [f for f in expected_fields if f not in sample_news]
            if missing_expected:
                logger.warning(f"Campos esperados ausentes: {', '.join(missing_expected)}")
            
            # Verificar metadados
            metadata = sample_news.get('metadata', {})
            if not isinstance(metadata, dict):
                logger.warning("O campo 'metadata' não é um dicionário")
            else:
                logger.info("Metadados:")
                for k, v in metadata.items():
                    logger.info(f"  - {k}: {v}")
            
            return True
            
    except Exception as e:
        logger.error(f"Erro ao acessar o banco de dados: {str(e)}")
        return False
    finally:
        await db_manager.close_mongodb_connection()

if __name__ == "__main__":
    success = asyncio.run(test_news_collection())
    exit(0 if success else 1)
