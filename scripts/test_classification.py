"""Script para testar e melhorar a classificação de notícias."""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from pprint import pprint
from collections import defaultdict

class ClassificationTester:
    """Classe para testar e melhorar a classificação de notícias."""
    
    def __init__(self):
        """Inicializa o classificador com as categorias."""
        # Categorias aprimoradas com palavras-chave mais específicas
        self.categories = {
            'Saúde': [
                'saúde mental', 'tratamento autismo', 'TEA', 'terapia ocupacional',
                'fonoaudiologia', 'psicólogo infantil', 'neurodesenvolvimento',
                'intervenção precoce', 'comorbidades', 'medicação autismo'
            ],
            'Direitos': [
                'direitos autistas', 'lei berenice piana', 'inclusão social',
                'acessibilidade', 'direito à educação', 'benefício assistencial',
                'direitos trabalhistas', 'estatuto da pessoa com deficiência'
            ],
            'Tecnologia Assistiva': [  # Renomeada para ser mais específica
                'tecnologia assistiva', 'comunicação alternativa', 'CAA',
                'aplicativo autismo', 'software educacional', 'dispositivo adaptado',
                'tecnologia inclusiva', 'recursos de acessibilidade'
            ],
            'Educação': [
                'educação inclusiva', 'sala de aula', 'professor de apoio',
                'adaptação curricular', 'escola inclusiva', 'ensino especial',
                'plano educacional individualizado', 'inclusão escolar'
            ],
            'Pesquisa': [
                'estudo científico', 'pesquisa autismo', 'descoberta científica',
                'artigo científico', 'neurociência', 'genética autismo',
                'pesquisa clínica', 'ensaios clínicos'
            ],
            'Família e Cuidadores': [  # Renomeada para ser mais específica
                'mãe de autista', 'pai de autista', 'cuidadores',
                'convívio familiar', 'rede de apoio', 'luto do diagnóstico',
                'qualidade de vida familiar'
            ],
            'Inclusão Social': [
                'inclusão no mercado de trabalho', 'vida independente',
                'moradia assistida', 'autonomia', 'emprego apoiado',
                'projeto de vida', 'envelhecimento e autismo'
            ],
            'Políticas Públicas': [  # Nova categoria
                'políticas públicas', 'leis de inclusão', 'direitos autistas',
                'saúde pública', 'SUS', 'benefícios governamentais',
                'movimento autista', 'conselhos de direitos'
            ]
        }
        
        # Palavras-chave para identificar conteúdo irrelevante
        self.irrelevant_keywords = [
            'futebol', 'esporte', 'celebridade', 'entretenimento', 'novela', 'cinema',
            'música', 'show', 'festival', 'bbb', 'big brother', 'lazer', 'viagem',
            'turismo', 'culinária', 'receita', 'moda', 'beleza', 'automobilismo'
        ]
        
        # Termos que devem estar presentes para considerar relevante
        self.required_terms = [
            'autis', 'TEA', 'transtorno do espectro autista', 'neurodiversidade',
            'neurodivergente', 'transtorno invasivo do desenvolvimento'
        ]

    def is_relevant(self, text: str) -> bool:
        """Verifica se o texto é relevante para autismo."""
        if not text:
            return False
            
        text_lower = text.lower()
        
        # Verifica se contém algum termo obrigatório
        has_required = any(term in text_lower for term in self.required_terms)
        
        # Verifica se contém palavras irrelevantes
        has_irrelevant = any(term in text_lower for term in self.irrelevant_keywords)
        
        # É relevante se tem termos obrigatórios E não tem termos irrelevantes
        return has_required and not has_irrelevant

    def categorize_article(self, article: dict) -> str:
        """Categoriza um artigo nas categorias definidas."""
        if not article:
            return 'Irrelevante'
            
        # Extrai o texto para análise
        text = ' '.join([
            article.get('title', ''),
            article.get('description', ''),
            article.get('content', '')
        ]).lower()
        
        # Verifica se é relevante
        if not self.is_relevant(text):
            return 'Irrelevante'
        
        # Calcula a pontuação para cada categoria
        category_scores = {}
        for category, keywords in self.categories.items():
            score = sum(1 for keyword in keywords if keyword.lower() in text)
            if score > 0:
                category_scores[category] = score
        
        # Retorna a categoria com maior pontuação ou 'Outros' se não encontrar
        if category_scores:
            return max(category_scores.items(), key=lambda x: x[1])[0]
        return 'Outros'

    async def test_classification(self):
        """Testa a classificação com artigos reais do banco de dados."""
        client = AsyncIOMotorClient('mongodb://mongodb:27017')
        db = client.bluemonitor
        
        try:
            # Busca os últimos 50 artigos
            articles = await db.news.find().sort('publish_date', -1).limit(50).to_list(length=50)
            
            # Classifica cada artigo
            results = []
            category_counts = defaultdict(int)
            
            for article in articles:
                category = self.categorize_article(article)
                results.append({
                    'title': article.get('title', 'Sem título'),
                    'original_category': article.get('category', 'N/A'),
                    'new_category': category,
                    'url': article.get('url', 'N/A')
                })
                category_counts[category] += 1
            
            # Imprime os resultados
            print("\n=== Distribuição de Categorias ===")
            for category, count in category_counts.items():
                print(f"{category}: {count} artigos")
            
            print("\n=== Exemplos de Classificação ===")
            for i, result in enumerate(results[:10]):  # Mostra os 10 primeiros
                print(f"\n{i+1}. {result['title']}")
                print(f"   Categoria original: {result['original_category']}")
                print(f"   Nova categoria: {result['new_category']}")
                print(f"   URL: {result['url']}")
            
            return results
                
        except Exception as e:
            print(f"Erro ao testar classificação: {e}")
            return []
        finally:
            client.close()

if __name__ == "__main__":
    tester = ClassificationTester()
    asyncio.run(tester.test_classification())
