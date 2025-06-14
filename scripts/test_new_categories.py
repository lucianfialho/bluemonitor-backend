"""Script para testar as novas categorias de classificação."""
import asyncio
import sys
from motor.motor_asyncio import AsyncIOMotorClient
from pprint import pprint
from datetime import datetime, timedelta

# Adiciona o diretório raiz ao path para importar os módulos
sys.path.append('/app')

# Importa a classe atualizada
from app.services.ai.topic_cluster_updated import TopicCluster

class CategoryTester:
    """Classe para testar a classificação de categorias."""
    
    def __init__(self):
        """Inicializa o testador de categorias."""
        self.classifier = TopicCluster()
    
    async def test_with_sample_articles(self):
        """Testa a classificação com artigos de exemplo."""
        samples = [
            {
                'title': 'Novo tratamento com terapia ocupacional mostra resultados promissores',
                'description': 'Estudo revela avanços no tratamento de crianças autistas',
                'content': 'A terapia ocupacional tem se mostrado eficaz...'
            },
            {
                'title': 'Escola é multada por não fornecer professor de apoio',
                'description': 'Justiça condena escola por descumprir lei de inclusão',
                'content': 'A escola foi multada em R$ 50 mil...'
            },
            {
                'title': 'Câmara aprova projeto que amplia direitos de autistas',
                'description': 'Nova lei garante mais benefícios para pessoas com TEA',
                'content': 'O projeto foi aprovado por unanimidade...'
            },
            {
                'title': 'Criança autista sofre bullying em escola de São Paulo',
                'description': 'Caso de agressão chama atenção para a necessidade de conscientização',
                'content': 'O menino de 8 anos foi vítima de agressões...'
            },
            {
                'title': 'Aplicativo ajuda na comunicação de crianças não verbais',
                'description': 'Ferrama usa IA para facilitar a comunicação alternativa',
                'content': 'O app já está disponível para download...'
            }
        ]
        
        print("=== Teste de Classificação de Categorias ===\n")
        
        for i, article in enumerate(samples, 1):
            category = self.classifier._categorize_article(article)
            print(f"Artigo {i}: {article['title']}")
            print(f"Categoria: {category}")
            print("-" * 80)
    
    async def test_with_database_articles(self, limit=10):
        """Testa a classificação com artigos reais do banco de dados."""
        client = AsyncIOMotorClient('mongodb://mongodb:27017')
        db = client.bluemonitor
        
        try:
            # Busca os artigos mais recentes
            articles = await db.news.find() \
                .sort('publish_date', -1) \
                .limit(limit) \
                .to_list(length=limit)
            
            print(f"\n=== Teste com {len(articles)} artigos do banco de dados ===\n")
            
            for i, article in enumerate(articles, 1):
                category = self.classifier._categorize_article(article)
                print(f"{i}. {article.get('title', 'Sem título')}")
                print(f"   Categoria: {category}")
                print(f"   Fonte: {article.get('source_name', 'N/A')}")
                print("   " + ("-" * 70))
                
        except Exception as e:
            print(f"Erro ao acessar o banco de dados: {e}")
        finally:
            client.close()

async def main():
    """Função principal."""
    tester = CategoryTester()
    
    print("1. Testando com artigos de exemplo...")
    await tester.test_with_sample_articles()
    
    print("\n2. Testando com artigos reais do banco de dados...")
    await tester.test_with_database_articles(limit=5)

if __name__ == "__main__":
    asyncio.run(main())
