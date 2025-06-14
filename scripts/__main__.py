#!/usr/bin/env python3
"""
BlueMonitor Scripts Runner

Execute scripts do BlueMonitor diretamente, por exemplo:
    python -m scripts diagnostics.check_news
"""

import argparse
import importlib
import sys
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description='BlueMonitor Scripts Runner')
    parser.add_argument('script', help='Script to run (e.g., diagnostics.check_news)')
    parser.add_argument('args', nargs=argparse.REMAINDER, help='Arguments to pass to the script')
    
    args = parser.parse_args()
    
    try:
        # Importa o módulo do script
        module = importlib.import_module(f'scripts.{args.script}')
        
        # Executa a função main se existir
        if hasattr(module, 'main') and callable(module.main):
            sys.argv = [args.script] + args.args
            module.main()
        else:
            print(f"Erro: O script {args.script} não possui uma função 'main'")
            return 1
    except ImportError as e:
        print(f"Erro ao importar o script {args.script}: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
