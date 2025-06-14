#!/usr/bin/env python3
"""
Classifica notícias direto no banco, sem depender da API.
"""
import asyncio
from app.core.database import MongoDBManager
from app.services.ai.topic_cluster_updated import TopicCluster

async def classify_direct_from_db():
    """Classifica notícias direto do banco."""
    
    print("🎯 CLASSIFICANDO DIRETO DO BANCO")
    print("="*50)
    
    manager = MongoDBManager()
    await manager.connect_to_mongodb()
    db = manager.db
    
    classifier = TopicCluster()
    
    # Buscar notícias mais recentes que não foram classificadas
    query = {
        "$or": [
            {"categories": {"$exists": False}},
            {"categories": {"$eq": []}},
            {"categories": {"$size": 0}}
        ]
    }
    
    # Ordenar por data mais recente
    cursor = db.news.find(query).sort("published_at", -1).limit(10)
    news_list = await cursor.to_list(length=None)
    
    print(f"📊 Encontradas {len(news_list)} notícias para classificar")
    
    classified_count = 0
    
    for i, news in enumerate(news_list, 1):
        print(f"\n--- NOTÍCIA {i} ---")
        title = news.get('title', '')
        print(f"📰 Título: {title}")
        print(f"📅 Data: {news.get('published_at', 'N/A')}")
        
        description = news.get('description', '')
        content = news.get('content', '') or description or title
        
        # Testar relevância
        is_relevant = classifier.is_relevant(content or title)
        print(f"🔍 Relevante: {is_relevant}")
        
        if is_relevant:
            # Classificar
            article = {
                'title': title,
                'description': description,
                'content': content or title
            }
            
            category = classifier._categorize_article(article)
            print(f"🎯 Categoria inicial: {category}")
            
            # Lógica especial para casos óbvios
            title_lower = title.lower()
            
            if any(word in title_lower for word in ["agredido", "agressão", "violência", "bullying"]):
                category = "violencia_discriminacao"
                print("   🚨 FORÇADO: violencia_discriminacao")
                
            elif any(word in title_lower for word in ["aprova", "lei", "projeto", "direito", "beneficia"]):
                category = "direitos_legislacao"
                print("   ⚖️  FORÇADO: direitos_legislacao")
                
            elif any(word in title_lower for word in ["símbolos", "conscientização", "campanha"]):
                category = "educacao_inclusiva"
                print("   📚 FORÇADO: educacao_inclusiva")
            
            # Atualizar no banco
            await db.news.update_one(
                {"_id": news["_id"]},
                {
                    "$set": {
                        "categories": [category],
                        "classified_at": datetime.utcnow(),
                        "is_relevant": True,
                        "classification_version": "v3_direct_db"
                    }
                }
            )
            
            classified_count += 1
            print(f"✅ Salvo como: {category}")
            
        else:
            print("❌ Não relevante")
            await db.news.update_one(
                {"_id": news["_id"]},
                {
                    "$set": {
                        "categories": [],
                        "classified_at": datetime.utcnow(),
                        "is_relevant": False,
                        "classification_version": "v3_direct_db"
                    }
                }
            )
    
    print(f"\n📊 RESUMO:")
    print(f"Processadas: {len(news_list)}")
    print(f"Classificadas: {classified_count}")
    
    # Verificar resultados no banco
    print(f"\n📋 VERIFICANDO RESULTADOS...")
    
    # Contar por categoria
    categories = ["violencia_discriminacao", "direitos_legislacao", "educacao_inclusiva", "saude_tratamento"]
    
    for cat in categories:
        count = await db.news.count_documents({"categories": cat})
        print(f"{cat}: {count} notícias")
        
        if count > 0:
            # Mostrar exemplo
            example = await db.news.find_one({"categories": cat})
            if example:
                print(f"   Exemplo: {example.get('title', 'N/A')[:50]}...")
    
    await manager.close_mongodb_connection()
    
    print(f"\n🎉 CLASSIFICAÇÃO CONCLUÍDA!")
    print("Agora você pode testar:")
    print("1. Reiniciar a API: docker-compose restart api")
    print("2. Testar: curl http://localhost:8000/api/v1/news?limit=3")
    print("3. Filtrar: curl http://localhost:8000/api/v1/news?category=violencia_discriminacao")

if __name__ == "__main__":
    from datetime import datetime
    asyncio.run(classify_direct_from_db())