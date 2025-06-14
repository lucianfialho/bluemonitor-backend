"""Módulo de processamento otimizado."""
from .batch_processor import BatchProcessor, OptimizedNewsProcessor
from .cache_manager import CacheManager
from .resource_monitor import ResourceMonitor

__all__ = [
    'BatchProcessor',
    'OptimizedNewsProcessor',
    'CacheManager', 
    'ResourceMonitor'
]