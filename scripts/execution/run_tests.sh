#!/bin/bash

# Script para executar testes do BlueMonitor

# Cores para saída
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Iniciando testes do BlueMonitor...${NC}"

# Verifica se o Poetry está instalado
if ! command -v poetry &> /dev/null; then
    echo -e "${RED}Erro: Poetry não encontrado. Por favor, instale o Poetry primeiro.${NC}"
    echo "Visite: https://python-poetry.org/docs/#installation"
    exit 1
fi

# Instala dependências se necessário
echo -e "\n${YELLOW}Instalando/atualizando dependências...${NC}"
poetry install --with dev

# Configura variáveis de ambiente
export $(grep -v '^#' .env.test | xargs)

# Verifica se o MongoDB está rodando
if ! nc -z localhost 27017 &> /dev/null; then
    echo -e "\n${YELLOW}Aviso: MongoDB não está rodando na porta 27017. Certifique-se de que o MongoDB está instalado e em execução.${NC}"
    read -p "Deseja tentar iniciar o MongoDB via Docker? (s/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Ss]$ ]]; then
        if ! command -v docker &> /dev/null; then
            echo -e "${RED}Erro: Docker não encontrado. Por favor, instale o Docker primeiro.${NC}"
            exit 1
        fi
        echo -e "\n${YELLOW}Iniciando MongoDB via Docker...${NC}"
        docker run -d -p 27017:27017 --name test-mongodb mongo:latest
        if [ $? -ne 0 ]; then
            echo -e "${RED}Erro ao iniciar o MongoDB via Docker.${NC}"
            exit 1
        fi
        # Aguarda o MongoDB iniciar
        sleep 5
    else
        echo -e "${RED}Testes interrompidos.${NC}"
        exit 1
    fi
fi

# Executa os testes
echo -e "\n${YELLOW}Executando testes...${NC}"
poetry run pytest -v --cov=app --cov-report=term-missing:skip-covered --cov-report=html
TEST_RESULT=$?

# Limpeza (se o MongoDB foi iniciado via Docker)
if [ -n "$(docker ps -q -f name=test-mongodb)" ]; then
    echo -e "\n${YELLOW}Parando e removendo container do MongoDB...${NC}"
    docker stop test-mongodb > /dev/null
    docker rm test-mongodb > /dev/null
fi

# Resultado final
if [ $TEST_RESULT -eq 0 ]; then
    echo -e "\n${GREEN}Todos os testes passaram com sucesso! 🎉${NC}"
    echo -e "Relatório de cobertura disponível em: file://$(pwd)/htmlcov/index.html"
    exit 0
else
    echo -e "\n${RED}Alguns testes falharam.${NC}"
    exit $TEST_RESULT
fi
