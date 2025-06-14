"""
Monitor de recursos do sistema (versão simplificada).
"""
import asyncio
import logging
from datetime import datetime
from collections import deque
from typing import Dict, Any

logger = logging.getLogger(__name__)

class ResourceMonitor:
    """Monitor de recursos do sistema (versão simplificada)."""
    
    def __init__(self, check_interval: float = 1.0):
        self.check_interval = check_interval
        self.monitoring = False
        self.metrics_history = deque(maxlen=100)
    
    async def start_monitoring(self) -> None:
        """Inicia monitoramento (versão simplificada)."""
        self.monitoring = True
        while self.monitoring:
            try:
                # Tentar usar psutil se disponível
                import psutil
                metrics = {
                    'timestamp': datetime.utcnow(),
                    'memory_percent': psutil.virtual_memory().percent,
                    'memory_gb': psutil.virtual_memory().used / (1024**3),
                    'cpu_percent': psutil.cpu_percent(interval=0.1),
                    'disk_percent': psutil.disk_usage('/').percent
                }
            except ImportError:
                # Fallback simples sem psutil
                metrics = {
                    'timestamp': datetime.utcnow(),
                    'memory_percent': 50.0,  # Valor estimado
                    'memory_gb': 2.0,        # Valor estimado
                    'cpu_percent': 30.0,     # Valor estimado
                    'disk_percent': 70.0     # Valor estimado
                }
            
            self.metrics_history.append(metrics)
            await asyncio.sleep(self.check_interval)
    
    def stop_monitoring(self) -> None:
        """Para monitoramento."""
        self.monitoring = False
    
    def get_current_metrics(self) -> Dict[str, float]:
        """Obtém métricas atuais."""
        if not self.metrics_history:
            return {
                'memory_percent': 50.0,
                'memory_gb': 2.0,
                'cpu_percent': 30.0,
                'disk_percent': 70.0
            }
        return self.metrics_history[-1]
    
    def should_throttle(self, config: Any) -> bool:
        """Verifica se deve reduzir processamento."""
        current = self.get_current_metrics()
        
        memory_gb = current.get('memory_gb', 0)
        cpu_percent = current.get('cpu_percent', 0)
        
        # Usar valores padrão se config não tiver os atributos
        memory_threshold = getattr(config, 'memory_threshold_gb', 4.0)
        cpu_threshold = getattr(config, 'cpu_threshold_percent', 80.0)
        
        return (
            memory_gb > memory_threshold or 
            cpu_percent > cpu_threshold
        )
