"""Módulo de classificação hierárquica."""
from .scalable_architecture import (
    HierarchicalClassificationSystem,
    ClassificationSystemFactory,
    DiscriminationClassifier,
    ViolenceClassifier
)

__all__ = [
    'HierarchicalClassificationSystem',
    'ClassificationSystemFactory', 
    'DiscriminationClassifier',
    'ViolenceClassifier'
]