"""Script para testar a coleta de notícias."""
import asyncio
import logging
import sys
from pathlib import Path

# Adiciona o diretório raiz ao path para importações
sys.path.append(str(Path(__file__).parent.parent))

from app.services.news.collector import news_collector

# Configuração básica de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_news_collection():
    """Testa a coleta de notícias."""
    try:
        logger.info("Iniciando teste de coleta de notícias...")
        
        # Testa com um termo de busca genérico
        query = "tecnologia"
        logger.info(f"Buscando notícias para: {query}")
        
        # Executa a coleta
        results = await news_collector.process_news_batch(query)
        
        # Exibe os resultados
        logger.info("\n=== Resultados da Coleta ===")
        logger.info(f"Total processado: {results['total_processed']}")
        logger.info(f"Sucesso: {results['successful']}")
        logger.info(f"Falhas: {results['failed']}")
        
        if results['errors']:
            logger.warning("\n=== Erros Encontrados ===")
            for error in results['errors']:
                logger.error(f"- {error}")
        
        logger.info("Teste de coleta concluído!")
        
    except Exception as e:
        logger.error(f"Erro durante o teste de coleta: {str(e)}", exc_info=True)
        return False
    
    return True

if __name__ == "__main__":
    # Executa o teste
    success = asyncio.run(test_news_collection())
    sys.exit(0 if success else 1)
