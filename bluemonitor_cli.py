"""BlueMonitor CLI - Ferramenta de linha de comando para gerenciar o BlueMonitor."""
import os
import sys
import time
import signal
import logging
import argparse
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# Importar configurações
from .config import Colors, get_config

# Inicializar configuração
config = get_config()

# Configuração de logging
log_format = config.get('logging.format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log_level = getattr(logging, config.get('logging.level', 'INFO'))

logging.basicConfig(
    level=log_level,
    format=log_format,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(config.get('paths.logs', 'logs') + '/bluemonitor_cli.log')
    ]
)
logger = logging.getLogger(__name__)

# Configurações dos processos
PROJECT_ROOT = str(Path(__file__).parent.parent)

# Construir configuração dos processos com base no arquivo de configuração
PROCESSES: Dict[str, Dict[str, Any]] = {
    'api': {
        'cmd': [
            'uvicorn', 'app.main:app',
            '--host', config.get('api.host', '0.0.0.0'),
            '--port', str(config.get('api.port', 8000)),
            '--reload' if config.get('api.reload', True) else '',
            '--workers', str(config.get('api.workers', 1)),
            '--log-level', config.get('api.log_level', 'info')
        ],
        'cwd': PROJECT_ROOT,
        'env': {**os.environ, 'PYTHONPATH': PROJECT_ROOT},
        'log': 'api.log',
        'pid': None,
        'process': None,
        'enabled': True
    },
    'collector': {
        'cmd': [
            'python', '-m', 'scripts.monitor_news_collection',
            '--interval', str(config.get('collector.interval', 3600))
        ],
        'cwd': PROJECT_ROOT,
        'env': {**os.environ, 'PYTHONPATH': PROJECT_ROOT},
        'log': 'collector.log',
        'pid': None,
        'process': None,
        'enabled': config.get('collector.enabled', True)
    },
    'monitor': {
        'cmd': [
            'python', '-m', 'scripts.monitor_resources',
            '--output', os.path.join(
                config.get('paths.monitor', 'monitor'),
                f'metrics_{int(time.time())}.jsonl'
            ),
            '--interval', str(config.get('monitor.interval', 60))
        ],
        'cwd': PROJECT_ROOT,
        'env': os.environ.copy(),
        'log': 'monitor.log',
        'pid': None,
        'process': None,
        'enabled': config.get('monitor.enabled', True)
    }
}

# Filtrar processos desabilitados
PROCESSES = {k: v for k, v in PROCESSES.items() if v.get('enabled', True)}

