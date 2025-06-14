"""
Sistema de aprendizado ativo para melhorar classificação com feedback humano.

Este arquivo deve ser salvo como: app/services/ai/classification/active_learning.py
"""
import asyncio
import logging
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime, timedelta
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score
from sklearn.model_selection import cross_val_score
import json
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class FeedbackEntry:
    """Entrada de feedback humano."""
    id: str
    text: str
    original_prediction: Dict[str, Any]
    human_label: str
    human_confidence: float
    annotator_id: str
    timestamp: datetime
    context: Dict[str, Any]
    difficulty_level: str  # 'easy', 'medium', 'hard'
    reasoning: Optional[str] = None

@dataclass
class UncertainSample:
    """Amostra incerta para revisão humana."""
    id: str
    text: str
    prediction: Dict[str, Any]
    uncertainty_score: float
    features: Dict[str, Any]
    priority: int  # 1-5, onde 5 é prioridade máxima
    suggested_reviewers: List[str]

class ActiveLearningSystem:
    """Sistema de aprendizado ativo para classificação de notícias."""
    
    def __init__(self, mongodb_manager):
        self.db_manager = mongodb_manager
        self.model = None
        self.feedback_history = []
        self.uncertainty_threshold = 0.7
        self.min_samples_for_retrain = 50
        self.performance_history = []
        
        # Estratégias de seleção de amostras
        self.selection_strategies = {
            'uncertainty_sampling': self._uncertainty_sampling,
            'diversity_sampling': self._diversity_sampling,
            'disagreement_sampling': self._disagreement_sampling,
            'hybrid_sampling': self._hybrid_sampling
        }
        
        # Perfis de anotadores
        self.annotator_profiles = {}

    async def initialize(self):
        """Inicializa o sistema de aprendizado ativo."""
        try:
            # Inicializar modelo base
            self.model = RandomForestClassifier(
                n_estimators=100,
                random_state=42,
                class_weight='balanced'
            )
            
            # Carregar histórico de feedback
            await self._load_feedback_history()
            
            # Carregar perfis de anotadores
            await self._load_annotator_profiles()
            
            logger.info("Sistema de aprendizado ativo inicializado")
            
        except Exception as e:
            logger.error(f"Erro ao inicializar sistema: {str(e)}")
            raise

    async def _load_feedback_history(self):
        """Carrega histórico de feedback do banco de dados."""
        try:
            async with self.db_manager.get_db() as db:
                feedback_docs = await db.human_feedback.find({}).to_list(length=None)
                
                self.feedback_history = [
                    FeedbackEntry(
                        id=doc['_id'],
                        text=doc['text'],
                        original_prediction=doc['original_prediction'],
                        human_label=doc['human_label'],
                        human_confidence=doc['human_confidence'],
                        annotator_id=doc['annotator_id'],
                        timestamp=doc['timestamp'],
                        context=doc.get('context', {}),
                        difficulty_level=doc.get('difficulty_level', 'medium'),
                        reasoning=doc.get('reasoning')
                    )
                    for doc in feedback_docs
                ]
                
                logger.info(f"Carregados {len(self.feedback_history)} registros de feedback")
                
        except Exception as e:
            logger.error(f"Erro ao carregar feedback: {str(e)}")

    async def _load_annotator_profiles(self):
        """Carrega perfis dos anotadores."""
        try:
            async with self.db_manager.get_db() as db:
                profiles = await db.annotator_profiles.find({}).to_list(length=None)
                
                for profile in profiles:
                    self.annotator_profiles[profile['annotator_id']] = {
                        'expertise_areas': profile.get('expertise_areas', []),
                        'accuracy_history': profile.get('accuracy_history', []),
                        'avg_response_time': profile.get('avg_response_time', 0),
                        'specializations': profile.get('specializations', []),
                        'workload': profile.get('current_workload', 0)
                    }
                
        except Exception as e:
            logger.error(f"Erro ao carregar perfis: {str(e)}")

    async def identify_uncertain_samples(
        self, 
        articles: List[Dict[str, Any]], 
        strategy: str = 'hybrid_sampling'
    ) -> List[UncertainSample]:
        """
        Identifica amostras incertas que precisam de revisão humana.
        
        Args:
            articles: Lista de artigos para análise
            strategy: Estratégia de seleção de amostras
            
        Returns:
            Lista de amostras incertas ordenadas por prioridade
        """
        uncertain_samples = []
        
        try:
            strategy_func = self.selection_strategies.get(strategy, self._hybrid_sampling)
            
            for article in articles:
                # Obter predição do modelo atual
                prediction = await self._get_model_prediction(article)
                
                # Calcular incerteza
                uncertainty = await strategy_func(article, prediction)
                
                if uncertainty['score'] > self.uncertainty_threshold:
                    sample = UncertainSample(
                        id=str(article.get('_id')),
                        text=article.get('extracted_content', ''),
                        prediction=prediction,
                        uncertainty_score=uncertainty['score'],
                        features=uncertainty.get('features', {}),
                        priority=self._calculate_priority(uncertainty, article),
                        suggested_reviewers=await self._suggest_reviewers(article, uncertainty)
                    )
                    uncertain_samples.append(sample)
            
            # Ordenar por prioridade
            uncertain_samples.sort(key=lambda x: x.priority, reverse=True)
            
            return uncertain_samples
            
        except Exception as e:
            logger.error(f"Erro ao identificar amostras incertas: {str(e)}")
            return []

    async def _get_model_prediction(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """Obtém predição do modelo atual."""
        # Aqui você integraria com seu sistema de classificação existente
        # Por agora, simulamos uma predição
        
        text = article.get('extracted_content', '')
        features = self._extract_features(text)
        
        # Simulação de predição com incerteza
        discrimination_score = np.random.random()
        confidence = np.random.random()
        
        return {
            'discrimination_score': discrimination_score,
            'confidence': confidence,
            'features': features,
            'timestamp': datetime.utcnow()
        }

    def _extract_features(self, text: str) -> Dict[str, Any]:
        """Extrai features do texto para análise de incerteza."""
        return {
            'text_length': len(text),
            'word_count': len(text.split()),
            'has_emotional_language': any(word in text.lower() for word in ['raiva', 'indignação', 'revolta']),
            'has_institutional_terms': any(word in text.lower() for word in ['escola', 'governo', 'secretaria']),
            'complexity_score': len(set(text.split())) / len(text.split()) if text.split() else 0
        }

    async def _uncertainty_sampling(
        self, 
        article: Dict[str, Any], 
        prediction: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Estratégia de amostragem por incerteza."""
        confidence = prediction.get('confidence', 0.5)
        discrimination_score = prediction.get('discrimination_score', 0.5)
        
        # Calcular incerteza como distância da decisão
        uncertainty = 1 - abs(discrimination_score - 0.5) * 2
        
        # Ajustar pela confiança
        final_uncertainty = uncertainty * (1 - confidence)
        
        return {
            'score': final_uncertainty,
            'method': 'uncertainty_sampling',
            'features': {
                'base_uncertainty': uncertainty,
                'confidence_penalty': 1 - confidence
            }
        }

    async def _diversity_sampling(
        self, 
        article: Dict[str, Any], 
        prediction: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Estratégia de amostragem por diversidade."""
        features = prediction.get('features', {})
        
        # Calcular diversidade baseada em features não vistas
        diversity_score = 0.0
        
        # Verificar se as features são diferentes do histórico
        if self.feedback_history:
            historical_features = [fb.context.get('features', {}) for fb in self.feedback_history]
            
            # Simplificação: calcular diferença nas features
            if historical_features:
                avg_historical = {}
                for key in features:
                    values = [hf.get(key, 0) for hf in historical_features if key in hf]
                    avg_historical[key] = np.mean(values) if values else 0
                
                # Calcular distância
                distances = []
                for key, value in features.items():
                    if key in avg_historical:
                        distances.append(abs(value - avg_historical[key]))
                
                diversity_score = np.mean(distances) if distances else 0.5
        else:
            diversity_score = 0.8  # Alta diversidade se não há histórico
        
        return {
            'score': diversity_score,
            'method': 'diversity_sampling',
            'features': {
                'diversity_score': diversity_score,
                'historical_samples': len(self.feedback_history)
            }
        }

    async def _disagreement_sampling(
        self, 
        article: Dict[str, Any], 
        prediction: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Estratégia de amostragem por desacordo entre modelos."""
        # Simular predições de múltiplos modelos
        models_predictions = [
            np.random.random() for _ in range(3)  # Simular 3 modelos
        ]
        
        # Calcular variância das predições
        disagreement = np.var(models_predictions)
        
        return {
            'score': disagreement,
            'method': 'disagreement_sampling',
            'features': {
                'model_predictions': models_predictions,
                'variance': disagreement
            }
        }

    async def _hybrid_sampling(
        self, 
        article: Dict[str, Any], 
        prediction: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Estratégia híbrida combinando múltiplas abordagens."""
        uncertainty = await self._uncertainty_sampling(article, prediction)
        diversity = await self._diversity_sampling(article, prediction)
        disagreement = await self._disagreement_sampling(article, prediction)
        
        # Combinar scores com pesos
        weights = {
            'uncertainty': 0.4,
            'diversity': 0.3,
            'disagreement': 0.3
        }
        
        hybrid_score = (
            uncertainty['score'] * weights['uncertainty'] +
            diversity['score'] * weights['diversity'] +
            disagreement['score'] * weights['disagreement']
        )
        
        return {
            'score': hybrid_score,
            'method': 'hybrid_sampling',
            'features': {
                'uncertainty_component': uncertainty['score'],
                'diversity_component': diversity['score'],
                'disagreement_component': disagreement['score'],
                'weights': weights
            }
        }

    def _calculate_priority(
        self, 
        uncertainty: Dict[str, Any], 
        article: Dict[str, Any]
    ) -> int:
        """Calcula prioridade da amostra (1-5)."""
        score = uncertainty['score']
        
        # Fatores que aumentam prioridade
        priority_factors = []
        
        # Alta incerteza = alta prioridade
        if score > 0.8:
            priority_factors.append(2)
        elif score > 0.6:
            priority_factors.append(1)
        
        # Artigos recentes têm maior prioridade
        pub_date = article.get('publish_date')
        if pub_date:
            try:
                if isinstance(pub_date, str):
                    pub_date = datetime.fromisoformat(pub_date)
                
                days_old = (datetime.utcnow() - pub_date).days
                if days_old < 7:
                    priority_factors.append(1)
            except:
                pass
        
        # Fontes importantes têm maior prioridade
        important_sources = ['folha', 'globo', 'estadão', 'uol']
        source = article.get('source_name', '').lower()
        if any(imp_source in source for imp_source in important_sources):
            priority_factors.append(1)
        
        # Calcular prioridade final
        base_priority = min(5, max(1, int(score * 5)))
        bonus = min(2, sum(priority_factors))
        
        return min(5, base_priority + bonus)

    async def _suggest_reviewers(
        self, 
        article: Dict[str, Any], 
        uncertainty: Dict[str, Any]
    ) -> List[str]:
        """Sugere revisores com base no artigo e incerteza."""
        suggested = []
        
        text = article.get('extracted_content', '').lower()
        
        # Sugerir revisores baseado no conteúdo
        for annotator_id, profile in self.annotator_profiles.items():
            score = 0
            
            # Verificar especialização
            for area in profile.get('expertise_areas', []):
                if area.lower() in text:
                    score += 2
            
            # Verificar carga de trabalho
            if profile.get('workload', 0) < 10:  # Menos de 10 tarefas pendentes
                score += 1
            
            # Verificar histórico de acurácia
            accuracy_history = profile.get('accuracy_history', [])
            if accuracy_history:
                avg_accuracy = np.mean(accuracy_history)
                if avg_accuracy > 0.8:
                    score += 1
            
            if score >= 2:
                suggested.append(annotator_id)
        
        # Limitar a 3 sugestões
        return suggested[:3]

    async def collect_feedback(
        self, 
        sample_id: str, 
        human_label: str, 
        confidence: float,
        annotator_id: str,
        reasoning: Optional[str] = None
    ) -> FeedbackEntry:
        """Coleta feedback humano sobre uma amostra."""
        try:
            # Encontrar a amostra original
            async with self.db_manager.get_db() as db:
                article = await db.news.find_one({"_id": sample_id})
                
                if not article:
                    raise ValueError(f"Artigo não encontrado: {sample_id}")
                
                # Obter predição original
                original_prediction = await self._get_model_prediction(article)
                
                # Criar entrada de feedback
                feedback = FeedbackEntry(
                    id=f"feedback_{datetime.utcnow().isoformat()}",
                    text=article.get('extracted_content', ''),
                    original_prediction=original_prediction,
                    human_label=human_label,
                    human_confidence=confidence,
                    annotator_id=annotator_id,
                    timestamp=datetime.utcnow(),
                    context={
                        'article_id': sample_id,
                        'source': article.get('source_name'),
                        'features': original_prediction.get('features', {})
                    },
                    difficulty_level=self._assess_difficulty(article, original_prediction),
                    reasoning=reasoning
                )
                
                # Salvar no banco
                await db.human_feedback.insert_one(asdict(feedback))
                
                # Adicionar ao histórico
                self.feedback_history.append(feedback)
                
                # Atualizar perfil do anotador
                await self._update_annotator_profile(annotator_id, feedback)
                
                logger.info(f"Feedback coletado para {sample_id} por {annotator_id}")
                
                return feedback
                
        except Exception as e:
            logger.error(f"Erro ao coletar feedback: {str(e)}")
            raise

    def _assess_difficulty(
        self, 
        article: Dict[str, Any], 
        prediction: Dict[str, Any]
    ) -> str:
        """Avalia dificuldade da amostra."""
        confidence = prediction.get('confidence', 0.5)
        discrimination_score = prediction.get('discrimination_score', 0.5)
        
        # Baixa confiança = alta dificuldade
        if confidence < 0.4:
            return 'hard'
        elif confidence < 0.7:
            return 'medium'
        else:
            return 'easy'

    async def _update_annotator_profile(
        self, 
        annotator_id: str, 
        feedback: FeedbackEntry
    ):
        """Atualiza perfil do anotador baseado no feedback."""
        try:
            if annotator_id not in self.annotator_profiles:
                self.annotator_profiles[annotator_id] = {
                    'expertise_areas': [],
                    'accuracy_history': [],
                    'avg_response_time': 0,
                    'specializations': [],
                    'workload': 0
                }
            
            profile = self.annotator_profiles[annotator_id]
            
            # Calcular acurácia (simplificado)
            original_score = feedback.original_prediction.get('discrimination_score', 0.5)
            human_score = 1.0 if feedback.human_label == 'discrimination' else 0.0
            
            accuracy = 1.0 - abs(original_score - human_score)
            profile['accuracy_history'].append(accuracy)
            
            # Manter apenas últimas 50 entradas
            if len(profile['accuracy_history']) > 50:
                profile['accuracy_history'] = profile['accuracy_history'][-50:]
            
            # Atualizar no banco
            async with self.db_manager.get_db() as db:
                await db.annotator_profiles.update_one(
                    {'annotator_id': annotator_id},
                    {'$set': profile},
                    upsert=True
                )
                
        except Exception as e:
            logger.error(f"Erro ao atualizar perfil: {str(e)}")

    async def should_retrain_model(self) -> bool:
        """Determina se o modelo deve ser retreinado."""
        # Critérios para retreinamento
        recent_feedback = [
            fb for fb in self.feedback_history
            if (datetime.utcnow() - fb.timestamp).days < 30
        ]
        
        # Verificar se há feedback suficiente
        if len(recent_feedback) < self.min_samples_for_retrain:
            return False
        
        # Verificar se a performance está degradando
        if len(self.performance_history) >= 2:
            recent_performance = np.mean(self.performance_history[-5:])
            older_performance = np.mean(self.performance_history[-10:-5])
            
            if recent_performance < older_performance - 0.05:  # 5% de degradação
                return True
        
        # Verificar se há muito feedback discordante
        disagreement_rate = len([
            fb for fb in recent_feedback
            if abs(fb.original_prediction.get('discrimination_score', 0.5) - 
                   (1.0 if fb.human_label == 'discrimination' else 0.0)) > 0.3
        ]) / len(recent_feedback)
        
        return disagreement_rate > 0.3

    async def retrain_model(self) -> Dict[str, Any]:
        """Retreina o modelo com novo feedback."""
        try:
            if not self.feedback_history:
                return {'status': 'no_data', 'message': 'Nenhum feedback disponível'}
            
            # Preparar dados de treino
            X, y = self._prepare_training_data()
            
            if len(X) < 10:
                return {'status': 'insufficient_data', 'message': 'Dados insuficientes para retreino'}
            
            # Treinar novo modelo
            new_model = RandomForestClassifier(
                n_estimators=100,
                random_state=42,
                class_weight='balanced'
            )
            
            new_model.fit(X, y)
            
            # Avaliar performance
            performance = cross_val_score(new_model, X, y, cv=5)
            avg_performance = np.mean(performance)
            
            # Atualizar modelo se performance melhorou
            if not self.performance_history or avg_performance > np.mean(self.performance_history[-5:]):
                self.model = new_model
                self.performance_history.append(avg_performance)
                
                # Salvar modelo
                await self._save_model()
                
                return {
                    'status': 'success',
                    'performance': avg_performance,
                    'training_samples': len(X),
                    'improvement': avg_performance - (np.mean(self.performance_history[-6:-1]) if len(self.performance_history) > 1 else 0)
                }
            else:
                return {
                    'status': 'no_improvement',
                    'performance': avg_performance,
                    'current_best': np.mean(self.performance_history[-5:])
                }
                
        except Exception as e:
            logger.error(f"Erro no retreinamento: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    def _prepare_training_data(self) -> Tuple[np.ndarray, np.ndarray]:
        """Prepara dados para treinamento."""
        X = []
        y = []
        
        for feedback in self.feedback_history:
            # Features simplificadas
            features = feedback.context.get('features', {})
            feature_vector = [
                features.get('text_length', 0),
                features.get('word_count', 0),
                float(features.get('has_emotional_language', False)),
                float(features.get('has_institutional_terms', False)),
                features.get('complexity_score', 0),
                feedback.human_confidence
            ]
            
            X.append(feature_vector)
            y.append(1 if feedback.human_label == 'discrimination' else 0)
        
        return np.array(X), np.array(y)

    async def _save_model(self):
        """Salva modelo treinado."""
        try:
            # Em produção, salvaria o modelo serializado
            model_metadata = {
                'timestamp': datetime.utcnow(),
                'performance': self.performance_history[-1] if self.performance_history else 0,
                'training_samples': len(self.feedback_history),
                'version': len(self.performance_history)
            }
            
            async with self.db_manager.get_db() as db:
                await db.model_versions.insert_one(model_metadata)
                
        except Exception as e:
            logger.error(f"Erro ao salvar modelo: {str(e)}")

    async def get_learning_statistics(self) -> Dict[str, Any]:
        """Obtém estatísticas do sistema de aprendizado."""
        try:
            total_feedback = len(self.feedback_history)
            recent_feedback = len([
                fb for fb in self.feedback_history
                if (datetime.utcnow() - fb.timestamp).days < 30
            ])
            
            # Acurácia por anotador
            annotator_accuracy = {}
            for annotator_id, profile in self.annotator_profiles.items():
                accuracy_history = profile.get('accuracy_history', [])
                if accuracy_history:
                    annotator_accuracy[annotator_id] = {
                        'avg_accuracy': np.mean(accuracy_history),
                        'samples_annotated': len(accuracy_history)
                    }
            
            # Distribuição de dificuldade
            difficulty_distribution = {
                'easy': 0,
                'medium': 0,
                'hard': 0
            }
            
            for feedback in self.feedback_history:
                difficulty = feedback.difficulty_level
                if difficulty in difficulty_distribution:
                    difficulty_distribution[difficulty] += 1
            
            return {
                'total_feedback': total_feedback,
                'recent_feedback': recent_feedback,
                'active_annotators': len(self.annotator_profiles),
                'model_performance': self.performance_history[-5:] if self.performance_history else [],
                'annotator_accuracy': annotator_accuracy,
                'difficulty_distribution': difficulty_distribution,
                'retrain_recommended': await self.should_retrain_model()
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas: {str(e)}")
            return {'error': str(e)}

# Exemplo de uso
async def main():
    """Exemplo de uso do sistema de aprendizado ativo."""
    # Simular inicialização com mongodb_manager
    class MockMongoDB:
        async def get_db(self):
            return self
        
        async def find(self, query):
            return self
        
        async def to_list(self, length):
            return []
        
        async def find_one(self, query):
            return None
        
        async def insert_one(self, doc):
            return type('Result', (), {'inserted_id': 'mock_id'})()
        
        async def update_one(self, query, update, upsert=False):
            return type('Result', (), {'modified_count': 1})()
    
    mock_db = MockMongoDB()
    
    # Inicializar sistema
    active_learning = ActiveLearningSystem(mock_db)
    await active_learning.initialize()
    
    # Simular artigos para análise
    articles = [
        {
            '_id': 'article_1',
            'extracted_content': 'Escola nega matrícula para criança autista alegando falta de estrutura.',
            'source_name': 'Folha de S.Paulo',
            'publish_date': datetime.utcnow().isoformat()
        }
    ]
    
    # Identificar amostras incertas
    uncertain_samples = await active_learning.identify_uncertain_samples(articles)
    
    print(f"Amostras incertas identificadas: {len(uncertain_samples)}")
    
    if uncertain_samples:
        sample = uncertain_samples[0]
        print(f"Prioridade: {sample.priority}")
        print(f"Incerteza: {sample.uncertainty_score:.2f}")
        print(f"Revisores sugeridos: {sample.suggested_reviewers}")

if __name__ == "__main__":
    asyncio.run(main())