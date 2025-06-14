import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def count_news():
    client = None
    try:
        client = AsyncIOMotorClient('mongodb://localhost:27017')
        db = client['bluemonitor']
        count = await db.news.count_documents({})
        print(f'Total de notícias: {count}')
        
        # Verificar se há documentos
        if count > 0:
            # Pegar o primeiro documento para inspecionar
            doc = await db.news.find_one()
            print("\nPrimeiro documento:")
            print(doc)
        else:
            print("A coleção de notícias está vazia.")
            
    except Exception as e:
        print(f"Erro ao acessar o banco de dados: {e}")
    finally:
        if client:
            client.close()

if __name__ == "__main__":
    asyncio.run(count_news())