class BlueMonitorCLI:
    """Interface de linha de comando para gerenciar o BlueMonitor."""
    
    def __init__(self):
        """Inicializa a CLI."""
        self.running = True
        self.processes = {}
        self.setup_signal_handlers()
    
    def setup_signal_handlers(self):
        """Configura os manipuladores de sinal para desligamento gracioso."""
        signal.signal(signal.SIGINT, self.handle_exit)
        signal.signal(signal.SIGTERM, self.handle_exit)
    
    def handle_exit(self, signum, frame):
        """Lida com sinais de desligamento."""
        print(f"\n{Colors.WARNING}Recebido sinal de desligamento. Encerrando processos...{Colors.ENDC}")
        self.running = False
        self.stop_all()
        sys.exit(0)
    
    def start_process(self, name: str) -> bool:
        """Inicia um processo.
        
        Args:
            name: Nome do processo para iniciar.
            
        Returns:
            bool: True se o processo foi iniciado com sucesso, False caso contrário.
        """
        if name not in PROCESSES:
            logger.error(f"Processo desconhecido: {name}")
            return False
        
        proc_info = PROCESSES[name]
        
        # Verificar se o processo já está em execução
        if self.is_process_running(proc_info.get('pid')):
            logger.warning(f"{name} já está em execução (PID: {proc_info['pid']})")
            return True
        
        try:
            # Criar diretório de logs se não existir
            os.makedirs('logs', exist_ok=True)
            os.makedirs('monitor', exist_ok=True)
            
            # Configurar redirecionamento de saída
            with open(f"logs/{proc_info['log']}", 'a') as log_file:
                process = subprocess.Popen(
                    proc_info['cmd'],
                    cwd=proc_info['cwd'],
                    env=proc_info['env'],
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    start_new_session=True
                )
            
            proc_info['pid'] = process.pid
            proc_info['process'] = process
            
            logger.info(f"{name} iniciado com PID {process.pid}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao iniciar {name}: {str(e)}", exc_info=True)
            return False
    
    def stop_process(self, name: str) -> bool:
        """Para um processo em execução.
        
        Args:
            name: Nome do processo para parar.
            
        Returns:
            bool: True se o processo foi parado com sucesso, False caso contrário.
        """
        if name not in PROCESSES:
            logger.error(f"Processo desconhecido: {name}")
            return False
        
        proc_info = PROCESSES[name]
        
        if not proc_info['pid'] or not self.is_process_running(proc_info['pid']):
            logger.warning(f"{name} não está em execução")
            return True
        
        try:
            # Enviar sinal SIGTERM
            proc = proc_info['process']
            if proc:
                proc.terminate()
                
                # Esperar até que o processo termine (timeout de 10 segundos)
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    logger.warning(f"Tempo limite esgotado ao encerrar {name}. Forçando encerramento...")
                    proc.kill()
                    proc.wait()
            
            logger.info(f"{name} (PID: {proc_info['pid']}) encerrado")
            proc_info['pid'] = None
            proc_info['process'] = None
            return True
            
        except Exception as e:
            logger.error(f"Erro ao parar {name}: {str(e)}", exc_info=True)
            return False
    
    def is_process_running(self, pid: Optional[int]) -> bool:
        """Verifica se um processo está em execução.
        
        Args:
            pid: ID do processo a ser verificado.
            
        Returns:
            bool: True se o processo estiver em execução, False caso contrário.
        """
        if not pid:
            return False
            
        try:
            # Verificar se o processo existe enviando sinal 0
            os.kill(pid, 0)
            return True
        except (ProcessLookupError, PermissionError):
            return False
    
    def start_all(self):
        """Inicia todos os processos do BlueMonitor."""
        print(f"{Colors.HEADER}Iniciando BlueMonitor...{Colors.ENDC}")
        
        # Iniciar processos em ordem
        for name in ['api', 'monitor', 'collector']:
            if self.start_process(name):
                print(f"{Colors.OKGREEN}✓{Colors.ENDC} {name} iniciado")
            else:
                print(f"{Colors.FAIL}✗{Colors.ENDC} Falha ao iniciar {name}")
        
        print(f"\n{Colors.OKGREEN}BlueMonitor iniciado com sucesso!{Colors.ENDC}")
        print(f"API disponível em: {Colors.OKBLUE}http://localhost:8000{Colors.ENDC}")
        print(f"Documentação da API: {Colors.OKBLUE}http://localhost:8000/docs{Colors.ENDC}")
        print(f"\nPressione Ctrl+C para parar")
        
        # Manter o script em execução
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.handle_exit(signal.SIGINT, None)
    
    def stop_all(self):
        """Para todos os processos do BlueMonitor."""
        print(f"\n{Colors.HEADER}Parando BlueMonitor...{Colors.ENDC}")
        
        # Parar processos em ordem reversa
        for name in reversed(['collector', 'monitor', 'api']):
            if self.stop_process(name):
                print(f"{Colors.OKGREEN}✓{Colors.ENDC} {name} parado")
            else:
                print(f"{Colors.FAIL}✗{Colors.ENDC} Falha ao parar {name}")
        
        print(f"{Colors.OKGREEN}Todos os processos foram encerrados.{Colors.ENDC}")
    
    def status(self):
        """Exibe o status de todos os processos."""
        print(f"{Colors.HEADER}Status do BlueMonitor{Colors.ENDC}")
        print("-" * 50)
        
        for name, proc_info in PROCESSES.items():
            pid = proc_info.get('pid')
            is_running = self.is_process_running(pid)
            
            status = f"{Colors.OKGREEN}●{Colors.ENDC} Em execução (PID: {pid})" if is_running else f"{Colors.FAIL}○{Colors.ENDC} Parado"
            print(f"{name:10} {status}")
        
        print("\nLegenda:")
        print(f"  {Colors.OKGREEN}●{Colors.ENDC} Em execução")
        print(f"  {Colors.FAIL}○{Colors.ENDC} Parado")
    
    def restart(self, name: str = None):
        """Reinicia um ou todos os processos.
        
        Args:
            name: Nome do processo para reiniciar. Se None, reinicia todos.
        """
        if name:
            if name not in PROCESSES:
                print(f"{Colors.FAIL}Processo desconhecido: {name}{Colors.ENDC}")
                return
            
            print(f"Reiniciando {name}...")
            self.stop_process(name)
            self.start_process(name)
        else:
            print(f"Reiniciando todos os processos...")
            self.stop_all()
            self.start_all()

