"""
Sistema para reduzir falsos positivos na detecção de violência institucional.

Este arquivo deve ser salvo como: app/services/ai/classification/false_positive_reducer.py
"""
import asyncio
import logging
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime
import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
import re

logger = logging.getLogger(__name__)

class FalsePositiveReducer:
    """Sistema para reduzir falsos positivos em classificação de violência institucional."""
    
    def __init__(self):
        self.context_validator = None
        self.confidence_calibrator = None
        self.whitelist_patterns = []
        self.context_filters = {}
        
        # Padrões que frequentemente geram falsos positivos
        self.false_positive_patterns = {
            'positive_context': [
                r'apoio\s+(?:especializado|adequado|necessário)',
                r'inclusão\s+(?:bem-sucedida|efetiva)',
                r'adaptação\s+(?:curricular|pedagógica)',
                r'acompanhamento\s+individualizado',
                r'formação\s+(?:de\s+)?professores',
                r'política\s+(?:de\s+)?inclusão'
            ],
            'neutral_procedures': [
                r'protocolo\s+(?:padrão|estabelecido)',
                r'procedimento\s+(?:normal|rotineiro)',
                r'avaliação\s+(?:pedagógica|psicopedagógica)',
                r'encaminhamento\s+(?:especializado|técnico)'
            ],
            'constructive_criticism': [
                r'necessidade\s+de\s+(?:melhorar|aprimorar)',
                r'desafios\s+(?:a\s+serem\s+)?superados',
                r'oportunidades\s+de\s+crescimento',
                r'área\s+de\s+desenvolvimento'
            ]
        }
        
        # Indicadores de contexto genuinamente problemático
        self.genuine_problem_indicators = {
            'exclusion_language': [
                r'(?:não\s+)?(?:consegue|pode)\s+(?:frequentar|participar)',
                r'(?:suspensão|expulsão|transferência)\s+(?:compulsória|forçada)',
                r'impossibilidade\s+de\s+(?:atender|incluir)',
                r'falta\s+de\s+(?:condições|estrutura|preparo)'
            ],
            'discriminatory_actions': [
                r'recusa\s+(?:de\s+)?(?:matrícula|atendimento)',
                r'tratamento\s+(?:diferenciado|discriminatório)',
                r'isolamento\s+(?:social|físico)',
                r'negação\s+de\s+(?:direitos|acesso)'
            ],
            'institutional_failure': [
                r'ausência\s+de\s+(?:política|protocolo|suporte)',
                r'despreparo\s+(?:institucional|profissional)',
                r'violação\s+de\s+(?:direitos|legislação)',
                r'negligência\s+(?:institucional|educacional)'
            ]
        }

    async def initialize(self):
        """Inicializa os componentes do sistema."""
        try:
            # Calibrador de confiança
            self.confidence_calibrator = CalibratedClassifierCV(
                RandomForestClassifier(n_estimators=100, random_state=42),
                method='isotonic'
            )
            
            # Compilar padrões regex
            self._compile_patterns()
            
            logger.info("Sistema de redução de falsos positivos inicializado")
            
        except Exception as e:
            logger.error(f"Erro ao inicializar sistema: {str(e)}")
            raise

    def _compile_patterns(self):
        """Compila padrões regex para melhor performance."""
        self.compiled_patterns = {}
        
        for category, patterns in self.false_positive_patterns.items():
            self.compiled_patterns[category] = [
                re.compile(pattern, re.IGNORECASE) for pattern in patterns
            ]
        
        for category, patterns in self.genuine_problem_indicators.items():
            self.compiled_patterns[category] = [
                re.compile(pattern, re.IGNORECASE) for pattern in patterns
            ]

    async def validate_classification(
        self, 
        text: str, 
        initial_classification: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Valida classificação inicial para reduzir falsos positivos.
        
        Args:
            text: Texto analisado
            initial_classification: Classificação inicial
            context: Contexto adicional
            
        Returns:
            Classificação validada com score ajustado
        """
        validation_result = {
            'original_score': initial_classification.get('discrimination_score', 0.0),
            'adjusted_score': 0.0,
            'confidence_adjustment': 0.0,
            'false_positive_indicators': [],
            'genuine_problem_indicators': [],
            'context_analysis': {},
            'final_recommendation': 'unknown'
        }
        
        try:
            # 1. Análise de contexto positivo
            positive_context = await self._analyze_positive_context(text)
            validation_result['false_positive_indicators'].extend(positive_context)
            
            # 2. Análise de indicadores genuínos
            genuine_indicators = await self._analyze_genuine_problems(text)
            validation_result['genuine_problem_indicators'].extend(genuine_indicators)
            
            # 3. Análise contextual avançada
            if context:
                context_analysis = await self._advanced_context_analysis(text, context)
                validation_result['context_analysis'] = context_analysis
            
            # 4. Calibração de confiança
            confidence_adjustment = await self._calibrate_confidence(
                text, initial_classification, positive_context, genuine_indicators
            )
            validation_result['confidence_adjustment'] = confidence_adjustment
            
            # 5. Score ajustado
            adjusted_score = await self._calculate_adjusted_score(
                initial_classification['discrimination_score'],
                positive_context,
                genuine_indicators,
                confidence_adjustment
            )
            validation_result['adjusted_score'] = adjusted_score
            
            # 6. Recomendação final
            validation_result['final_recommendation'] = await self._generate_final_recommendation(
                validation_result
            )
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Erro na validação: {str(e)}")
            validation_result['error'] = str(e)
            return validation_result

    async def _analyze_positive_context(self, text: str) -> List[Dict[str, Any]]:
        """Analisa indicadores de contexto positivo."""
        positive_indicators = []
        
        for category, patterns in self.compiled_patterns.items():
            if category in self.false_positive_patterns:
                for pattern in patterns:
                    matches = pattern.finditer(text)
                    for match in matches:
                        positive_indicators.append({
                            'type': 'positive_context',
                            'category': category,
                            'matched_text': match.group(),
                            'position': match.span(),
                            'confidence_reduction': 0.3
                        })
        
        return positive_indicators

    async def _analyze_genuine_problems(self, text: str) -> List[Dict[str, Any]]:
        """Analisa indicadores de problemas genuínos."""
        genuine_indicators = []
        
        for category, patterns in self.compiled_patterns.items():
            if category in self.genuine_problem_indicators:
                for pattern in patterns:
                    matches = pattern.finditer(text)
                    for match in matches:
                        genuine_indicators.append({
                            'type': 'genuine_problem',
                            'category': category,
                            'matched_text': match.group(),
                            'position': match.span(),
                            'confidence_boost': 0.2
                        })
        
        return genuine_indicators

    async def _advanced_context_analysis(
        self, 
        text: str, 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Análise contextual avançada."""
        context_analysis = {
            'source_type': context.get('source_type', 'unknown'),
            'article_tone': 'neutral',
            'institutional_involvement': False,
            'legal_framework_mentioned': False,
            'stakeholder_perspectives': []
        }
        
        # Detectar tom do artigo
        if any(word in text.lower() for word in ['denuncia', 'acusa', 'viola', 'discrimina']):
            context_analysis['article_tone'] = 'accusatory'
        elif any(word in text.lower() for word in ['defende', 'justifica', 'esclarece']):
            context_analysis['article_tone'] = 'defensive'
        elif any(word in text.lower() for word in ['promove', 'apoia', 'inclui', 'acolhe']):
            context_analysis['article_tone'] = 'positive'
        
        # Detectar envolvimento institucional
        institutions = ['escola', 'secretaria', 'ministério', 'governo', 'prefeitura']
        context_analysis['institutional_involvement'] = any(
            inst in text.lower() for inst in institutions
        )
        
        # Detectar menção ao framework legal
        legal_terms = ['lei', 'constituição', 'ldb', 'estatuto', 'direito', 'legislação']
        context_analysis['legal_framework_mentioned'] = any(
            term in text.lower() for term in legal_terms
        )
        
        return context_analysis

    async def _calibrate_confidence(
        self, 
        text: str, 
        initial_classification: Dict[str, Any],
        positive_indicators: List[Dict[str, Any]],
        genuine_indicators: List[Dict[str, Any]]
    ) -> float:
        """Calibra a confiança da classificação."""
        base_confidence = initial_classification.get('confidence', 0.5)
        
        # Ajuste baseado em indicadores positivos
        positive_adjustment = sum(
            indicator.get('confidence_reduction', 0) for indicator in positive_indicators
        )
        
        # Ajuste baseado em indicadores genuínos
        genuine_adjustment = sum(
            indicator.get('confidence_boost', 0) for indicator in genuine_indicators
        )
        
        # Calibração final
        adjusted_confidence = base_confidence - positive_adjustment + genuine_adjustment
        adjusted_confidence = max(0.0, min(1.0, adjusted_confidence))
        
        return adjusted_confidence - base_confidence

    async def _calculate_adjusted_score(
        self,
        original_score: float,
        positive_indicators: List[Dict[str, Any]],
        genuine_indicators: List[Dict[str, Any]],
        confidence_adjustment: float
    ) -> float:
        """Calcula score ajustado."""
        # Fator de redução baseado em contexto positivo
        positive_factor = 1.0 - (len(positive_indicators) * 0.15)
        positive_factor = max(0.3, positive_factor)  # Mínimo de 30% do score original
        
        # Fator de aumento baseado em indicadores genuínos
        genuine_factor = 1.0 + (len(genuine_indicators) * 0.1)
        genuine_factor = min(1.5, genuine_factor)  # Máximo de 150% do score original
        
        # Score ajustado
        adjusted_score = original_score * positive_factor * genuine_factor
        
        # Ajuste adicional baseado na confiança
        if confidence_adjustment < -0.3:  # Muita redução de confiança
            adjusted_score *= 0.7
        elif confidence_adjustment > 0.2:  # Aumento significativo de confiança
            adjusted_score *= 1.2
        
        return max(0.0, min(1.0, adjusted_score))

    async def _generate_final_recommendation(
        self, 
        validation_result: Dict[str, Any]
    ) -> str:
        """Gera recomendação final."""
        original_score = validation_result['original_score']
        adjusted_score = validation_result['adjusted_score']
        false_positives = len(validation_result['false_positive_indicators'])
        genuine_problems = len(validation_result['genuine_problem_indicators'])
        
        # Lógica de decisão
        if adjusted_score < 0.3:
            return 'likely_false_positive'
        elif adjusted_score > 0.7 and genuine_problems > false_positives:
            return 'confirmed_problem'
        elif false_positives > genuine_problems and adjusted_score < original_score * 0.7:
            return 'probable_false_positive'
        elif genuine_problems > 0 and adjusted_score > 0.5:
            return 'requires_investigation'
        else:
            return 'uncertain_needs_review'

    async def update_model_with_feedback(
        self, 
        text: str, 
        predicted_label: str, 
        actual_label: str,
        features: Dict[str, Any]
    ):
        """Atualiza modelo com feedback humano."""
        try:
            # Em produção, isso atualizaria o modelo de ML
            # Por agora, apenas log para análise posterior
            feedback_data = {
                'timestamp': datetime.utcnow(),
                'text_hash': hash(text),
                'predicted': predicted_label,
                'actual': actual_label,
                'features': features,
                'was_correct': predicted_label == actual_label
            }
            
            logger.info(f"Feedback recebido: {feedback_data}")
            
            # Aqui você implementaria a lógica de retreinamento
            # ou ajuste de pesos baseado no feedback
            
        except Exception as e:
            logger.error(f"Erro ao processar feedback: {str(e)}")

# Exemplo de uso
async def main():
    """Exemplo de uso do sistema de redução de falsos positivos."""
    reducer = FalsePositiveReducer()
    await reducer.initialize()
    
    # Texto que pode gerar falso positivo
    text = """
    A escola implementou um programa de apoio especializado para 
    estudantes com autismo. O protocolo padrão inclui avaliação 
    pedagógica individualizada e acompanhamento por profissionais 
    capacitados. A política de inclusão tem mostrado resultados 
    positivos na adaptação curricular.
    """
    
    # Classificação inicial (simulada)
    initial = {
        'discrimination_score': 0.6,  # Score alto por mencionar "protocolo padrão"
        'confidence': 0.7
    }
    
    context = {
        'source_type': 'educational_news',
        'domain': 'education'
    }
    
    result = await reducer.validate_classification(text, initial, context)
    
    print(f"Score original: {result['original_score']:.2f}")
    print(f"Score ajustado: {result['adjusted_score']:.2f}")
    print(f"Recomendação: {result['final_recommendation']}")
    print(f"Indicadores de falso positivo: {len(result['false_positive_indicators'])}")
    print(f"Indicadores genuínos: {len(result['genuine_problem_indicators'])}")

if __name__ == "__main__":
    asyncio.run(main())