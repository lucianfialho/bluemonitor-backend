#!/usr/bin/env python3
"""
Script simples para classificar notícias usando o sistema atualizado
"""

import asyncio
import sys
import os
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient

# Configuração
MONGODB_URL = "mongodb://mongodb:27017"
DATABASE_NAME = "bluemonitor"

sys.path.append('.')

async def classify_all_news():
    """Classifica todas as notícias usando o sistema atualizado."""
    
    try:
        # Importa o classificador
        from app.services.ai.topic_cluster import TopicCluster
        classifier = TopicCluster()
        
        print("🔍 Conectando ao MongoDB...")
        client = AsyncIOMotorClient(MONGODB_URL)
        db = client[DATABASE_NAME]
        
        # Busca todas as notícias
        print("📰 Buscando notícias...")
        cursor = db.news.find({})
        news_list = await cursor.to_list(length=None)
        
        print(f"📊 Encontradas {len(news_list)} notícias para classificar")
        
        if not news_list:
            print("❌ Nenhuma notícia encontrada!")
            return
        
        # Classifica cada notícia
        classified_count = 0
        category_stats = {}
        
        for i, news in enumerate(news_list, 1):
            try:
                # Classifica usando o método _categorize_article
                category = classifier._categorize_article(news)
                
                # Atualiza estatísticas
                category_stats[category] = category_stats.get(category, 0) + 1
                
                # Atualiza no banco se a categoria não é 'outros' ou 'irrelevante'
                if category and category.lower() not in ['outros', 'irrelevante']:
                    await db.news.update_one(
                        {"_id": news["_id"]},
                        {
                            "$set": {
                                "topic_category": category,
                                "classification_updated_at": datetime.now()
                            }
                        }
                    )
                    classified_count += 1
                
                # Progresso
                if i % 10 == 0:
                    print(f"   Processadas {i}/{len(news_list)} notícias...")
                    
            except Exception as e:
                print(f"❌ Erro ao classificar notícia {news.get('_id')}: {e}")
        
        print(f"\n✅ Classificação concluída!")
        print(f"📊 Estatísticas:")
        print(f"   • Total de notícias: {len(news_list)}")
        print(f"   • Classificadas com sucesso: {classified_count}")
        print(f"   • Taxa de sucesso: {(classified_count/len(news_list)*100):.1f}%")
        
        print(f"\n📂 Distribuição por categoria:")
        for category, count in sorted(category_stats.items(), key=lambda x: x[1], reverse=True):
            print(f"   • {category}: {count} notícias")
        
        client.close()
        return category_stats
        
    except Exception as e:
        print(f"❌ Erro durante classificação: {e}")
        import traceback
        traceback.print_exc()

async def test_classification():
    """Testa a classificação com algumas notícias."""
    
    try:
        from app.services.ai.topic_cluster import TopicCluster
        classifier = TopicCluster()
        
        print("🧪 Testando classificação...")
        
        # Artigos de teste
        test_articles = [
            {
                "title": "Avó diz que neto autista foi agredido em escola particular",
                "description": "Caso de violência contra criança autista",
                "content": "A avó relatou que o neto foi agredido..."
            },
            {
                "title": "Girassol, infinito e quebra-cabeça: entenda os símbolos do autismo",
                "description": "Artigo sobre símbolos e direitos",
                "content": "Os símbolos representam..."
            },
            {
                "title": "CMU aprova projetos que beneficiam autistas",
                "description": "Aprovação de projetos legislativos",
                "content": "A câmara municipal aprovou..."
            }
        ]
        
        for i, article in enumerate(test_articles, 1):
            category = classifier._categorize_article(article)
            print(f"{i}. {article['title'][:50]}...")
            print(f"   → Categoria: {category}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        return False

async def main():
    """Função principal."""
    
    print("🚀 CLASSIFICAÇÃO AUTOMÁTICA DE NOTÍCIAS")
    print("=" * 50)
    
    # Primeiro, testa se funciona
    print("1️⃣ Testando o sistema...")
    if not await test_classification():
        print("❌ Teste falhou. Verifique a configuração.")
        return
    
    print("\n2️⃣ Sistema funcionando! Iniciando classificação completa...")
    
    # Executa classificação completa
    stats = await classify_all_news()
    
    if stats:
        print(f"\n🎉 Classificação concluída com sucesso!")
        print(f"💡 Teste os resultados:")
        print(f"   curl \"http://localhost:8000/api/v1/news?limit=5\" | jq '.data[] | {{title: .title, category: .topic_category}}'")

if __name__ == "__main__":
    asyncio.run(main())