def main():
    """Função principal da CLI."""
    parser = argparse.ArgumentParser(description='CLI para gerenciar o BlueMonitor')
    subparsers = parser.add_subparsers(dest='command', help='Comando')
    
    # Comando: start
    start_parser = subparsers.add_parser('start', help='Iniciar serviços')
    start_parser.add_argument('service', nargs='?', choices=list(PROCESSES.keys()) + ['all'], 
                             default='all', help='Serviço para iniciar (padrão: todos)')
    
    # Comando: stop
    stop_parser = subparsers.add_parser('stop', help='Parar serviços')
    stop_parser.add_argument('service', nargs='?', choices=list(PROCESSES.keys()) + ['all'], 
                            default='all', help='Serviço para parar (padrão: todos)')
    
    # Comando: restart
    restart_parser = subparsers.add_parser('restart', help='Reiniciar serviços')
    restart_parser.add_argument('service', nargs='?', choices=list(PROCESSES.keys()) + ['all'], 
                               default='all', help='Serviço para reiniciar (padrão: todos)')
    
    # Comando: status
    subparsers.add_parser('status', help='Verificar status dos serviços')
    
    # Comando: run (inicia tudo e monitora)
    subparsers.add_parser('run', help='Iniciar todos os serviços e monitorar')
    
    # Se nenhum argumento for fornecido, mostrar ajuda
    if len(sys.argv) == 1:
        parser.print_help()
        return
    
    args = parser.parse_args()
    cli = BlueMonitorCLI()
    
    try:
        if args.command == 'start':
            if args.service == 'all':
                cli.start_all()
            else:
                if cli.start_process(args.service):
                    print(f"{Colors.OKGREEN}{args.service} iniciado com sucesso!{Colors.ENDC}")
                else:
                    print(f"{Colors.FAIL}Falha ao iniciar {args.service}{Colors.ENDC}")
        
        elif args.command == 'stop':
            if args.service == 'all':
                cli.stop_all()
            else:
                if cli.stop_process(args.service):
                    print(f"{Colors.OKGREEN}{args.service} parado com sucesso!{Colors.ENDC}")
                else:
                    print(f"{Colors.FAIL}Falha ao parar {args.service}{Colors.ENDC}")
        
        elif args.command == 'restart':
            if args.service == 'all':
                cli.restart()
            else:
                cli.restart(args.service)
        
        elif args.command == 'status':
            cli.status()
        
        elif args.command == 'run':
            cli.start_all()
        
    except KeyboardInterrupt:
        cli.handle_exit(signal.SIGINT, None)
    except Exception as e:
        logger.error(f"Erro: {str(e)}", exc_info=True)
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
