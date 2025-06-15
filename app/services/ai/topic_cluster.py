"""Topic clustering service for grouping related news articles."""
import logging
import re
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
from datetime import datetime, timedelta
from bson import ObjectId
from sklearn.cluster import DBSCAN
from sklearn.metrics.pairwise import cosine_similarity

from app.core.config import settings
from app.core.database import MongoDBManager
from app.services.ai.processor import ai_processor

logger = logging.getLogger(__name__)

from .fact_extraction import fact_extraction_system
from collections import Counter

class TopicCluster:
    """Service for clustering news articles into topics."""
    
    def __init__(self):
        """Initialize the topic clustering service."""
        self.min_samples = 1  # Permite clusters menores
        self.eps = 0.85  # Ajustado para melhor equilíbrio
        self.min_topic_size = 1  # Permite tópicos com apenas 1 artigo
        self.max_topic_age_days = 30  # Período maior para análise
        self.max_articles_to_process = 1000  # Aumentado para incluir mais artigos
        self.similarity_threshold = 0.4  # Reduzido para agrupar tópicos mais diversos
        
        # Categorias pré-definidas para classificação
        self.categories = {
            'saude_tratamento': [
                'terapia ocupacional', 'fonoaudiologia', 'psicólogo infantil',
                'neuropediatra', 'intervenção precoce', 'tratamento TEA',
                'comorbidades', 'medicação autismo', 'acompanhamento multidisciplinar',
                'saúde mental', 'terapia ABA', 'integração sensorial',
                'tratamento para autismo', 'saúde do autista', 'acompanhamento médico',
                'terapia para autismo', 'intervenção terapêutica', 'saúde infantil',
                'desenvolvimento infantil', 'neurodesenvolvimento', 'saúde neurológica',
                # Termos adicionais para medicações e tratamentos
                'medicamento', 'medicação', 'remédio', 'fármaco', 'droga',
                'aprovação', 'aprovado', 'liberação', 'liberado', 'autorização', 'autorizado',
                'anvisa', 'agência nacional de vigilância sanitária',
                'ministério da saúde', 'secretaria de saúde',
                'estudo clínico', 'ensaio clínico', 'estudo de fase',
                'eficácia', 'eficiente', 'efetivo', 'benefício',
                'efeito colateral', 'efeito adverso', 'contraindicação',
                'dose', 'dosagem', 'administração', 'prescrição',
                'tratamento medicamentoso', 'terapia medicamentosa',
                'neurológico', 'neurologia', 'neurologista',
                'psiquiátrico', 'psiquiatria', 'psiquiatra',
                'desenvolvimento neuropsicomotor', 'desenvolvimento cognitivo',
                'habilidades sociais', 'habilidades comunicativas',
                'transtorno de processamento sensorial', 'hipersensibilidade sensorial',
                'sintomas', 'manifestações', 'condições', 'comorbidade'
            ],
            'educacao_inclusiva': [
                'educação especial', 'sala de recursos', 'professor de apoio',
                'plano educacional individualizado', 'adaptação curricular',
                'escola inclusiva', 'métodos de ensino', 'alfabetização',
                'inclusão escolar', 'tecnologias educacionais',
                'ensino especial', 'atendimento educacional especializado',
                'educação inclusiva', 'práticas pedagógicas', 'currículo adaptado',
                'projeto pedagógico', 'ensino-aprendizagem', 'mediação escolar',
                'acessibilidade na educação', 'recursos pedagógicos', 'formação de professores',
                # Termos adicionais para educação inclusiva
                'ensino adaptado', 'aprendizagem adaptada', 'estratégias de ensino',
                'metodologia inclusiva', 'pedagogia inclusiva', 'didática inclusiva',
                'escola regular', 'classe regular', 'turma regular', 'ensino regular',
                'material adaptado', 'material didático adaptado', 'avaliação adaptada',
                'comunicação alternativa na escola', 'CAA na escola',
                'PECS na escola', 'método TEACCH', 'método ABA na escola',
                'apoio escolar', 'auxílio escolar', 'acompanhamento escolar',
                'monitor escolar', 'tutor escolar', 'mediador escolar',
                'profissional de apoio', 'acompanhante especializado',
                'ambiente sensorial na escola', 'escola amiga do autista',
                'sala sensorial', 'espaço sensorial', 'adaptação sensorial',
                'inclusão social na escola', 'socialização na escola'
            ],
            'direitos_legislacao': [
                'lei berenice piana', 'estatuto da pessoa com deficiência',
                'direitos trabalhistas', 'benefício assistencial', 'LOAS',
                'isenção de impostos', 'direito à educação', 'direitos autistas',
                'políticas públicas', 'conselhos de direitos'
            ],
            'violencia_discriminacao': [
                # Termos gerais de violência
                'bullying', 'agressão', 'agredid', 'violência', 'maus-tratos', 'abuso', 
                'assédio', 'xingamento', 'humilhação', 'ofensa', 'ameaça', 'intimidação',
                'perseguição', 'preconceito', 'discriminação', 'hostilidade', 'ofensa',
                'constrangimento', 'opressão', 'coerção',
                # Termos adicionais para discriminação sutil
                'exclusão', 'isolamento', 'segregação', 'separação',
                'negligência', 'descaso', 'indiferença', 'falta de atenção',
                'desrespeito', 'desprezo', 'ridicularização', 'estigmatização',
                'estereótipo', 'estereotipação', 'rótulo', 'rotulação',
                'olhar diferente', 'tratar diferente', 'tratamento diferenciado',
                'barreira atitudinal', 'barreira social', 'microagressão',
                'não aceitação', 'não inclusão', 'não adaptação',
                'inadequação', 'não apropriado', 'comportamento inadequado',
                'não é normal', 'anormal', 'diferente dos outros',
                'falta de empatia', 'falta de compreensão', 'falta de sensibilidade',
                'desinformação', 'desconhecimento', 'ignorância',
                'capacitismo', 'capacitista', 'preconceito sobre deficiência',
                
                # Termos específicos para violência física e psicológica
                'agressão física', 'violência física', 'violência psicológica', 
                'assédio moral', 'violência verbal', 'violência institucional',
                'violação de direitos', 'direitos violados', 'direito violado',
                'vítima de agressão', 'sofrendo agressão', 'sofrendo violência',
                
                # Contexto escolar
                'violência escolar', 'violência na escola', 'agressão na escola',
                'bullying escolar', 'assédio na escola', 'preconceito na escola',
                'discriminação na escola', 'violência entre alunos', 'briga de alunos',
                'conflito escolar', 'agressão entre alunos',
                
                # Responsabilização institucional
                'escola processada', 'processo contra escola', 'processo contra colégio',
                'responsabilidade da escola', 'responsabilidade do colégio',
                'ação judicial contra escola', 'processo judicial', 'ação judicial',
                'denúncia contra escola', 'reclamação contra escola', 'escola denunciada',
                'direção da escola', 'omissão da escola', 'falha da escola', 'erro da escola',
                'responsabilidade civil', 'indenização por danos', 'danos morais',
                'processo na justiça', 'na justiça', 'na vara da infância', 'MPE', 'Ministério Público',
                'conselho tutelar', 'conselho de direitos', 'direitos humanos',
                'notificação extrajudicial', 'notificação à escola', 'notificação ao colégio'
            ],
            'tecnologia_assistiva': [
                'comunicação alternativa', 'CAA', 'aplicativo autismo',
                'software educacional', 'dispositivo adaptado', 'tecnologia inclusiva',
                'recursos de acessibilidade', 'comunicação suplementar'
            ],
            'pesquisa_cientifica': [
                'estudo científico', 'pesquisa autismo', 'neurociência',
                'genética autismo', 'ensaios clínicos', 'artigo científico',
                'descoberta científica', 'pesquisa médica'
            ],
            'familia_cuidadores': [
                'relato de mãe', 'relato de pai', 'cuidadores', 'rede de apoio',
                'qualidade de vida familiar', 'desafios familiares', 'maternidade atípica',
                'paternidade atípica', 'grupo de apoio',
                # Termos adicionais para desafios familiares
                'pais', 'mães', 'responsáveis', 'família', 'familiares', 'irmãos',
                'desafio', 'dificuldade', 'obstáculo', 'barreira', 'problema',
                'sobrecarga', 'estresse', 'burnout', 'esgotamento', 'exaustão',
                'rotina', 'dia a dia', 'cotidiano', 'convivência', 'adaptação',
                'apoio psicológico', 'apoio emocional', 'acolhimento',
                'suporte familiar', 'orientação familiar', 'aconselhamento',
                'relação familiar', 'dinâmica familiar', 'ambiente familiar',
                'experiência familiar', 'vivência familiar', 'história familiar',
                'vida familiar', 'família atípica', 'família neurodiversa',
                'impacto familiar', 'impacto na família', 'impacto no cuidador',
                'bem-estar familiar', 'bem-estar do cuidador', 'qualidade de vida',
                'cuidado parental', 'criação', 'educação em casa', 'educação familiar',
                'socialização', 'interação social', 'relacionamento interpessoal'
            ],
            'mercado_trabalho': [
                'inclusão profissional', 'empregabilidade', 'treinamento profissional',
                'empresas inclusivas', 'leis trabalhistas', 'qualificação profissional',
                'mercado de trabalho', 'carreira', 'oportunidades de emprego'
            ],
            'cultura_lazer': [
                'evento inclusivo', 'atividades recreativas', 'esportes adaptados',
                'oficinas culturais', 'teatro acessível', 'cinema inclusivo',
                'atividades lúdicas', 'lazer adaptado'
            ],
            'pesquisa_estatistica': [
                'pesquisa', 'estudo', 'levantamento', 'dados', 'estatística', 'censo',
                'pesquisadores', 'cientistas', 'universidade', 'instituição de pesquisa',
                'IBGE', 'Instituto Brasileiro de Geografia e Estatística', 'dados oficiais',
                'relatório', 'análise estatística', 'pesquisa científica', 'estudo acadêmico',
                'publicação científica', 'artigo científico', 'revista científica', 'periódico científico',
                'metanálise', 'revisão sistemática', 'estudo longitudinal', 'pesquisa de campo',
                'coleta de dados', 'análise de dados', 'resultados de pesquisa', 'descoberta científica',
                'inovação em pesquisa', 'tecnologia assistiva', 'avanço científico', 'pesquisa clínica',
                'ensaio clínico', 'estudo multicêntrico', 'pesquisa translacional', 'pesquisa aplicada',
                'pesquisa básica', 'pesquisa qualitativa', 'pesquisa quantitativa', 'métodos de pesquisa',
                'metodologia científica', 'revisão por pares', 'fator de impacto', 'indexação em bases científicas',
                'banco de dados de pesquisa', 'repositório científico', 'acesso aberto', 'ciência aberta',
                'divulgação científica', 'popularização da ciência', 'jornalismo científico', 'comunicação científica',
                'ética em pesquisa', 'comitê de ética', 'comissão nacional de ética em pesquisa', 'conep',
                'plataforma brasil', 'sistema cnpq', 'currículo lattes', 'plataforma lattes', 'diretório dos grupos de pesquisa',
                'dgp cnpq', 'grupos de pesquisa', 'linhas de pesquisa', 'projetos de pesquisa', 'bolsas de pesquisa',
                'iniciação científica', 'mestrado', 'doutorado', 'pós-doutorado', 'produtividade em pesquisa',
                'pesquisador associado', 'pesquisador sênior', 'pesquisador visitante', 'colaboração internacional',
                'cooperação científica', 'acordos de cooperação', 'projetos conjuntos', 'redes de pesquisa',
                'associações científicas', 'sociedades científicas', 'congressos científicos', 'eventos científicos',
                'semanas acadêmicas', 'jornadas científicas', 'seminários', 'workshops', 'oficinas técnicas',
                'cursos de capacitação', 'treinamentos', 'palestras', 'mesas-redondas', 'debates', 'painéis',
                'apresentações orais', 'sessões de pôsteres', 'resumos expandidos', 'anais de eventos',
                'proceedings', 'livros científicos', 'capítulos de livros', 'coletâneas', 'edições especiais',
                'edições temáticas', 'edições comemorativas', 'edições especiais', 'edições temáticas',
                'edições comemorativas', 'edições especiais', 'edições temáticas', 'edições comemorativas'
            ]
        }
        
        # Termos obrigatórios para considerar um artigo relevante
        self.required_terms = [
            # Termos diretos sobre autismo
            'autis',  # Captura autismo, autista, autistas
            'TEA', 'transtorno do espectro autista',
            'neurodiversidade', 'neurodivergente',
            'síndrome de asperger',
            'transtorno invasivo do desenvolvimento',
            'TID', 'TGD',
            'condição do espectro autista',
            'transtorno global do desenvolvimento',
            
            # Termos relacionados a deficiência
            'criança especial', 'pessoa com deficiência', 'PCD',
            'necessidades especiais', 'deficiência intelectual',
            'transtorno do desenvolvimento', 'condição neurológica',
            'condição do neurodesenvolvimento', 'transtorno neurológico',
            'pessoa com deficiência', 'pessoa com necessidades especiais',
            'criança com deficiência', 'adolescente com deficiência',
            'pessoa com transtorno', 'criança com transtorno',
            
            # Termos para capturar processos judiciais e responsabilização
            'aluno com deficiência', 'aluno especial', 'aluno autista',
            'criança autista', 'adolescente autista', 'pessoa autista',
            'estudante autista', 'estudante com deficiência',
            'aluno com necessidades especiais', 'criança especial',
            'criança com necessidades especiais', 'adolescente com necessidades especiais',
            'pessoa com necessidades especiais', 'pessoa com TEA', 'pessoa com autismo',
            'criança com TEA', 'adolescente com TEA', 'estudante com TEA', 'aluno com TEA',
            
            # Termos adicionais para responsabilização institucional
            'processo judicial', 'ação judicial', 'processo na justiça',
            'ação na justiça', 'ação na vara da infância', 'ação no MPE',
            'Ministério Público Estadual', 'Ministério Público Federal',
            'promotoria de justiça', 'promotor de justiça', 'promotora de justiça',
            'defensoria pública', 'defensor público', 'defensora pública',
            'vara da infância', 'vara da criança e do adolescente', 'juizado especial',
            'ação civil pública', 'ação de responsabilidade', 'ação indenizatória',
            'ação por danos morais', 'danos morais', 'danos materiais', 'danos estéticos',
            'indenização por danos', 'indenização por dano moral', 'indenização por dano material',
            'responsabilidade civil', 'responsabilidade objetiva', 'responsabilidade subjetiva',
            'obrigação de indenizar', 'dever de indenizar', 'dever de reparar',
            'reparação de danos', 'reparação civil', 'reparação por danos',
            'responsabilidade da escola', 'responsabilidade do colégio',
            'responsabilidade da instituição de ensino', 'responsabilidade do estabelecimento de ensino',
            'dever de cuidado', 'dever de vigilância', 'dever de proteção',
            'omissão da escola', 'omissão do colégio', 'falha na fiscalização',
            'falha na supervisão', 'falha no acompanhamento', 'falha na segurança',
            'notificação extrajudicial', 'notificação à escola', 'notificação ao colégio',
            'notificação à direção', 'notificação à secretaria', 'notificação ao conselho',
            'denúncia contra escola', 'denúncia ao conselho tutelar', 'denúncia ao MP',
            'representação ao MP', 'representação ao Ministério Público', 'queixa-crime',
            'boletim de ocorrência', 'B.O.', 'registro de ocorrência', 'termo circunstanciado',
            'delegacia de proteção à criança e ao adolescente', 'delegacia da criança e do adolescente',
            'conselho tutelar', 'conselho municipal dos direitos da criança e do adolescente',
            'conselho estadual dos direitos da criança e do adolescente', 'CMDCA', 'CEDCA',
            'vítima de violência', 'vítima de agressão', 'vítima de maus-tratos',
            'vítima de bullying', 'vítima de assédio', 'vítima de discriminação',
            'vítima de preconceito', 'vítima de negligência', 'vítima de omissão',
            'vítima de abandono intelectual', 'vítima de abuso', 'vítima de violação de direitos'
        ]
        
        # Palavras-chave para identificar notícias irrelevantes
        self.irrelevant_keywords = [
            # Entretenimento e lazer
            'futebol', 'esporte', 'jogo', 'partida', 'campeonato', 'time', 'seleção',
            'celebridade', 'famoso', 'famosos', 'famosas', 'ator', 'atriz', 'cantor', 'cantora',
            'entretenimento', 'novela', 'série', 'filme', 'cinema', 'música', 'show', 'festival',
            'bbb', 'big brother', 'reality show', 'programa de auditório', 'lazer', 'viagem',
            'turismo', 'passeio', 'passeios', 'feriado', 'férias', 'hotel', 'resort',
            'culinária', 'receita', 'comida', 'gastronomia', 'restaurante', 'chef', 'cozinha',
            'moda', 'beleza', 'maquiagem', 'cabelo', 'estética', 'cosmético', 'perfume',
            'automobilismo', 'corrida', 'fórmula 1', 'f1', 'moto', 'carro', 'automóvel',
            'política partidária', 'eleições', 'candidato', 'candidata', 'partido', 'governo',
            'religião', 'igreja', 'templo', 'culto', 'missa', 'bispo', 'pastor', 'padre',
            'fofoca', 'celebridades', 'famosinhos', 'celebridade internacional', 'hollywood'
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
        
        # Verifica se é uma notícia de pesquisa/estatística sobre autismo
        is_research = any(term in text_lower for term in self.categories['pesquisa_estatistica'])
        is_about_autism = any(term in text_lower for term in ['autis', 'TEA', 'transtorno do espectro autista'])
        
        # É relevante se:
        # 1. Tem termos obrigatórios E não tem termos irrelevantes, OU
        # 2. É uma notícia de pesquisa/estatística sobre autismo
        return (has_required and not has_irrelevant) or (is_research and is_about_autism)
    
    async def _preprocess_topic_facts(self, db, topic_id: str, topic_name: str) -> None:
        """Pré-processa fatos para um tópico específico.
        
        Args:
            db: Conexão com banco de dados
            topic_id: ID do tópico
            topic_name: Nome do tópico
        """
        try:
            logger.info(f"🧠 Pré-processando fatos para tópico: {topic_name}")
            
            # Extrair fatos do tópico
            facts = await fact_extraction_system.extract_facts_from_topic(db, topic_id)
            facts_summary = fact_extraction_system.get_facts_summary(facts)
            
            # Salvar fatos no tópico
            await db.topics.update_one(
                {'_id': ObjectId(topic_id)},
                {
                    '$set': {
                        'extracted_facts': facts[:20],  # Top 20 fatos mais relevantes
                        'facts_summary': facts_summary,
                        'facts_processed': True,
                        'facts_processed_at': datetime.utcnow(),
                        'total_facts_available': len(facts)
                    }
                }
            )
            
            logger.info(f"✅ {topic_name}: {len(facts)} fatos extraídos, {len(facts[:20])} salvos")
            
        except Exception as e:
            logger.error(f"❌ Erro ao pré-processar fatos para {topic_name}: {str(e)}")
            # Não falha o clustering se a extração de fatos der erro

    def _categorize_article(self, article: Dict[str, Any]) -> str:
        """Categorize an article into one of the predefined categories.
        
        Args:
            article: Dictionary containing article data with at least 'title', 'description', and 'content'.
            
        Returns:
            str: The category name or 'irrelevante' if the article doesn't match any category.
        """
        # Combine all text fields for analysis
        text = ' '.join([
            article.get('title', ''),
            article.get('description', ''),
            article.get('content', '')
        ]).lower()
        
        # First check if the article is relevant
        if not self.is_relevant(text):
            return 'irrelevante'
            
        # Get title and description for special cases
        title = article.get('title', '').lower()
        description = article.get('description', '').lower()
        title_desc = f"{title} {description}"
        
        # Check for multi-word phrases that indicate specific categories
        # This helps with context that might be missed by single-word matching
        health_phrases = [
            'novo medicamento', 'nova medicação', 'novo tratamento', 'nova terapia',
            'aprovação de medicamento', 'aprovação de tratamento', 'liberação de medicamento',
            'estudo de medicamento', 'pesquisa de medicamento', 'ensaio clínico',
            'benefícios do tratamento', 'efeitos do tratamento', 'eficácia do tratamento'
        ]
        
        family_phrases = [
            'desafios dos pais', 'desafios das mães', 'desafios das famílias',
            'dificuldades dos cuidadores', 'sobrecarga dos cuidadores', 'estresse dos pais',
            'experiência parental', 'experiência familiar', 'rotina familiar',
            'impacto na família', 'impacto nos pais', 'impacto no dia a dia'
        ]
        
        discrimination_phrases = [
            'tratamento diferenciado', 'olhares diferentes', 'comentários inapropriados',
            'falta de compreensão', 'falta de empatia', 'falta de inclusão',
            'barreira atitudinal', 'barreira social', 'não aceitação',
            'exclusão social', 'isolamento social', 'segregação social'
        ]
        
        # Check for multi-word phrase matches first
        # Health treatment phrases
        health_phrase_score = sum(15 for phrase in health_phrases if phrase in text)
        if health_phrase_score >= 15:
            return 'saude_tratamento'
            
        # Family challenges phrases
        family_phrase_score = sum(15 for phrase in family_phrases if phrase in text)
        if family_phrase_score >= 15:
            return 'familia_cuidadores'
            
        # Discrimination phrases
        discrimination_phrase_score = sum(15 for phrase in discrimination_phrases if phrase in text)
        if discrimination_phrase_score >= 15:
            return 'violencia_discriminacao'
        
        # Special case 1: Check for violence/discrimination first (highest priority)
        violence_terms = self.categories['violencia_discriminacao']
        violence_score = sum(10 for term in violence_terms if term in title_desc)  # Higher weight for title/desc
        violence_score += sum(1 for term in violence_terms if term in text)  # Lower weight for full text
        
        if violence_score >= 3:  # Threshold for violence/discrimination
            return 'violencia_discriminacao'
            
        # Special case 2: Check for legislation/rights (high priority)
        rights_terms = self.categories['direitos_legislacao']
        rights_score = sum(5 for term in rights_terms if term in title_desc)
        rights_score += sum(1 for term in rights_terms if term in text)
        
        # Special case 3: Check for research/statistics (medium priority)
        research_terms = self.categories['pesquisa_estatistica']
        research_score = sum(3 for term in research_terms if term in title_desc)
        research_score += sum(1 for term in research_terms if term in text)
        
        # Only classify as research if it's specifically about autism research
        is_about_autism = any(term in text for term in ['autis', 'TEA', 'transtorno do espectro autista'])
        
        # If it's about rights/legislation and not just a general research article
        if rights_score >= 5 and 'direito' in text:
            return 'direitos_legislacao'
            
        # If it's specifically about autism research
        if research_score >= 3 and is_about_autism and 'pesquisa' in text:
            return 'pesquisa_estatistica'
            
        # Special case for health/treatment (medication, therapy, etc.)
        health_terms = self.categories['saude_tratamento']
        health_score = sum(5 for term in health_terms if term in title_desc)
        health_score += sum(1 for term in health_terms if term in text)
        
        if health_score >= 5 and any(term in text for term in ['medicamento', 'medicação', 'remédio', 'terapia', 'tratamento']):
            return 'saude_tratamento'
            
        # Special case for family/caregivers
        family_terms = self.categories['familia_cuidadores']
        family_score = sum(5 for term in family_terms if term in title_desc)
        family_score += sum(1 for term in family_terms if term in text)
        
        if family_score >= 5 and any(term in text for term in ['família', 'pais', 'mães', 'cuidadores', 'desafio']):
            return 'familia_cuidadores'
        
        # Calculate scores for all categories with weights
        category_scores = {}
        
        for category, keywords in self.categories.items():
            # Skip categories we already checked
            if category in ['violencia_discriminacao', 'direitos_legislacao', 'pesquisa_estatistica']:
                continue
                
            # Initialize score for this category
            score = 0
            
            # Higher weight for title matches (3x)
            if 'title' in article:
                title = article['title'].lower()
                score += sum(3 for keyword in keywords if keyword in title)
                
            # Medium weight for description matches (2x)
            if 'description' in article:
                desc = article['description'].lower()
                score += sum(2 for keyword in keywords if keyword in desc)
                
            # Lower weight for content matches (1x)
            if 'content' in article:
                content = article['content'].lower()
                score += sum(1 for keyword in keywords if keyword in content)
            
            # Only add to scores if we found matches
            if score > 0:
                category_scores[category] = score
        
        # If we have category matches, return the highest scoring one
        if category_scores:
            best_category = max(category_scores.items(), key=lambda x: x[1])[0]
            # Only return if score is above threshold
            if category_scores[best_category] >= 3:  # Minimum threshold
                return best_category
        
        # Special case: Check for autism-related research that might have been missed
        research_terms = ['pesquisa', 'estudo', 'levantamento', 'dados', 'estatística', 'censo']
        if any(term in text for term in research_terms) and \
           any(term in text for term in ['autis', 'TEA', 'transtorno do espectro autista']):
            return 'pesquisa_estatistica'
            
        # Special case: Check for rights/legislation that might have been missed
        rights_terms = ['direito', 'lei', 'legislação', 'projeto de lei', 'PL', 'proposta']
        if any(term in text for term in rights_terms) and \
           any(term in text for term in ['autis', 'TEA', 'transtorno do espectro autista']):
            return 'direitos_legislacao'
        
        # If we get here, no category matched well enough
        return 'outros'

    async def cluster_recent_news(self, country: str = 'BR', force_update: bool = False) -> Dict[str, Any]:
        """Cluster recent news articles into topics and extract facts.
        
        Args:
            country: Country code to filter news by
            force_update: Whether to force reclustering even if recent clustering was performed
            
        Returns:
            Dictionary with clustering results and statistics
        """
        try:
            start_time = datetime.utcnow()
            logger.info(f"🚀 Iniciando clustering de notícias para {country}")
            
            # Conectar ao banco de dados
            db_manager = MongoDBManager()
            await db_manager.connect_to_mongodb()
            
            async with db_manager.get_db() as db:
                # Check if recent clustering was performed (unless forced)
                if not force_update:
                    recent_clustering = await db.clustering_logs.find_one(
                        {
                            'country': country,
                            'status': 'completed',
                            'completed_at': {'$gte': datetime.utcnow() - timedelta(hours=6)}
                        },
                        sort=[('completed_at', -1)]
                    )
                    
                    if recent_clustering:
                        logger.info(f"⏭️ Clustering recente encontrado para {country}, pulando...")
                        return {
                            'status': 'skipped',
                            'reason': 'recent_clustering_exists',
                            'last_clustering': recent_clustering['completed_at']
                        }
                
                # Log do início do clustering
                log_id = await self._log_clustering_start(db, country)
                
                try:
                    # 1. Buscar artigos não categorizados
                    uncategorized_articles = await self._get_uncategorized_articles(db, country)
                    logger.info(f"📊 Encontrados {len(uncategorized_articles)} artigos não categorizados")
                    
                    if not uncategorized_articles:
                        logger.info("ℹ️ Nenhum artigo novo para clustering")
                        await self._log_clustering_completion(db, log_id, 0, 0)
                        return {
                            'status': 'completed',
                            'topics_created': 0,
                            'articles_processed': 0,
                            'message': 'No new articles to cluster'
                        }
                    
                    # 2. Categorizar artigos
                    categorized_articles = {}
                    for article in uncategorized_articles:
                        category = self._categorize_article(article)
                        if category not in categorized_articles:
                            categorized_articles[category] = []
                        categorized_articles[category].append(article)
                    
                    logger.info(f"📁 Artigos categorizados em {len(categorized_articles)} categorias")
                    
                    # 3. Fazer clustering por categoria
                    total_topics_created = 0
                    total_articles_processed = 0
                    
                    for category, articles in categorized_articles.items():
                        if category == 'irrelevante':
                            # Marcar como processados mas não criar tópicos
                            await self._mark_articles_as_processed(db, articles, 'irrelevante')
                            total_articles_processed += len(articles)
                            continue
                        
                        logger.info(f"🔍 Clustering categoria '{category}' ({len(articles)} artigos)")
                        
                        # Clustering dentro da categoria
                        topics_created = await self._cluster_by_category(db, articles, category, country)
                        total_topics_created += topics_created
                        total_articles_processed += len(articles)
                        
                        logger.info(f"✅ Categoria '{category}': {topics_created} tópicos criados")
                    
                    # 4. NOVA SEÇÃO: Pós-processamento de fatos para todos os tópicos
                    await self._postprocess_all_topics_facts(db, country)
                    
                    # 5. Log de conclusão
                    await self._log_clustering_completion(db, log_id, total_topics_created, total_articles_processed)
                    
                    end_time = datetime.utcnow()
                    duration = (end_time - start_time).total_seconds()
                    
                    logger.info(f"🎉 Clustering concluído: {total_topics_created} tópicos, {total_articles_processed} artigos em {duration:.2f}s")
                    
                    return {
                        'status': 'completed',
                        'topics_created': total_topics_created,
                        'articles_processed': total_articles_processed,
                        'categories_processed': list(categorized_articles.keys()),
                        'duration_seconds': duration,
                        'facts_extracted': True  # Novo campo
                    }
                    
                except Exception as e:
                    # Log de erro
                    await self._log_clustering_error(db, log_id, str(e))
                    raise
                    
        except Exception as e:
            logger.error(f"❌ Erro no clustering: {str(e)}", exc_info=True)
            raise


    async def _cluster_by_category(self, db, articles: List[Dict], category: str, country: str) -> int:
        """Cluster articles within a specific category and extract facts.
        
        Args:
            db: Database connection
            articles: List of articles to cluster
            category: Category name
            country: Country code
            
        Returns:
            Number of topics created
        """
        if len(articles) < 2:
            # Para artigos únicos, criar tópico individual
            if articles:
                topic_id = await self._create_single_article_topic(db, articles[0], category, country)
                # INTEGRAÇÃO: Extrair fatos do tópico único
                if topic_id:
                    await self._preprocess_topic_facts(db, str(topic_id), f"Tópico individual - {category}")
                return 1
            return 0
        
        try:
            # Extrair embeddings
            embeddings = []
            valid_articles = []
            
            for article in articles:
                embedding = article.get('embedding')
                if embedding and len(embedding) > 0:
                    embeddings.append(embedding)
                    valid_articles.append(article)
            
            if len(valid_articles) < 2:
                logger.warning(f"Não há embeddings suficientes para clustering na categoria {category}")
                return 0
            
            # Aplicar DBSCAN clustering
            embeddings_array = np.array(embeddings)
            
            # Parâmetros ajustados para melhor clustering
            eps = 0.3 if len(valid_articles) > 10 else 0.4
            min_samples = max(2, min(3, len(valid_articles) // 4))
            
            clustering = DBSCAN(eps=eps, min_samples=min_samples, metric='cosine')
            cluster_labels = clustering.fit_predict(embeddings_array)
            
            # Agrupar artigos por cluster
            clusters = {}
            noise_articles = []
            
            for idx, label in enumerate(cluster_labels):
                if label == -1:  # Ruído
                    noise_articles.append(valid_articles[idx])
                else:
                    if label not in clusters:
                        clusters[label] = []
                    clusters[label].append(valid_articles[idx])
            
            # Criar tópicos para cada cluster
            topics_created = 0
            
            for cluster_id, cluster_articles in clusters.items():
                if len(cluster_articles) >= 2:  # Mínimo 2 artigos por tópico
                    topic_id = await self._create_topic_from_cluster(db, cluster_articles, category, country)
                    if topic_id:
                        # INTEGRAÇÃO: Extrair fatos do tópico
                        topic_title = await self._get_topic_title(db, topic_id)
                        await self._preprocess_topic_facts(db, str(topic_id), topic_title)
                        topics_created += 1
                else:
                    noise_articles.extend(cluster_articles)
            
            # Processar artigos de ruído como tópicos individuais
            for article in noise_articles:
                topic_id = await self._create_single_article_topic(db, article, category, country)
                if topic_id:
                    # INTEGRAÇÃO: Extrair fatos do tópico individual
                    await self._preprocess_topic_facts(db, str(topic_id), f"Tópico individual - {category}")
                    topics_created += 1
            
            return topics_created
            
        except Exception as e:
            logger.error(f"Erro no clustering da categoria {category}: {str(e)}", exc_info=True)
            return 0


    async def _postprocess_all_topics_facts(self, db, country: str) -> None:
        """Pós-processa fatos para todos os tópicos que ainda não foram processados.
        
        Args:
            db: Database connection
            country: Country code
        """
        try:
            logger.info(f"🧠 Iniciando pós-processamento de fatos para tópicos do país {country}")
            
            # Buscar tópicos que não tiveram fatos processados
            unprocessed_topics = await db.topics.find({
                'country_focus': country,
                'is_active': True,
                '$or': [
                    {'facts_processed': {'$exists': False}},
                    {'facts_processed': False},
                    {'facts_processed_at': {'$lt': datetime.utcnow() - timedelta(days=1)}}  # Reprocessar diariamente
                ]
            }).to_list(length=None)
            
            logger.info(f"🔍 Encontrados {len(unprocessed_topics)} tópicos para processamento de fatos")
            
            facts_processed_count = 0
            facts_failed_count = 0
            
            for topic in unprocessed_topics:
                topic_id = str(topic['_id'])
                topic_name = topic.get('title', 'Tópico sem nome')
                
                try:
                    await self._preprocess_topic_facts(db, topic_id, topic_name)
                    facts_processed_count += 1
                except Exception as e:
                    logger.error(f"❌ Erro ao processar fatos do tópico {topic_name}: {str(e)}")
                    facts_failed_count += 1
            
            logger.info(f"✅ Pós-processamento concluído: {facts_processed_count} sucessos, {facts_failed_count} falhas")
            
        except Exception as e:
            logger.error(f"❌ Erro no pós-processamento de fatos: {str(e)}", exc_info=True)


    async def _get_topic_title(self, db, topic_id: ObjectId) -> str:
        """Busca o título de um tópico pelo ID.
        
        Args:
            db: Database connection
            topic_id: ObjectId do tópico
            
        Returns:
            Título do tópico ou string padrão
        """
        try:
            topic = await db.topics.find_one({'_id': topic_id}, {'title': 1})
            return topic.get('title', 'Tópico sem nome') if topic else 'Tópico não encontrado'
        except Exception:
            return 'Tópico desconhecido'


    async def _create_topic_from_cluster(self, db, articles: List[Dict], category: str, country: str) -> Optional[ObjectId]:
        """Cria um tópico a partir de um cluster de artigos.
        
        Args:
            db: Database connection
            articles: Lista de artigos do cluster
            category: Categoria do tópico
            country: Código do país
            
        Returns:
            ObjectId do tópico criado ou None se falhou
        """
        try:
            # Gerar título e descrição usando IA
            title, description = await self._generate_topic_metadata(articles)
            
            # Calcular embedding médio
            embeddings = [article['embedding'] for article in articles if article.get('embedding')]
            avg_embedding = np.mean(embeddings, axis=0).tolist() if embeddings else []
            
            # Preparar dados do tópico
            topic_data = {
                'title': title,
                'description': description,
                'category': category,
                'country_focus': country,
                'articles': [str(article['_id']) for article in articles],
                'article_count': len(articles),
                'sources': list(set(article.get('domain', '') for article in articles if article.get('domain'))),
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
                'is_active': True,
                'embedding': avg_embedding,
                # Campos para fatos (serão preenchidos depois)
                'facts_processed': False,
                'extracted_facts': [],
                'facts_summary': {},
                'total_facts_available': 0
            }
            
            # Inserir no banco
            result = await db.topics.insert_one(topic_data)
            
            # Marcar artigos como processados
            article_ids = [article['_id'] for article in articles]
            await db.news.update_many(
                {'_id': {'$in': article_ids}},
                {
                    '$set': {
                        'clustered': True,
                        'topic_id': str(result.inserted_id),
                        'updated_at': datetime.utcnow()
                    }
                }
            )
            
            logger.debug(f"✅ Tópico criado: {title} (ID: {result.inserted_id})")
            return result.inserted_id
            
        except Exception as e:
            logger.error(f"❌ Erro ao criar tópico: {str(e)}", exc_info=True)
            return None


    # O método _preprocess_topic_facts já existe e está correto!
    # Basta garantir que ele seja chamado nos momentos certos acima.

    # Também adicione este método de utilidade:

    async def _mark_articles_as_processed(self, db, articles: List[Dict], reason: str) -> None:
        """Marca artigos como processados sem criar tópicos.
        
        Args:
            db: Database connection
            articles: Lista de artigos para marcar
            reason: Motivo do processamento (ex: 'irrelevante')
        """
        try:
            article_ids = [article['_id'] for article in articles]
            await db.news.update_many(
                {'_id': {'$in': article_ids}},
                {
                    '$set': {
                        'clustered': True,
                        'cluster_reason': reason,
                        'updated_at': datetime.utcnow()
                    }
                }
            )
            logger.debug(f"✅ {len(articles)} artigos marcados como processados ({reason})")
        except Exception as e:
            logger.error(f"❌ Erro ao marcar artigos como processados: {str(e)}", exc_info=True)

    async def _log_clustering_start(self, db, country: str) -> str:
        """Log início do clustering."""
        try:
            log_doc = {
                'country': country,
                'status': 'started',
                'started_at': datetime.utcnow(),
                'process_id': f"clustering_{country}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            }
            result = await db.clustering_logs.insert_one(log_doc)
            logger.info(f"📝 Log de clustering iniciado: {result.inserted_id}")
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"❌ Erro ao criar log de clustering: {str(e)}")
            return None

    async def _log_clustering_completion(self, db, log_id: str, topics_created: int, articles_processed: int) -> None:
        """Log conclusão do clustering."""
        try:
            if log_id and ObjectId.is_valid(log_id):
                await db.clustering_logs.update_one(
                    {'_id': ObjectId(log_id)},
                    {
                        '$set': {
                            'status': 'completed',
                            'completed_at': datetime.utcnow(),
                            'topics_created': topics_created,
                            'articles_processed': articles_processed,
                            'duration_seconds': None  # Será calculado se necessário
                        }
                    }
                )
                logger.info(f"📝 Log de clustering atualizado: {log_id}")
        except Exception as e:
            logger.error(f"❌ Erro ao atualizar log de clustering: {str(e)}")

    async def _log_clustering_error(self, db, log_id: str, error: str) -> None:
        """Log erro do clustering."""
        try:
            if log_id and ObjectId.is_valid(log_id):
                await db.clustering_logs.update_one(
                    {'_id': ObjectId(log_id)},
                    {
                        '$set': {
                            'status': 'error',
                            'error_at': datetime.utcnow(),
                            'error_message': error[:1000],  # Limitar tamanho do erro
                            'completed_at': datetime.utcnow()
                        }
                    }
                )
                logger.error(f"📝 Log de erro registrado: {log_id}")
        except Exception as e:
            logger.error(f"❌ Erro ao registrar erro no log: {str(e)}")

    async def _get_uncategorized_articles(self, db, country: str) -> List[Dict]:
        """Busca artigos que ainda não foram categorizados."""
        try:
            # Buscar artigos não clusterizados do país
            articles = await db.news.find({
                'country_focus': country.upper(),
                '$or': [
                    {'clustered': {'$exists': False}},
                    {'clustered': False}
                ]
            }).to_list(length=None)
            
            logger.info(f"🔍 Encontrados {len(articles)} artigos não categorizados para {country}")
            return articles
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar artigos não categorizados: {str(e)}")
            return []

    async def _create_single_article_topic(self, db, article: Dict, category: str, country: str) -> Optional[ObjectId]:
        """Cria um tópico para um artigo único."""
        try:
            title = article.get('title', 'Tópico sem título')
            description = f"Tópico criado a partir do artigo: {title[:100]}..."
            
            topic_data = {
                'title': title,
                'description': description,
                'category': category,
                'country_focus': country,
                'articles': [str(article['_id'])],
                'article_count': 1,
                'sources': [article.get('source_domain', '')],
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
                'is_active': True,
                'embedding': article.get('embedding', []),
                # Campos para fatos
                'facts_processed': False,
                'extracted_facts': [],
                'facts_summary': {},
                'total_facts_available': 0
            }
            
            result = await db.topics.insert_one(topic_data)
            
            # Marcar artigo como processado
            await db.news.update_one(
                {'_id': article['_id']},
                {
                    '$set': {
                        'clustered': True,
                        'topic_id': str(result.inserted_id),
                        'updated_at': datetime.utcnow()
                    }
                }
            )
            
            logger.debug(f"✅ Tópico individual criado: {title[:50]}...")
            return result.inserted_id
            
        except Exception as e:
            logger.error(f"❌ Erro ao criar tópico individual: {str(e)}")
            return None

    async def _generate_topic_metadata(self, articles: List[Dict]) -> Tuple[str, str]:
        """Gera título e descrição para um tópico baseado nos artigos."""
        try:
            # Extrair títulos dos artigos
            titles = [article.get('title', '') for article in articles if article.get('title')]
            
            if not titles:
                return "Tópico sem título", "Tópico agrupado automaticamente"
            
            # Usar o título mais comum ou o primeiro se não houver padrão
            if len(titles) == 1:
                title = titles[0]
            else:
                # Encontrar palavras comuns nos títulos
                words = []
                for title in titles:
                    words.extend(title.lower().split())
                
                common_words = [word for word, count in Counter(words).most_common(3) 
                            if len(word) > 3 and word not in ['para', 'sobre', 'como', 'mais']]
                
                if common_words:
                    title = f"Notícias sobre {' '.join(common_words[:2])}"
                else:
                    title = titles[0]  # Fallback para o primeiro título
            
            # Limitar tamanho do título
            title = title[:100] if len(title) > 100 else title
            
            # Gerar descrição
            description = f"Tópico agrupando {len(articles)} artigos relacionados"
            
            return title, description
            
        except Exception as e:
            logger.error(f"❌ Erro ao gerar metadados do tópico: {str(e)}")
            return "Tópico agrupado", f"Tópico com {len(articles)} artigos"
# Create a singleton instance
topic_cluster = TopicCluster()
