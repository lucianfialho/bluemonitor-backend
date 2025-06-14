#!/usr/bin/env python3
"""
BlueMonitor - Ponto de entrada principal da aplicação.

Este script gerencia a inicialização de todos os serviços do BlueMonitor,
incluindo a API, coletor de notícias e monitoramento.
"""
import os
import sys
import logging
from pathlib import Path

# Configuração básica de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/startup.log')
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Ponto de entrada principal da aplicação."""
    try:
        # Verificar se estamos no diretório correto
        if not (Path('app') / 'main.py').exists():
            logger.error("Erro: Execute o script a partir do diretório raiz do projeto.")
            return 1
        
        # Criar diretórios necessários
        os.makedirs('logs', exist_ok=True)
        os.makedirs('data', exist_ok=True)
        os.makedirs('monitor', exist_ok=True)
        
        # Importar e executar o gerenciador de inicialização
        from scripts.startup import StartupManager
        
        manager = StartupManager()
        manager.start_all()
        
        logger.info("BlueMonitor iniciado com sucesso! Pressione Ctrl+C para parar.")
        
        # Manter o script em execução
        while True:
            try:
                import time
                time.sleep(1)
            except KeyboardInterrupt:
                logger.info("\nEncerrando BlueMonitor...")
                break
        
        return 0
        
    except Exception as e:
        logger.exception("Erro ao iniciar o BlueMonitor")
        return 1
    finally:
        # Garantir que todos os processos sejam parados
        if 'manager' in locals():
            manager.stop_all()

if __name__ == "__main__":
    sys.exit(main())
