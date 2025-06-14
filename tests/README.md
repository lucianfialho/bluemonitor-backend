# Testes do BlueMonitor

Este diretório contém os testes automatizados para o projeto BlueMonitor.

## Estrutura de Diretórios

- `/tests/api/v1/endpoints/`: Testes para os endpoints da API v1
- `/tests/conftest.py`: Configurações e fixtures do pytest

## Como Executar os Testes

### Pré-requisitos

- Python 3.9+
- Poetry (gerenciador de dependências)
- MongoDB rodando localmente (ou configurado via variáveis de ambiente)

### Instalação

1. Instale as dependências de desenvolvimento:

```bash
poetry install --with dev
```

2. Configure as variáveis de ambiente (opcional, valores padrão serão usados se não configurados):

```bash
export TEST_MONGODB_URL="mongodb://localhost:27017/test_bluemonitor"
```

### Executando os Testes

Para executar todos os testes:

```bash
poetry run pytest -v
```

Para executar testes específicos:

```bash
# Executar testes em um arquivo específico
poetry run pytest tests/api/v1/endpoints/test_news.py -v

# Executar uma classe de teste específica
poetry run pytest tests/api/v1/endpoints/test_news.py::TestGetNews -v

# Executar um teste específico
poetry run pytest tests/api/v1/endpoints/test_news.py::TestGetNews::test_get_news_success -v
```

### Opções Adicionais

- `-s`: Mostrar saída de print (útil para depuração)
- `-v`: Modo verboso
- `--cov=app`: Gerar relatório de cobertura de código
- `--cov-report=html`: Gerar relatório HTML de cobertura

Exemplo com cobertura:

```bash
poetry run pytest --cov=app --cov-report=html
```

## Escrevendo Novos Testes

1. Crie um novo arquivo de teste seguindo o padrão `test_*.py`
2. Use as fixtures disponíveis em `conftest.py`
3. Para testes assíncronos, use `pytest.mark.asyncio`
4. Mantenpo os testes pequenos e focados em um único cenário

## Boas Práticas

- Nomeie os testes de forma descritiva
- Use fixtures para setup e teardown
- Mantenha os testes independentes um do outro
- Teste casos de sucesso e falha
- Use mocks para dependências externas
