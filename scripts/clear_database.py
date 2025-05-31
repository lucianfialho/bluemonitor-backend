"""Script para limpar o banco de dados MongoDB."""
import asyncio
import logging
import sys
from pathlib import Path

# Adicionar o diretório raiz ao path para importar os módulos do projeto
sys.path.append(str(Path(__file__).parent.parent))

from app.core.database import mongodb_manager
from app.core.config import settings

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def clear_database():
    """Limpa todas as coleções do banco de dados."""
    try:
        # Conectar ao MongoDB
        await mongodb_manager.connect_to_mongodb()
        
        if mongodb_manager.db is None:
            logger.error("❌ Não foi possível conectar ao banco de dados")
            return
        
        # Listar todas as coleções
        collections = await mongodb_manager.db.list_collection_names()
        
        if not collections:
            logger.info("ℹ️ Nenhuma coleção encontrada no banco de dados")
            return
        
        logger.info(f"📋 Coleções encontradas: {', '.join(collections)}")
        
        # Confirmar limpeza (sem input interativo)
        logger.warning(f"⚠️  Limpando TODAS as coleções no banco de dados '{settings.MONGODB_DB_NAME}'")
        logger.warning("⚠️  Esta operação NÃO PODE SER DESFEITA")
        
        # Limpar cada coleção
        for collection_name in collections:
            try:
                result = await mongodb_manager.db[collection_name].delete_many({})
                logger.info(f"🧹 Coleção '{collection_name}': {result.deleted_count} documentos removidos")
            except Exception as e:
                logger.error(f"❌ Erro ao limpar a coleção '{collection_name}': {str(e)}")
        
        logger.info("✅ Banco de dados limpo com sucesso!")
        
    except Exception as e:
        logger.error(f"❌ Erro ao limpar o banco de dados: {str(e)}")
    finally:
        # Fechar conexão
        await mongodb_manager.close_mongodb_connection()

if __name__ == "__main__":
    asyncio.run(clear_database())
