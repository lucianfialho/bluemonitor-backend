#!/bin/bash
echo "🔍 VERIFICANDO USO REAL DOS MÓDULOS..."

echo "1. Testando endpoints questionáveis:"
echo "Topics:" 
docker exec bluemonitor-api curl -s "http://localhost:8000/api/v1/topics" 2>/dev/null | head -c 100
echo -e "\nCategories:"
docker exec bluemonitor-api curl -s "http://localhost:8000/api/v1/categories" 2>/dev/null | head -c 100

echo -e "\n2. Verificando imports de IA:"
echo "Processamento IA:"
grep -r "ai_processor\|process_news_content" app/services/news/ 2>/dev/null || echo "Não encontrado"

echo -e "\n3. Verificando clustering:"
grep -r "topic_cluster\|TopicCluster" app/services/news/ 2>/dev/null || echo "Não encontrado"

echo -e "\n4. Verificando classificação avançada:"
grep -r "classification" app/services/news/ 2>/dev/null || echo "Não encontrado"

echo -e "\n5. Verificando middleware:"
grep -r "middleware" app/main.py 2>/dev/null || echo "Não encontrado"
