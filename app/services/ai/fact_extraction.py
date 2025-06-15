"""Sistema de extração de fatos de notícias por tópico."""

import re
import logging
from typing import List, Dict, Any, Set, Tuple
from datetime import datetime
from collections import defaultdict, Counter
from bson import ObjectId

logger = logging.getLogger(__name__)

class FactExtractionSystem:
    """Sistema para extração de fatos de notícias por tópico."""
    
    def __init__(self):
        """Initialize the fact extraction system."""
        # Padrões para identificar fatos/estatísticas
        self.fact_patterns = [
            r'\d+[%％][\s\w]*(?:dos|das|de|em|entre)[\s\w]*(?:casos|pessoas|crianças|autistas)',
            r'(?:apenas|somente|cerca de|aproximadamente)?\s*\d+[%％]',
            r'\d+(?:\.\d+)?\s*(?:milhões?|mil|bilhões?)\s*de\s*(?:pessoas|crianças|brasileiros)',
            r'(?:antes dos?|após os?|até os?)\s*\d+\s*anos?',
            r'em\s*\d{4}(?:,\s*\d+[%％])?',
            r'(?:desde|a partir de)\s*\d{4}',
            r'(?:cresceu|aumentou|subiu|diminuiu|reduziu)\s*(?:em\s*)?\d+[%％]',
            r'(?:mais|menos)\s*(?:de\s*)?\d+[%％]',
            r'Lei\s+(?:Federal\s+)?n?º?\s*\d+(?:\/\d+)?',
            r'(?:estudo|pesquisa|levantamento)[\s\w]*(?:revela|mostra|indica|aponta)',
            r'(?:segundo|conforme|de acordo com)\s+(?:a\s+)?(?:pesquisa|estudo)',
            r'(?:dados|estatísticas)\s+(?:mostram|revelam|indicam)',
        ]
        
        self.sentence_fact_indicators = [
            'dados mostram', 'pesquisa revela', 'estudo indica',
            'estatísticas apontam', 'levantamento mostra',
            'censo revela', 'segundo especialistas',
            'de acordo com', 'conforme dados',
            'ibge divulga', 'ministério informa',
            'pesquisadores descobriram', 'análise revela'
        ]
        
        self.relevance_boosters = [
            'autismo', 'TEA', 'autista', 'espectro autista',
            'neurodiversidade', 'inclusão', 'diagnóstico',
            'terapia', 'tratamento', 'educação especial'
        ]

    async def extract_facts_from_topic(self, db, topic_id: str) -> List[Dict[str, Any]]:
        """Extrai fatos de todas as notícias de um tópico específico."""
        try:
            if not ObjectId.is_valid(topic_id):
                logger.warning(f"ID de tópico inválido: {topic_id}")
                return []
                
            topic = await db.topics.find_one({'_id': ObjectId(topic_id), 'is_active': True})
            if not topic:
                logger.warning(f"Tópico não encontrado: {topic_id}")
                return []
            
            topic_name = topic.get('title', 'Tópico sem nome')
            
            # Buscar artigos do tópico
            article_ids = [ObjectId(aid) for aid in topic.get('articles', [])]
            articles = await db.news.find({'_id': {'$in': article_ids}}).to_list(length=None)
            
            logger.info(f"Extraindo fatos de {len(articles)} artigos do tópico '{topic_name}'")
            
            all_facts = []
            
            for article in articles:
                article_facts = self._extract_facts_from_article(article)
                
                for fact in article_facts:
                    fact.update({
                        'source_article_id': str(article['_id']),
                        'source_title': article.get('title', ''),
                        'source_url': article.get('source_url', ''),
                        'source_date': article.get('publish_date'),
                        'topic': topic_name,
                        'topic_id': topic_id
                    })
                
                all_facts.extend(article_facts)
            
            unique_facts = self._deduplicate_and_rank_facts(all_facts)
            
            logger.info(f"Extraídos {len(unique_facts)} fatos únicos do tópico '{topic_name}'")
            return unique_facts
            
        except Exception as e:
            logger.error(f"Erro ao extrair fatos do tópico {topic_id}: {str(e)}")
            return []

    def _extract_facts_from_article(self, article: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extrai fatos de um artigo específico."""
        facts = []
        
        full_text = ' '.join([
            article.get('title', ''),
            article.get('description', ''),
            article.get('content', '')
        ])
        
        sentences = self._split_into_sentences(full_text)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 20:
                continue
                
            fact_score = self._calculate_fact_score(sentence)
            
            if fact_score > 0.3:
                facts.append({
                    'text': sentence,
                    'score': fact_score,
                    'type': self._classify_fact_type(sentence),
                    'extracted_data': self._extract_structured_data(sentence),
                    'length': len(sentence),
                    'word_count': len(sentence.split())
                })
        
        return facts

    def _split_into_sentences(self, text: str) -> List[str]:
        """Divide texto em sentenças."""
        text = re.sub(r'\bDr\.\s+', 'Dr ', text)
        text = re.sub(r'\bSr\.\s+', 'Sr ', text) 
        text = re.sub(r'\bSra\.\s+', 'Sra ', text)
        text = re.sub(r'\betc\.\s+', 'etc ', text)
        
        sentence_endings = r'[.!?]+\s+'
        sentences = re.split(sentence_endings, text)
        
        cleaned_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence and len(sentence) > 10:
                cleaned_sentences.append(sentence)
        
        return cleaned_sentences

    def _calculate_fact_score(self, sentence: str) -> float:
        """Calcula score de relevância de uma sentença como fato."""
        score = 0.0
        sentence_lower = sentence.lower()
        
        pattern_matches = 0
        for pattern in self.fact_patterns:
            if re.search(pattern, sentence_lower):
                pattern_matches += 1
                score += 0.25
        
        for indicator in self.sentence_fact_indicators:
            if indicator in sentence_lower:
                score += 0.3
        
        if re.search(r'\d+[%％]', sentence):
            score += 0.4
        
        if re.search(r'\d+(?:\.\d+)?\s*(?:milhões?|mil|bilhões?)', sentence_lower):
            score += 0.3
        
        if re.search(r'\d{4}', sentence):
            score += 0.2
        
        relevance_count = sum(1 for keyword in self.relevance_boosters 
                            if keyword in sentence_lower)
        score += relevance_count * 0.1
        
        if pattern_matches > 1:
            score += 0.2
        
        sentence_length = len(sentence)
        if sentence_length < 50:
            score *= 0.7
        elif sentence_length > 300:
            score *= 0.8
        elif 80 <= sentence_length <= 200:
            score *= 1.1
        
        if sentence.count(',') >= 1 and sentence_length > 80:
            score += 0.1
        
        return min(score, 1.0)

    def _classify_fact_type(self, sentence: str) -> str:
        """Classifica o tipo de fato."""
        sentence_lower = sentence.lower()
        
        if re.search(r'\d+[%％]', sentence_lower):
            return 'estatística'
        elif re.search(r'lei|legislação|projeto|decreto|portaria', sentence_lower):
            return 'legislação'
        elif re.search(r'estudo|pesquisa|levantamento|descoberta', sentence_lower):
            return 'pesquisa'
        elif re.search(r'tratamento|terapia|diagnóstico|medicamento', sentence_lower):
            return 'saúde'
        elif re.search(r'educação|escola|ensino|professor|aluno', sentence_lower):
            return 'educação'
        elif re.search(r'violência|agressão|discriminação|bullying', sentence_lower):
            return 'violência'
        elif re.search(r'direito|inclusão|acessibilidade|benefício', sentence_lower):
            return 'direitos'
        elif re.search(r'\d{4}|ano|anos|desde|até', sentence_lower):
            return 'temporal'
        elif re.search(r'censo|ibge|dados oficiais', sentence_lower):
            return 'censo'
        else:
            return 'geral'

    def _extract_structured_data(self, sentence: str) -> Dict[str, Any]:
        """Extrai dados estruturados da sentença."""
        data = {}
        
        percentages = re.findall(r'(\d+(?:\.\d+)?)[%％]', sentence)
        if percentages:
            data['percentages'] = [float(p) for p in percentages]
        
        large_numbers = re.findall(r'(\d+(?:\.\d+)?)\s*(?:milhões?|mil|bilhões?)', sentence, re.IGNORECASE)
        if large_numbers:
            data['large_numbers'] = large_numbers
        
        years = re.findall(r'\b(19|20)\d{2}\b', sentence)
        if years:
            data['years'] = [''.join(year) for year in years]
        
        ages = re.findall(r'(\d+)\s*anos?', sentence)
        if ages:
            data['ages'] = [int(age) for age in ages]
        
        laws = re.findall(r'(?:lei|decreto|portaria)\s+(?:n?º?\s*)?(\d+(?:\/\d+)?)', sentence, re.IGNORECASE)
        if laws:
            data['laws'] = laws
        
        institutions = []
        if re.search(r'\bibge\b', sentence, re.IGNORECASE):
            institutions.append('IBGE')
        if re.search(r'\bministério\b', sentence, re.IGNORECASE):
            institutions.append('Ministério')
        if re.search(r'\buniversidade\b', sentence, re.IGNORECASE):
            institutions.append('Universidade')
        
        if institutions:
            data['institutions'] = institutions
        
        return data

    def _deduplicate_and_rank_facts(self, facts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicatas e ranqueia fatos por relevância."""
        if not facts:
            return []
        
        unique_facts = []
        seen_texts = set()
        
        facts_sorted = sorted(facts, key=lambda x: x['score'], reverse=True)
        
        for fact in facts_sorted:
            text_normalized = self._normalize_fact_text(fact['text'])
            
            is_duplicate = False
            for seen_text in seen_texts:
                if self._texts_are_similar(text_normalized, seen_text):
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_facts.append(fact)
                seen_texts.add(text_normalized)
                
                if len(unique_facts) >= 50:
                    break
        
        return unique_facts

    def _normalize_fact_text(self, text: str) -> str:
        """Normaliza texto para comparação de duplicatas."""
        normalized = re.sub(r'[^\w\s]', ' ', text.lower())
        normalized = re.sub(r'\s+', ' ', normalized)
        stopwords = {
            'o', 'a', 'os', 'as', 'de', 'do', 'da', 'dos', 'das', 
            'em', 'no', 'na', 'nos', 'nas', 'para', 'por', 'com',
            'um', 'uma', 'uns', 'umas', 'e', 'ou', 'mas', 'que',
            'se', 'é', 'são', 'foi', 'foram', 'tem', 'têm'
        }
        words = [w for w in normalized.split() if w not in stopwords and len(w) > 2]
        return ' '.join(words)

    def _texts_are_similar(self, text1: str, text2: str, threshold: float = 0.8) -> bool:
        """Verifica se dois textos são similares."""
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 and not words2:
            return True
        if not words1 or not words2:
            return False
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        jaccard_similarity = intersection / union if union > 0 else 0
        return jaccard_similarity >= threshold

    def get_facts_summary(self, facts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Gera resumo estatístico dos fatos extraídos."""
        if not facts:
            return {
                'total_facts': 0,
                'fact_types': {},
                'avg_score': 0.0,
                'top_score': 0.0,
                'has_statistics': False,
                'has_research': False,
                'has_legislation': False,
                'facts_with_structured_data': 0,
                'coverage_percentage': 0.0
            }
        
        scores = [fact['score'] for fact in facts]
        fact_types = Counter(fact['type'] for fact in facts)
        
        has_statistics = any(fact['type'] == 'estatística' for fact in facts)
        has_research = any(fact['type'] == 'pesquisa' for fact in facts)
        has_legislation = any(fact['type'] == 'legislação' for fact in facts)
        
        facts_with_data = sum(1 for fact in facts if fact.get('extracted_data'))
        
        return {
            'total_facts': len(facts),
            'fact_types': dict(fact_types),
            'avg_score': sum(scores) / len(scores),
            'top_score': max(scores),
            'has_statistics': has_statistics,
            'has_research': has_research,
            'has_legislation': has_legislation,
            'facts_with_structured_data': facts_with_data,
            'coverage_percentage': (facts_with_data / len(facts)) * 100
        }

# Instância global
fact_extraction_system = FactExtractionSystem()