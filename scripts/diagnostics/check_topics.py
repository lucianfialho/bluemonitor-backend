import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def check_topics():
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    db = client.bluemonitor
    
    # Conta o número total de tópicos
    count = await db.topics.count_documents({})
    print(f'Total de tópicos: {count}')
    
    # Se houver tópicos, mostra o nome do primeiro
    if count > 0:
        doc = await db.topics.find_one({})
        print(f'Exemplo de tópico: {doc.get("name", "Sem nome")}')
    
    client.close()

if __name__ == "__main__":
    asyncio.run(check_topics())
