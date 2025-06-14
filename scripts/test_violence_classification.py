"""Teste específico para classificação de violência e discriminação."""
import asyncio
from app.services.ai.topic_cluster_updated import TopicCluster

async def test_violence_classification():
    """Testa a classificação de artigos sobre violência."""
    classifier = TopicCluster()
    
    test_cases = [
        {
            'title': 'Avó diz que neto autista foi agredido em escola particular',
            'description': 'Criança com autismo sofreu agressões físicas de colegas',
            'content': 'A avó relatou que a criança sofreu agressões repetidas na escola...'
        },
        {
            'title': 'Estudante autista sore bullying em colégio de São Paulo',
            'description': 'Pais denunciam caso de bullying contra adolescente com TEA',
            'content': 'O adolescente de 14 anos sofreu humilhações e agressões...'
        },
        {
            'title': 'Escola é processada por não intervir em caso de agressão a aluno autista',
            'description': 'Família processa instituição por omissão em caso de violência contra estudante com TEA',
            'content': 'A direção da escola foi acusada de não tomar as devidas providências após o aluno autista sofrer agressões...'
        },
        {
            'title': 'Justiça condena colégio por falha na proteção de estudante autista',
            'description': 'Instituição terá que indenizar família por danos morais',
            'content': 'O juiz considerou que a escola falhou em seu dever de proteção ao estudante com autismo...'
        },
        {
            'title': 'MPE move ação contra escola por omissão em caso de bullying',
            'description': 'Ministério Público Estadual acusa instituição de não proteger aluno com necessidades especiais',
            'content': 'O MPE entrou com uma ação civil pública contra a escola por não ter adotado medidas para coibir o bullying...'
        },
        {
            'title': 'Aluno autista é vítima de preconceito em sala de aula',
            'description': 'Professor teria feito comentários discriminatórios',
            'content': 'Os pais registraram boletim de ocorrência contra o educador...'
        }
    ]
    
    print("=== Teste de Classificação de Violência e Discriminação ===\n")
    
    for i, article in enumerate(test_cases, 1):
        category = classifier._categorize_article(article)
        print(f"Caso {i}: {article['title']}")
        print(f"Descrição: {article['description']}")
        print(f"Categoria: {category}")
        print("-" * 80)

if __name__ == "__main__":
    asyncio.run(test_violence_classification())
