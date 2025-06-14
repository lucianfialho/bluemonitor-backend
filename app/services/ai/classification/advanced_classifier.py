"""
Sistema de classificação avançada para detectar linguagem sutil sobre violência e discriminação.

Este arquivo deve ser salvo como: app/services/ai/classification/advanced_classifier.py
"""
import asyncio
import logging
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime
import numpy as np
from sklearn.ensemble import VotingClassifier
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
import spacy
import re

logger = logging.getLogger(__name__)

class AdvancedClassificationService:
    """Serviço de classificação avançada para detectar linguagem sutil."""
    
    def __init__(self):
        self.nlp = None
        self.sentiment_analyzer = None
        self.bias_detector = None
        self.context_analyzer = None
        
        # Padrões linguísticos para detecção sutil
        self.subtle_patterns = {
            'minimization': [
                r'apenas\s+(?:um\s+)?(?:pouco|leve|simples)',
                r'não\s+é\s+tão\s+(?:grave|sério|importante)',
                r'exagero',
                r'drama(?:tização)?'
            ],
            'victim_blaming': [
                r'deveria\s+(?:ter|saber|entender)',
                r'culpa\s+(?:própria|dele|dela)',
                r'provocou',
                r'não\s+se\s+adaptou'
            ],
            'institutional_gaslighting': [
                r'(?:política|norma|procedimento)\s+(?:padrão|normal|comum)',
                r'para\s+(?:todos|todo\s+mundo)',
                r'não\s+fazemos\s+exceções',
                r'regras\s+são\s+regras'
            ],
            'euphemisms': [
                r'pessoa\s+(?:especial|diferente)',
                r'necessidades\s+especiais',
                r'comportamento\s+inadequado',
                r'não\s+se\s+enquadra'
            ]
        }
        
        # Contextos que amplificam problemas
        self.amplifying_contexts = [
            'escola', 'educação', 'ensino', 'professor',
            'trabalho', 'emprego', 'contratação',
            'saúde', 'médico', 'tratamento',
            'transporte', 'público', 'acesso'
        ]

    async def initialize(self):
        """Inicializa os modelos de NLP."""
        try:
            # Carregamento assíncrono dos modelos
            self.nlp = spacy.load("pt_core_news_sm")
            
            # Analisador de sentimento contextual
            self.sentiment_analyzer = pipeline(
                "sentiment-analysis",
                model="neuralmind/bert-base-portuguese-cased",
                device=-1
            )
            
            # Detector de viés linguístico personalizado
            self.bias_detector = await self._load_bias_detector()
            
            logger.info("Modelos de classificação avançada inicializados")
            
        except Exception as e:
            logger.error(f"Erro ao inicializar modelos: {str(e)}")
            raise

    async def _load_bias_detector(self):
        """Carrega modelo personalizado para detecção de viés."""
        # Implementação simplificada - em produção, usaria modelo treinado
        return pipeline(
            "text-classification",
            model="microsoft/DialoGPT-medium",
            device=-1
        )

    async def classify_subtle_discrimination(
        self, 
        text: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Classifica texto para detectar discriminação sutil.
        
        Args:
            text: Texto para análise
            context: Contexto adicional (fonte, categoria, etc.)
            
        Returns:
            Análise completa com scores e detalhes
        """
        if not self.nlp:
            await self.initialize()
            
        analysis = {
            'text': text,
            'timestamp': datetime.utcnow(),
            'discrimination_score': 0.0,
            'confidence': 0.0,
            'detected_patterns': [],
            'linguistic_markers': {},
            'context_analysis': {},
            'recommendations': []
        }
        
        try:
            # 1. Análise de padrões sutis
            pattern_analysis = await self._analyze_subtle_patterns(text)
            analysis['detected_patterns'] = pattern_analysis
            
            # 2. Análise linguística profunda
            linguistic_analysis = await self._deep_linguistic_analysis(text)
            analysis['linguistic_markers'] = linguistic_analysis
            
            # 3. Análise contextual
            if context:
                context_analysis = await self._analyze_context(text, context)
                analysis['context_analysis'] = context_analysis
            
            # 4. Score final combinado
            final_score = await self._calculate_discrimination_score(
                pattern_analysis, linguistic_analysis, context_analysis if context else {}
            )
            analysis['discrimination_score'] = final_score['score']
            analysis['confidence'] = final_score['confidence']
            
            # 5. Recomendações
            analysis['recommendations'] = await self._generate_recommendations(analysis)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Erro na classificação sutil: {str(e)}")
            analysis['error'] = str(e)
            return analysis

    async def _analyze_subtle_patterns(self, text: str) -> List[Dict[str, Any]]:
        """Analisa padrões linguísticos sutis."""
        detected = []
        text_lower = text.lower()
        
        for pattern_type, patterns in self.subtle_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text_lower)
                for match in matches:
                    detected.append({
                        'type': pattern_type,
                        'pattern': pattern,
                        'matched_text': match.group(),
                        'position': match.span(),
                        'severity': self._calculate_pattern_severity(pattern_type)
                    })
        
        return detected

    async def _deep_linguistic_analysis(self, text: str) -> Dict[str, Any]:
        """Análise linguística profunda usando spaCy."""
        doc = self.nlp(text)
        
        analysis = {
            'entities': [],
            'sentiment_markers': [],
            'modal_verbs': [],
            'negations': [],
            'hedging_language': [],
            'power_dynamics': []
        }
        
        # Entidades relacionadas a autismo
        autism_entities = []
        for ent in doc.ents:
            if any(term in ent.text.lower() for term in ['autis', 'tea', 'espectro']):
                autism_entities.append({
                    'text': ent.text,
                    'label': ent.label_,
                    'start': ent.start_char,
                    'end': ent.end_char
                })
        analysis['entities'] = autism_entities
        
        # Verbos modais (indicam incerteza, obrigação)
        modal_verbs = []
        for token in doc:
            if token.text.lower() in ['deve', 'deveria', 'precisa', 'tem que', 'pode']:
                modal_verbs.append({
                    'verb': token.text,
                    'dependency': token.dep_,
                    'head': token.head.text
                })
        analysis['modal_verbs'] = modal_verbs
        
        # Linguagem de minimização (hedging)
        hedging_words = ['talvez', 'possivelmente', 'aparentemente', 'supostamente']
        for token in doc:
            if token.text.lower() in hedging_words:
                analysis['hedging_language'].append({
                    'word': token.text,
                    'context': doc[max(0, token.i-3):token.i+4].text
                })
        
        return analysis

    async def _analyze_context(self, text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analisa o contexto para amplificar detecções."""
        context_analysis = {
            'domain': context.get('domain', 'unknown'),
            'source_credibility': context.get('source_credibility', 0.5),
            'amplification_factors': [],
            'risk_level': 'low'
        }
        
        # Verifica se está em contexto sensível
        text_lower = text.lower()
        for context_keyword in self.amplifying_contexts:
            if context_keyword in text_lower:
                context_analysis['amplification_factors'].append({
                    'factor': context_keyword,
                    'weight': 1.5 if context_keyword in ['escola', 'trabalho'] else 1.2
                })
        
        # Define nível de risco baseado no contexto
        if len(context_analysis['amplification_factors']) > 2:
            context_analysis['risk_level'] = 'high'
        elif len(context_analysis['amplification_factors']) > 0:
            context_analysis['risk_level'] = 'medium'
            
        return context_analysis

    def _calculate_pattern_severity(self, pattern_type: str) -> float:
        """Calcula severidade do padrão detectado."""
        severity_map = {
            'victim_blaming': 0.8,
            'institutional_gaslighting': 0.9,
            'minimization': 0.6,
            'euphemisms': 0.4
        }
        return severity_map.get(pattern_type, 0.5)

    async def _calculate_discrimination_score(
        self, 
        patterns: List[Dict[str, Any]], 
        linguistic: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> Dict[str, float]:
        """Calcula score final de discriminação."""
        base_score = 0.0
        confidence = 0.0
        
        # Score dos padrões detectados
        pattern_score = sum(p['severity'] for p in patterns) / max(len(patterns), 1)
        
        # Score linguístico
        linguistic_score = len(linguistic.get('modal_verbs', [])) * 0.1
        linguistic_score += len(linguistic.get('hedging_language', [])) * 0.15
        
        # Amplificação contextual
        context_multiplier = 1.0
        for factor in context.get('amplification_factors', []):
            context_multiplier *= factor['weight']
        
        # Score final
        base_score = (pattern_score * 0.6 + linguistic_score * 0.4) * context_multiplier
        base_score = min(base_score, 1.0)  # Limita a 1.0
        
        # Confiança baseada na quantidade de evidências
        evidence_count = len(patterns) + len(linguistic.get('modal_verbs', [])) + len(context.get('amplification_factors', []))
        confidence = min(evidence_count * 0.2, 1.0)
        
        return {
            'score': base_score,
            'confidence': confidence
        }

    async def _generate_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """Gera recomendações baseadas na análise."""
        recommendations = []
        
        score = analysis['discrimination_score']
        patterns = analysis['detected_patterns']
        
        if score > 0.7:
            recommendations.append("ALERTA: Alto risco de discriminação detectado")
            recommendations.append("Revisão manual urgente recomendada")
        elif score > 0.4:
            recommendations.append("Possível discriminação sutil detectada")
            recommendations.append("Análise adicional recomendada")
        
        # Recomendações específicas por padrão
        pattern_types = {p['type'] for p in patterns}
        
        if 'victim_blaming' in pattern_types:
            recommendations.append("Linguagem de culpabilização da vítima detectada")
        
        if 'institutional_gaslighting' in pattern_types:
            recommendations.append("Possível invalidação institucional detectada")
        
        if 'minimization' in pattern_types:
            recommendations.append("Linguagem minimizadora detectada")
            
        return recommendations

# Exemplo de uso
async def main():
    """Exemplo de uso do sistema de classificação avançada."""
    classifier = AdvancedClassificationService()
    
    # Texto exemplo com discriminação sutil
    text = """
    A criança não consegue se adaptar às regras da escola. 
    É apenas um comportamento inadequado que precisa ser corrigido. 
    Todos os alunos devem seguir os mesmos procedimentos padrão.
    """
    
    context = {
        'domain': 'education',
        'source_credibility': 0.8
    }
    
    result = await classifier.classify_subtle_discrimination(text, context)
    
    print(f"Score de discriminação: {result['discrimination_score']:.2f}")
    print(f"Confiança: {result['confidence']:.2f}")
    print(f"Padrões detectados: {len(result['detected_patterns'])}")
    print(f"Recomendações: {result['recommendations']}")

if __name__ == "__main__":
    asyncio.run(main())