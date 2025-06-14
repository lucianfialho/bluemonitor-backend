"""Script para testar a classificação com notícias reais do banco de dados."""
import asyncio
import sys
from datetime import datetime, timedelta
from pprint import pprint

# Adiciona o diretório raiz ao path para importar os módulos
sys.path.append('/app')

from motor.motor_asyncio import AsyncIOMotorClient
from app.services.ai.topic_cluster_updated import TopicCluster

class NewsClassifierTester:
    """Classe para testar a classificação de notícias reais."""
    
    def __init__(self):
        """Inicializa o testador de classificação."""
        self.classifier = TopicCluster()
        self.mongodb_uri = 'mongodb://mongodb:27017'
        self.db_name = 'bluemonitor'
    
    async def get_recent_news(self, limit=20):
        """Obtém as notícias mais recentes do banco de dados."""
        client = AsyncIOMotorClient(self.mongodb_uri)
        db = client[self.db_name]
        
        try:
            # Busca as notícias mais recentes
            cursor = db.news.find().sort('publish_date', -1).limit(limit)
            return await cursor.to_list(length=limit)
        except Exception as e:
            print(f"Erro ao buscar notícias: {e}")
            return []
        finally:
            client.close()
    
    def print_news_with_category(self, news_list):
        """Imprime as notícias com suas categorias."""
        print(f"\n=== Classificação de {len(news_list)} Notícias Reais ===\n")
        
        category_counts = {}
        
        for i, news in enumerate(news_list, 1):
            # Classifica a notícia
            category = self.classifier._categorize_article(news)
            
            # Atualiza a contagem de categorias
            category_counts[category] = category_counts.get(category, 0) + 1
            
            # Imprime os detalhes da notícia
            print(f"\n{i}. {news.get('title', 'Sem título')}")
            print(f"   Fonte: {news.get('source_name', 'N/A')}")
            print(f"   Data: {news.get('publish_date', 'N/A')}")
            print(f"   Categoria: {category}")
            
            # Mostra um trecho do conteúdo (opcional)
            content_preview = (news.get('content', '')[:150] + '...') if news.get('content') else 'Sem conteúdo'
            print(f"   Conteúdo: {content_preview}")
            print("   " + ("-" * 70))
        
        # Imprime o resumo por categoria
        print("\n=== Resumo por Categoria ===")
        for category, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"{category}: {count} notícias")
    
    async def run(self):
        """Executa o teste de classificação."""
        print("Buscando notícias recentes no banco de dados...")
        news_list = await self.get_recent_news(limit=20)
        
        if not news_list:
            print("Nenhuma notícia encontrada no banco de dados.")
            return
        
        self.print_news_with_category(news_list)

async def main():
    """Função principal."""
    tester = NewsClassifierTester()
    await tester.run()

if __name__ == "__main__":
    asyncio.run(main())
