# BlueMonitor

Plataforma para monitoramento e análise de notícias relacionadas ao autismo no Brasil.

## Visão Geral

O BlueMonitor é uma ferramenta poderosa para coletar, classificar e analisar notícias relacionadas ao autismo, com foco especial em violência, direitos e legislação.

## Tecnologias

- **Backend**: Python 3.11+
- **Banco de Dados**: MongoDB
- **Cache**: Redis
- **Processamento Assíncrono**: FastAPI, Celery
- **Análise de Texto**: spaCy, NLTK
- **Machine Learning**: scikit-learn, TensorFlow

## Como Usar

1. **Pré-requisitos**
   - Python 3.11 ou superior
   - MongoDB rodando localmente ou acesso a uma instância remota
   - Redis para cache e filas

2. **Configuração**
   ```bash
   # Clone o repositório
   git clone https://github.com/seu-usuario/bluemonitor.git
   cd bluemonitor
   
   # Instale as dependências
   pip install -r requirements.txt
   
   # Configure as variáveis de ambiente
   cp .env.example .env
   # Edite o .env com suas configurações
   ```

3. **Executando**
   ```bash
   # Iniciar o servidor web
   uvicorn app.main:app --reload
   
   # Iniciar o worker do Celery
   celery -A app.worker worker --loglevel=info
   ```

## Estrutura do Projeto

```
bluemonitor/
├── app/                    # Código-fonte da aplicação
│   ├── api/                # Rotas da API
│   ├── core/               # Configurações e utilitários
│   ├── models/             # Modelos de dados
│   ├── services/           # Lógica de negócios
│   └── tasks/              # Tarefas agendadas
├── config/                 # Arquivos de configuração
├── scripts/                # Scripts úteis
├── tests/                  # Testes automatizados
├── .env.example           # Exemplo de variáveis de ambiente
├── .gitignore
├── docker-compose.yml      # Configuração do Docker
├── Dockerfile             # Definição da imagem Docker
└── requirements.txt       # Dependências do projeto
```

## Contribuição

1. Faça um fork do projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Faça o push da branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## Licença

Distribuído sob a licença MIT. Veja `LICENSE` para mais informações.

## Contato

