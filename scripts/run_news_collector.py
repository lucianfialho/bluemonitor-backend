"""Script para executar o coletor de notícias manualmente."""
import asyncio
import logging
import sys
from pathlib import Path

# Adicionar o diretório raiz ao path para importar os módulos do projeto
sys.path.append(str(Path(__file__).parent.parent))

from app.core.config import settings
from app.core.database import mongodb_manager
from app.services.news.collector import news_collector
from app.services.ai.topic_cluster import topic_cluster

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Lista de consultas de busca para coleta de notícias
SEARCH_QUERIES = [
    "autismo Brasil",
    "TEA Brasil",
    "transtorno do espectro autista",
    "inclusão autismo",
    "direitos autistas",
    "tratamento autismo",
    "educação especial autismo"
]

# País para coleta de notícias
COUNTRY = 'BR'

async def main():
    """Função principal para executar o coletor de notícias."""
    try:
        # Conectar ao MongoDB
        await mongodb_manager.connect_to_mongodb()
        if mongodb_manager.db is None:
            logger.error("❌ Não foi possível conectar ao banco de dados")
            return
        
        logger.info("✅ Conectado ao MongoDB")
        
        # Coletar notícias para cada consulta
        for query in SEARCH_QUERIES:
            try:
                logger.info(f"🔍 Coletando notícias para: {query}")
                await news_collector.process_news_batch(query, COUNTRY)
                logger.info(f"✅ Concluída coleta para: {query}")
            except Exception as e:
                logger.error(f"❌ Erro ao processar a consulta '{query}': {str(e)}", exc_info=True)
        
        # Agrupar notícias em tópicos
        logger.info("🔍 Agrupando notícias em tópicos...")
        await topic_cluster.cluster_recent_news(COUNTRY)
        logger.info("✅ Agrupamento de tópicos concluído")
        
    except Exception as e:
        logger.error(f"❌ Erro durante a execução: {str(e)}", exc_info=True)
    finally:
        # Fechar conexão com o banco de dados
        await mongodb_manager.close_mongodb_connection()
        logger.info("🔌 Conexão com o MongoDB encerrada")

if __name__ == "__main__":
    asyncio.run(main())
