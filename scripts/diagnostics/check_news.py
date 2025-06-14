import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

async def check_db():
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    db = client.bluemonitor
    
    # Conta o número total de notícias
    count = await db.news.count_documents({})
    print(f'Total de notícias: {count}')
    
    # Se houver notícias, mostra o ID da primeira
    if count > 0:
        doc = await db.news.find_one({})
        print(f'Exemplo de ID: {doc["_id"]}')
        print(f'Título: {doc.get("title", "Sem título")}')
    
    client.close()

if __name__ == "__main__":
    asyncio.run(check_db())
