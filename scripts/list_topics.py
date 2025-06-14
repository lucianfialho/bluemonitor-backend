"""Script para listar tópicos e categorias do MongoDB."""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from pprint import pprint

async def list_topics():
    """Lista os tópicos do MongoDB."""
    # Conectar ao MongoDB
    client = AsyncIOMotorClient('mongodb://mongodb:27017')
    db = client.bluemonitor
    
    try:
        # Contar o total de tópicos
        total = await db.topics.count_documents({})
        print(f"\n=== Total de tópicos: {total} ===\n")
        
        # Buscar os 10 tópicos mais recentes
        cursor = db.topics.find().sort('updated_at', -1).limit(10)
        topics = await cursor.to_list(length=10)
        
        print("=== Últimos 10 tópicos ===")
        for topic in topics:
            print(f"\nID: {topic['_id']}")
            print(f"Título: {topic.get('title', 'Sem título')}")
            print(f"Categoria: {topic.get('category', 'Sem categoria')}")
            print(f"Artigos: {topic.get('article_count', 0)}")
            print(f"Fontes: {', '.join(topic.get('sources', ['Nenhuma']))}")
            print(f"Palavras-chave: {', '.join(topic.get('keywords', [])[:5])}")
            print(f"Atualizado em: {topic.get('updated_at', 'N/A')}")
            print("-" * 50)
        
        # Contar tópicos por categoria
        pipeline = [
            {"$group": {
                "_id": "$category",
                "count": {"$sum": 1},
                "total_articles": {"$sum": "$article_count"}
            }},
            {"$sort": {"count": -1}}
        ]
        
        print("\n=== Estatísticas por Categoria ===")
        async for doc in db.topics.aggregate(pipeline):
            print(f"{doc['_id']}: {doc['count']} tópicos, {doc['total_articles']} artigos")
        
        # Verificar tópicos sem categoria
        uncategorized = await db.topics.count_documents({"$or": [
            {"category": {"$exists": False}},
            {"category": ""}
        ]})
        print(f"\nTópicos sem categoria: {uncategorized}")
        
        # Verificar tópicos com poucos artigos
        few_articles = await db.topics.count_documents({"article_count": {"$lt": 2}})
        print(f"Tópicos com menos de 2 artigos: {few_articles}")
        
    except Exception as e:
        print(f"Erro ao acessar o banco de dados: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(list_topics())
