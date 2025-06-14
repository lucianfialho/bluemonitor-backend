"""Script para instalar a CLI do BlueMonitor como um comando global."""
import os
import sys
import shutil
import platform
from pathlib import Path

def create_launcher_script(install_dir: str, python_path: str) -> str:
    """Cria um script de inicialização para a CLI.
    
    Args:
        install_dir: Diretório de instalação
        python_path: Caminho para o executável do Python
        
    Returns:
        Caminho para o script criado
    """
    script_content = f"""#!/bin/sh
# BlueMonitor CLI wrapper
"{python_path}" -m scripts.bluemonitor_cli "$@"
"""
    
    script_path = os.path.join(install_dir, 'bmon')
    
    with open(script_path, 'w') as f:
        f.write(script_content)
    
    # Tornar o script executável
    os.chmod(script_path, 0o755)
    
    return script_path

def install_windows(install_dir: str, python_path: str) -> bool:
    """Instala a CLI no Windows.
    
    Args:
        install_dir: Diretório de instalação
        python_path: Caminho para o executável do Python
        
    Returns:
        True se a instalação for bem-sucedida, False caso contrário
    """
    try:
        # Criar diretório de instalação se não existir
        os.makedirs(install_dir, exist_ok=True)
        
        # Criar arquivo batch
        batch_content = f"""@echo off
"{python_path}" -m scripts.bluemonitor_cli %*
"""
        
        batch_path = os.path.join(install_dir, 'bmon.bat')
        
        with open(batch_path, 'w') as f:
            f.write(batch_content)
        
        # Adicionar ao PATH se não estiver
        add_to_path = input(f"Deseja adicionar {install_dir} ao PATH? [S/n] ").strip().lower()
        
        if not add_to_path or add_to_path == 's':
            # Adicionar ao PATH do usuário
            import winreg
            
            # Abrir a chave de variáveis de ambiente do usuário
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                'Environment',
                0,
                winreg.KEY_READ | winreg.KEY_SET_VALUE
            )
            
            # Obter o valor atual do PATH
            try:
                path_value = winreg.QueryValueEx(key, 'Path')[0]
            except WindowsError:
                path_value = ''
            
            # Adicionar o diretório ao PATH se ainda não estiver lá
            if install_dir not in path_value.split(os.pathsep):
                new_path = f"{path_value}{os.pathsep}{install_dir}" if path_value else install_dir
                winreg.SetValueEx(key, 'Path', 0, winreg.REG_EXPAND_SZ, new_path)
                print(f"\n{install_dir} adicionado ao PATH. Você precisará reiniciar o terminal para que as alterações tenham efeito.")
            
            winreg.CloseKey(key)
        
        print(f"\nInstalação concluída! Use o comando 'bmon' em qualquer lugar para acessar a CLI.")
        return True
        
    except Exception as e:
        print(f"Erro durante a instalação: {str(e)}")
        return False

def install_unix(install_dir: str, python_path: str) -> bool:
    """Instala a CLI em sistemas Unix-like (Linux, macOS).
    
    Args:
        install_dir: Diretório de instalação
        python_path: Caminho para o executável do Python
        
    Returns:
        True se a instalação for bem-sucedida, False caso contrário
    """
    try:
        # Criar diretório de instalação se não existir
        os.makedirs(install_dir, exist_ok=True)
        
        # Criar script de inicialização
        script_path = create_launcher_script(install_dir, python_path)
        
        # Criar link simbólico em /usr/local/bin se possível
        try:
            symlink_path = "/usr/local/bin/bmon"
            if os.path.exists(symlink_path):
                os.remove(symlink_path)
            
            os.symlink(script_path, symlink_path)
            print(f"Link simbólico criado em {symlink_path}")
        except PermissionError:
            # Se não tiver permissão para /usr/local/bin, tentar ~/.local/bin
            local_bin = os.path.expanduser("~/.local/bin")
            os.makedirs(local_bin, exist_ok=True)
            
            symlink_path = os.path.join(local_bin, 'bmon')
            if os.path.lexists(symlink_path):
                os.remove(symlink_path)
            
            os.symlink(script_path, symlink_path)
            
            # Verificar se ~/.local/bin está no PATH
            if local_bin not in os.environ.get('PATH', '').split(':'):
                print(f"\nAdicione {local_bin} ao seu PATH adicionando a seguinte linha ao seu ~/.bashrc, ~/.zshrc ou ~/.profile:")
                print(f"\n    export PATH=\"$HOME/.local/bin:$PATH\"")
                print("\nDepois execute 'source ~/.bashrc' (ou o arquivo correspondente ao seu shell).")
        
        print(f"\nInstalação concluída! Use o comando 'bmon' em qualquer lugar para acessar a CLI.")
        return True
        
    except Exception as e:
        print(f"Erro durante a instalação: {str(e)}")
        return False

def main():
    """Função principal de instalação."""
    print("""
╔══════════════════════════════════════════╗
║        Instalador BlueMonitor CLI        ║
╚══════════════════════════════════════════╝
""")
    
    # Verificar se estamos no diretório correto
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    
    if not os.path.exists(os.path.join(project_root, 'app')) or not os.path.exists(os.path.join(project_root, 'scripts')):
        print("Erro: Este script deve ser executado a partir do diretório raiz do projeto BlueMonitor.")
        return 1
    
    # Obter o caminho para o Python atual
    python_path = sys.executable
    
    if not python_path:
        print("Erro: Não foi possível determinar o caminho para o Python.")
        return 1
    
    print(f"\nPython detectado: {python_path}")
    
    # Determinar o diretório de instalação com base no sistema operacional
    if platform.system() == 'Windows':
        install_dir = os.path.join(os.environ.get('APPDATA', ''), 'BlueMonitor', 'bin')
        success = install_windows(install_dir, python_path)
    else:
        # Unix-like (Linux, macOS)
        install_dir = "/usr/local/opt/blue-monitor/bin"
        
        # Verificar se temos permissão para /usr/local/opt
        if not os.access(os.path.dirname(os.path.dirname(install_dir)), os.W_OK):
            # Se não tivermos permissão, instalar no diretório do usuário
            install_dir = os.path.expanduser("~/.local/opt/blue-monitor/bin")
        
        success = install_unix(install_dir, python_path)
    
    if success:
        print("\n✅ Instalação concluída com sucesso!")
        print("\nComo usar:")
        print("  bmon run         - Iniciar todos os serviços")
        print("  bmon status      - Verificar status dos serviços")
        print("  bmon --help      - Ver todos os comandos disponíveis")
        print("\nDocumentação completa em: https://github.com/seu-usuario/bluemonitor")
        return 0
    else:
        print("\n❌ Falha na instalação. Consulte as mensagens de erro acima.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
