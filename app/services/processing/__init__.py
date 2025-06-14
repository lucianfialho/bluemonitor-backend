"""Módulo de processamento otimizado."""
try:
    from .batch_processor import BatchProcessor, OptimizedNewsProcessor
    from .cache_manager import CacheManager
    from .resource_monitor import ResourceMonitor
    
    __all__ = [
        'BatchProcessor',
        'OptimizedNewsProcessor',
        'CacheManager', 
        'ResourceMonitor'
    ]
except ImportError as e:
    # Se houver problemas de import, disponibilizar apenas o que funciona
    __all__ = []
    
    try:
        from .cache_manager import CacheManager
        __all__.append('CacheManager')
    except ImportError:
        pass
    
    try:
        from .resource_monitor import ResourceMonitor
        __all__.append('ResourceMonitor')
    except ImportError:
        pass
    
    try:
        from .batch_processor import BatchProcessor, OptimizedNewsProcessor
        __all__.extend(['BatchProcessor', 'OptimizedNewsProcessor'])
    except ImportError:
        pass
