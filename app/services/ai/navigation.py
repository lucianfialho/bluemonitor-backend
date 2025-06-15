"""Sistema de navegação recursiva entre tópicos."""

import re
import logging
from typing import List, Dict, Any, Set, Tuple
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)

class TopicNavigationSystem:
    """Sistema para navegação recursiva entre tópicos."""
    
    def __init__(self):
        """Initialize the navigation system."""
        # Mapeamento de termos para tópicos (baseado no seu código atual)
        self.topic_keywords_map = {
            'Diagnóstico e Detecção Precoce': [
                'diagnóstico', 'detecção precoce', 'precoce', 'detectar',
                'identificar', 'sinais', 'sintomas', 'cedo', 'infância',
                'diagnóstico precoce', 'identificação precoce'
            ],
            'Desinformação e Fake News sobre Autismo': [
                'desinformação', 'fake news', 'fake', 'mito', 'mentira',
                'boato', 'falsa informação', 'desinformar', 'fake news',
                'informação falsa', 'notícia falsa'
            ],
            'Violência e Discriminação': [
                'agressão', 'violência', 'agredido', 'discriminação', 'bullying',
                'preconceito', 'maltrato', 'abuso', 'violento', 'agressor',
                'discriminar', 'maltratar'
            ],
            'Censo 2022: Estatísticas Oficiais': [
                'censo', '2,4 milhões', 'dados inéditos', 'estatística',
                'ibge', 'oficial', 'brasileiros', 'censo 2022',
                'dados oficiais', 'levantamento oficial'
            ],
            'Capacitação e Formação Profissional': [
                'capacitação', 'treinamento', 'curso', 'formação',
                'profissional', 'atendimento', 'qualificação', 'capacitar',
                'treinar', 'formar profissionais'
            ],
            'Crescimento na Educação': [
                'cresce', 'crescimento', 'aumenta', 'estudantes', '44,4%',
                'educação', 'escola', 'matrícula', 'número de estudantes',
                'crescimento educacional', 'aumento de matrículas'
            ],
            'Símbolos e Representação': [
                'símbolos', 'girassol', 'quebra-cabeça', 'infinito',
                'representação', 'conscientização', 'símbolo do autismo',
                'cordão de girassol', 'peça de quebra-cabeça'
            ]
        }
        
        # Termos gerais do autismo que sempre devem ser linkados
        self.autism_general_terms = [
            'TEA', 'autismo', 'autista', 'transtorno do espectro autista',
            'asperger', 'neurodiversidade', 'neurodivergente',
            'espectro autista', 'pessoa autista', 'criança autista'
        ]
        
        # Tratamentos e terapias
        self.treatment_terms = [
            'terapia ABA', 'fonoaudiologia', 'terapia ocupacional',
            'psicólogo infantil', 'neuropediatra', 'intervenção precoce',
            'ABA', 'TEACCH', 'PECS', 'integração sensorial'
        ]
        
        # Legislação e direitos
        self.legislation_terms = [
            'Lei Berenice Piana', 'estatuto da pessoa com deficiência',
            'LOAS', 'benefício assistencial', 'direitos autistas',
            'lei 12.764', 'política nacional', 'direitos da pessoa com deficiência'
        ]

    def extract_linkable_terms(self, text: str, current_topic: str = None) -> List[Dict[str, Any]]:
        """Extrai termos do texto que podem ser linkados para outros tópicos."""
        linkable_terms = []
        text_lower = text.lower()
        
        # Buscar por todos os tópicos disponíveis
        for topic_name, keywords in self.topic_keywords_map.items():
            if topic_name == current_topic:
                continue
                
            for keyword in keywords:
                pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
                matches = re.finditer(pattern, text_lower)
                
                for match in matches:
                    linkable_terms.append({
                        'term': keyword,
                        'start_pos': match.start(),
                        'end_pos': match.end(),
                        'target_topic': topic_name,
                        'topic_category': self._get_topic_category(topic_name),
                        'original_text': text[match.start():match.end()],
                        'priority': 2
                    })
        
        # Adicionar termos gerais
        for term in self.autism_general_terms:
            pattern = r'\b' + re.escape(term.lower()) + r'\b'
            matches = re.finditer(pattern, text_lower)
            
            for match in matches:
                linkable_terms.append({
                    'term': term,
                    'start_pos': match.start(),
                    'end_pos': match.end(),
                    'target_topic': 'Informações Gerais sobre Autismo',
                    'topic_category': 'Pesquisa e Ciência',
                    'original_text': text[match.start():match.end()],
                    'priority': 1
                })
        
        # Remover sobreposições e ordenar
        linkable_terms = self._remove_overlapping_terms(linkable_terms)
        return sorted(linkable_terms, key=lambda x: x['start_pos'])

    def _remove_overlapping_terms(self, terms: List[Dict]) -> List[Dict]:
        """Remove termos sobrepostos, mantendo o de maior prioridade."""
        if not terms:
            return terms
            
        terms_sorted = sorted(terms, key=lambda x: (x['start_pos'], -x['priority'], -len(x['term'])))
        
        non_overlapping = []
        last_end = -1
        
        for term in terms_sorted:
            if term['start_pos'] >= last_end:
                non_overlapping.append(term)
                last_end = term['end_pos']
            else:
                if term['priority'] > non_overlapping[-1]['priority']:
                    non_overlapping[-1] = term
                    last_end = term['end_pos']
        
        return non_overlapping

    def _get_topic_category(self, topic_name: str) -> str:
        """Mapeia nome do tópico para categoria."""
        category_mapping = {
            'Diagnóstico e Detecção Precoce': 'Saúde e Tratamento',
            'Desinformação e Fake News sobre Autismo': 'Pesquisa e Ciência',
            'Violência e Discriminação': 'Direitos e Proteção',
            'Censo 2022: Estatísticas Oficiais': 'Pesquisa e Ciência',
            'Capacitação e Formação Profissional': 'Educação e Capacitação',
            'Crescimento na Educação': 'Educação e Inclusão',
            'Símbolos e Representação': 'Direitos e Legislação',
            'Informações Gerais sobre Autismo': 'Pesquisa e Ciência',
            'Tratamentos e Terapias': 'Saúde e Tratamento',
            'Direitos e Legislação': 'Direitos e Legislação'
        }
        return category_mapping.get(topic_name, 'Outros')

    def generate_navigation_html(self, text: str, current_topic: str = None) -> str:
        """Gera HTML com links para navegação recursiva."""
        linkable_terms = self.extract_linkable_terms(text, current_topic)
        
        if not linkable_terms:
            return text
        
        html_parts = []
        last_pos = 0
        
        for term in linkable_terms:
            html_parts.append(text[last_pos:term['start_pos']])
            
            link_html = f'''<a href="/topicos/{term['target_topic']}" 
                           class="topic-link topic-link--{term['topic_category'].lower().replace(' ', '-')}" 
                           data-category="{term['topic_category']}"
                           data-priority="{term['priority']}"
                           title="Ver tópico: {term['target_topic']} ({term['topic_category']})">
                           {term['original_text']}</a>'''
            html_parts.append(link_html)
            
            last_pos = term['end_pos']
        
        html_parts.append(text[last_pos:])
        return ''.join(html_parts)

# Instância global
navigation_system = TopicNavigationSystem()