Seu Nome - [@seu_twitter](https://twitter.com/seu_twitter) - seu.email@exemplo.com

Link do Projeto: [https://github.com/seu-usuario/bluemonitor](https://github.com/seu-usuario/bluemonitor)

Veja o arquivo `config/.env.example` para um exemplo completo de configuração.

## Recursos

- **Coleta Automática**: Coleta de notícias de múltiplas fontes usando SerpAPI
- **Processamento Avançado**: Extração de conteúdo, títulos, descrições e favicons
- **IA Poderosa**: Agrupamento de tópicos e sumarização com IA
- **Análise de Sentimento**: Identificação do tom das notícias
- **API RESTful**: Interface para integração com frontend e outros serviços
- **Monitoramento em Tempo Real**: Acompanhamento de desempenho e recursos
- **CLI Integrada**: Interface de linha de comando para gerenciamento
- **Scripts de Utilidade**: Ferramentas para manutenção e diagnóstico

## 🛠️ Stack Tecnológica

### Backend
- Python 3.11+
- FastAPI
- MongoDB

### Scripts de Utilidade

#### Verificação de Ambiente

O script `check_environment.py` verifica se o ambiente está configurado corretamente:

```bash
# Executar verificação de ambiente
./check_environment.py

# Opções adicionais
./check_environment.py --verbose  # Mostrar mais detalhes
./check_environment.py --fix      # Tentar corrigir problemas automaticamente
```

O que é verificado:
- Conexão com o MongoDB
- Conexão com o Redis
- Acesso à API do SerpAPI
- Permissões de arquivo e diretório
- Variáveis de ambiente obrigatórias

#### Outros Scripts Úteis

O projeto inclui vários scripts para auxiliar no desenvolvimento e manutenção:

```bash
# Executar um script específico
python -m scripts diagnostics.check_news
python -m scripts diagnostics.check_topics
python -m scripts diagnostics.count_news

# Executar o coletor de notícias
python run_news_collector.py

# Executar o agrupamento de tópicos
python run_clustering.py

# Executar os testes
./run_tests.sh

# Instalar a CLI
python install_cli.py
```

#### Estrutura de Pastas dos Scripts

- `scripts/diagnostics/`: Scripts para diagnóstico e verificação do sistema
- `scripts/maintenance/`: Scripts para manutenção do banco de dados
- `scripts/migrations/`: Scripts de migração de dados
- SerpAPI
- Hugging Face Transformers

### Monitoramento
- psutil para métricas do sistema
- Matplotlib para visualização
- Logging avançado

### Infraestrutura
- Docker e Docker Compose
- Monitoramento de recursos em tempo real
- Alertas automáticos

## 🧪 Testes

O BlueMonitor possui uma suíte abrangente de testes para garantir a qualidade e estabilidade do código.

### Executando os Testes

1. **Pré-requisitos**:
   - Python 3.9+
   - MongoDB rodando localmente (ou Docker para executar um container de teste)
   - Poetry instalado

2. **Instale as dependências de desenvolvimento**:
   ```bash
   poetry install --with dev
   ```

3. **Execute os testes** com o script de conveniência:
   ```bash
   ./scripts/run_tests.sh
   ```
   
   Ou execute diretamente com o pytest:
   ```bash
   poetry run pytest -v
   ```

4. **Gere relatório de cobertura**:
   ```bash
   poetry run pytest --cov=app --cov-report=html
   ```
   O relatório estará disponível em `htmlcov/index.html`.

### Tipos de Testes

- **Testes de Unidade**: Testam componentes individuais em isolamento
- **Testes de Integração**: Verificam a interação entre componentes
- **Testes de API**: Validam os endpoints da API

Consulte o [guia de testes](tests/README.md) para mais detalhes.

## 🚀 Primeiros Passos

### Instalação Rápida

1. Clone o repositório:
   ```bash
   git clone https://github.com/seu-usuario/bluemonitor.git
   cd bluemonitor
   ```

2. Instale a CLI do BlueMonitor:
   ```bash
   python -m scripts.install_cli
   ```
   
   Siga as instruções na tela para completar a instalação.

3. Inicie todos os serviços:
   ```bash
   bmon run
   ```

### Usando a CLI

A CLI do BlueMonitor oferece comandos fáceis para gerenciar todos os serviços:

```bash
# Iniciar todos os serviços
bmon run

# Verificar status dos serviços
bmon status

# Iniciar/parar/reiniciar serviços específicos
bmon start api
bmon stop collector
bmon restart monitor
```

Para ver todos os comandos disponíveis:
```bash
bmon --help
```

## 📊 Monitoramento Avançado

O BlueMonitor oferece um sistema de monitoramento abrangente para acompanhar o desempenho e a saúde do sistema em tempo real.

### Monitoramento em Tempo Real

#### Usando a CLI
```bash
# Iniciar monitoramento de recursos
bmon monitor start

# Visualizar métricas em tempo real
bmon metrics

# Gerar relatório de desempenho
bmon report --format html
```

#### Monitoramento de Recursos
O sistema coleta e exibe métricas detalhadas:
- **Uso de CPU e memória** por processo
- **Uso de disco** e operações de I/O
- **Uso de rede** e conexões ativas
- **Status dos serviços** e tempo de atividade

#### Dashboard de Monitoramento
Acesse o dashboard web para visualização avançada:
```bash
bmon dashboard
```

### Alertas e Notificações
Configure alertas personalizados para:
- Uso de recursos acima dos limites
- Serviços inativos
- Erros e exceções
- Qualidade das notícias coletadas

### Relatórios de Qualidade
```bash
# Relatório de qualidade das notícias
bmon quality-report --days 7 --output report.html

# Análise de sentimento
bmon sentiment-analysis --period month
```

### Logs e Depuração
```bash
# Visualizar logs em tempo real
bmon logs --follow

# Filtrar logs por nível
bmon logs --level error

# Depurar problemas específicos
bmon debug --service collector
```

### Monitoramento Personalizado
Adicione suas próprias métricas personalizadas:
```python
from app.monitoring import monitor

@monitor.timer('meu_servico.tempo_execucao')
def minha_funcao():
    # Código a ser monitorado
    pass
```

### Integração com Ferramentas Externas
- Exporte métricas para Prometheus
- Envie alertas para Slack/Email/Webhook
- Integre com ferramentas de monitoramento externas

### Monitoramento de Saúde da API
```bash
# Verificar saúde da API
curl http://localhost:8000/health

# Métricas no formato Prometheus
curl http://localhost:8000/metrics
```

## 📚 Documentação

- [Documentação da API](http://localhost:8000/docs) (disponível com o serviço em execução)
- [Guia da CLI](CLI_README.md)
- [Melhorias Recentes](NEWS_ENHANCEMENTS.md)

## Getting Started

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and configure your environment variables
4. Run the application: `uvicorn app.main:app --reload`

## 🗂️ Estrutura do Projeto

```
bluemonitor/
├── app/                    # Código-fonte da aplicação
│   ├── api/               # Rotas e endpoints da API
│   ├── core/              # Configurações e utilitários
│   ├── models/            # Modelos de dados
│   ├── schemas/           # Esquemas Pydantic
│   └── services/          # Lógica de negócios
├── scripts/               # Scripts de utilidade
│   ├── diagnostics/       # Scripts de diagnóstico
│   │   ├── check_*.py    # Scripts de verificação
│   │   ├── monitor_*.py  # Monitoramento de recursos
│   │   └── test_*.py     # Testes específicos
│   │
│   ├── maintenance/       # Scripts de manutenção
│   │   ├── add_indexes.py    # Gerenciamento de índices
│   │   ├── clear_database.py # Limpeza do banco
│   │   └── fix_*.py         # Correções específicas
│   │
│   └── migrations/        # Scripts de migração de dados
│       └── migrate_*.py      # Migrações de esquema/dados
│
├── logs/                     # Logs da aplicação
├── monitor/                   # Dados de monitoramento
├── tests/                     # Testes automatizados
│
├── .env                   # Variáveis de ambiente
├── .env.example           # Exemplo de variáveis de ambiente
├── .gitignore
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
├── README.md
├── CLI_README.md             # Documentação da CLI
└── NEWS_ENHANCEMENTS.md      # Melhorias recentes
```

## 🛠️ Desenvolvimento

### Pré-requisitos

- Python 3.11+
- MongoDB (ou Docker)
- Poetry (gerenciador de dependências)
- Git

### Configuração do Ambiente

1. Instale o Poetry (se ainda não tiver):
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

2. Clone o repositório e instale as dependências:
   ```bash
   git clone https://github.com/seu-usuario/bluemonitor.git
   cd bluemonitor
   poetry install
   ```

3. Configure os hooks do pre-commit:
   ```bash
   poetry run pre-commit install
   ```

4. Configure as variáveis de ambiente:
   ```bash
   cp .env.example .env
   # Edite o arquivo .env com suas configurações
   ```

### Executando Localmente

#### Usando Docker (Recomendado)
```bash
# Iniciar MongoDB e outros serviços
docker-compose up -d

# Iniciar a aplicação com a CLI
bmon run
```

#### Sem Docker
```bash
# Iniciar MongoDB localmente
# Certifique-se de ter o MongoDB instalado e em execução

# Iniciar a aplicação
uvicorn app.main:app --reload
```

### Documentação da API

Com a aplicação em execução, acesse:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🧪 Testes

```bash
# Executar todos os testes
pytest

# Executar testes com cobertura
pytest --cov=app --cov-report=html
```

## 🐛 Depuração

Para depuração, você pode usar o modo debug:
```bash
# Iniciar em modo debug
python -m debugpy --listen 0.0.0.0:5678 -m uvicorn app.main:app --reload
```

## 📦 Implantação

### Docker
```bash
# Construir a imagem
docker-compose build

# Iniciar todos os serviços
docker-compose up -d
```

### Implantação em Produção
1. Configure um servidor web (Nginx/Apache) como proxy reverso
2. Use o Gunicorn como servidor ASGI:
   ```bash
   gunicorn -k uvicorn.workers.UvicornWorker app.main:app --workers 4 --bind 0.0.0.0:8000
   ```
3. Configure um processo manager como Systemd ou Supervisor

## 🤝 Contribuição

1. Faça um fork do projeto
2. Crie uma branch para sua feature (`git checkout -b feature/awesome-feature`)
3. Commit suas alterações (`git commit -am 'Add some awesome feature'`)
4. Push para a branch (`git push origin feature/awesome-feature`)
5. Abra um Pull Request

## 📄 Licença

Este projeto está licenciado sob a licença MIT - veja o arquivo [LICENSE](LICENSE) para mais detalhes.

---

Desenvolvido com ❤️ pela equipe BlueMonitor

## Testing

```bash
# Run tests
pytest

# Run tests with coverage
pytest --cov=app --cov-report=term-missing
```

## Deployment

### Docker

Build and run the application using Docker Compose:

```bash
docker-compose up --build
```

### Production

For production deployments, you'll want to:

1. Set `ENVIRONMENT=production` in your `.env` file
2. Configure proper CORS settings
3. Set up a reverse proxy (Nginx, Traefik, etc.)
4. Configure HTTPS
5. Set up monitoring and logging

## License

MIT
