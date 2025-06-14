"""Módulo de classificação avançada."""
from .advanced_classifier import AdvancedClassificationService
from .false_positive_reducer import FalsePositiveReducer
from .active_learning import ActiveLearningSystem

__all__ = [
    'AdvancedClassificationService',
    'FalsePositiveReducer', 
    'ActiveLearningSystem'
]