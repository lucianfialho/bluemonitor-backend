# Melhorias na Extração de Notícias

Este documento descreve as melhorias implementadas no sistema de coleta e processamento de notícias.

## Melhorias Implementadas

1. **Extração Melhorada de Títulos**
   - Adicionada extração de título da meta tag `og:title` como fonte primária
   - Fallback para título da página HTML
   - Fallback para título da SerpAPI

2. **Adição de Descrição**
   - Extração de meta descrição (meta name="description" ou og:description)
   - Fallback para snippet da SerpAPI

3. **Favicon**
   - Extração de favicon do HTML da página
   - Suporte a URLs relativas e absolutas
   - Fallback para favicon padrão baseado no domínio

4. **Estrutura de Dados Aprimorada**
   - Novos campos: `title`, `description`, `favicon`, `domain`
   - Metadados estruturados em `metadata`
   - Melhor organização dos campos de origem

5. **Performance**
   - Índices otimizados para consultas comuns
   - Processamento em lote para migração
   - Melhor tratamento de erros

## Como Testar

1. **Rodar a migração**
   ```bash
   python -m scripts.migrate_news
   ```

2. **Criar índices**
   ```bash
   python -m scripts.create_indexes
   ```

3. **Testar a API**
   ```bash
   python -m scripts.test_news_endpoint
   ```

4. **Gerar relatório de qualidade**
   ```bash
   python -m scripts.news_quality_report --days 7
   ```
   
5. **Monitorar coleta em tempo real**
   ```bash
   # Configurar variáveis de ambiente primeiro
   export SMTP_HOST=smtp.example.com
   export SMTP_PORT=587
   export SMTP_USER=user@example.com
   export SMTP_PASSWORD=yourpassword
   export ALERT_RECIPIENTS=admin@example.com,dev@example.com
   
   # Executar monitor
   python -m scripts.monitor_news_collection
   ```
   
   Para executar como um serviço:
   ```bash
   # No Linux/macOS
   nohup python -m scripts.monitor_news_collection > monitor.log 2>&1 &
   ```

## Exemplo de Resposta da API

```json
{
  "data": [
    {
      "id": "60f8e5b5e6b3f2a9d9f8e5b5",
      "title": "Título da Notícia",
      "description": "Descrição resumida da notícia...",
      "url": "https://exemplo.com/noticia",
      "source": {
        "name": "Exemplo Notícias",
        "domain": "exemplo.com",
        "favicon": "https://exemplo.com/favicon.ico"
      },
      "published_at": "2023-07-20T14:30:00Z",
      "content": "Conteúdo completo da notícia...",
      "summary": "Resumo gerado por IA...",
      "metadata": {
        "has_image": true,
        "has_favicon": true,
        "has_description": true,
        "language": "pt-br",
        "processed_at": "2023-07-20T15:00:00Z"
      },
      "topics": ["60f8e5b5e6b3f2a9d9f8e5b6"]
    }
  ],
  "pagination": {
    "total": 100,
    "skip": 0,
    "limit": 10,
    "has_more": true
  }
}
```

## Filtros Disponíveis

- `country`: Código do país (ex: 'BR')
- `source`: Domínio da fonte (ex: 'g1.globo.com')
- `has_image`: Filtrar por notícias com imagem
- `has_favicon`: Filtrar por notícias com favicon
- `skip`: Número de itens para pular
- `limit`: Número máximo de itens por página (máx. 100)

## Monitoramento e Manutenção

### Monitoramento de Recursos

O sistema inclui vários scripts para monitorar o desempenho e o uso de recursos:

1. **Monitoramento em Tempo Real**
   - `monitor_news_collection.py`: Monitora o processo de coleta e envia alertas
   - `monitor_resources.py`: Monitora o uso de CPU, memória, disco e rede
   - `visualize_resources.py`: Gera relatórios visuais a partir dos dados coletados

2. **Relatórios de Qualidade**
   - `news_quality_report.py`: Analisa a qualidade dos dados coletados
   - Gera métricas sobre preenchimento de campos, taxas de erro, etc.

3. **Configuração de Alertas**
   - Alertas por email para problemas críticos
   - Monitoramento contínuo do sistema

### Como Usar o Monitoramento de Recursos

1. **Monitorar um Processo**
   ```bash
   # Monitorar o processo atual
   python -m scripts.monitor_resources --output metrics.jsonl
   
   # Monitorar um processo específico por PID
   python -m scripts.monitor_resources --pid 1234 --interval 0.5 --output metrics.jsonl
   ```

2. **Visualizar os Dados Coletados**
   ```bash
   python -m scripts.visualize_resources metrics.jsonl
   ```
   Isso criará um diretório `metrics_plots/` com gráficos e um relatório HTML.

3. **Monitoramento Contínuo**
   ```bash
   # Iniciar o monitoramento em segundo plano
   nohup python -m scripts.monitor_resources --output monitor/metrics_$(date +%Y%m%d_%H%M%S).jsonl > monitor.log 2>&1 &
   
   # Parar o monitoramento
   pkill -f "python -m scripts.monitor_resources"
   ```

### Métricas Coletadas

O monitor de recursos coleta as seguintes métricas:

- **Processo**
  - Uso de CPU (%)
  - Uso de memória (RSS, %)
  - Número de threads
  - Número de descritores de arquivo
  - Número de conexões de rede

- **Sistema**
  - Uso de CPU total (%)
  - Uso de memória (total, disponível, %)
  - Uso de swap
  - I/O de disco (leituras/escritas, bytes)
  - Uso de rede (bytes enviados/recebidos, taxas)

### Relatórios de Qualidade

O script `news_quality_report.py` gera relatórios detalhados sobre a qualidade dos dados coletados, incluindo:

- Métricas de preenchimento de campos (título, descrição, favicon, etc.)
- Estatísticas de comprimento do conteúdo
- Taxas de erro
- Principais fontes de notícias
- Erros recentes

### Monitoramento em Tempo Real

O script `monitor_news_collection.py` monitora continuamente o processo de coleta e envia alertas por email quando problemas são detectados:

- Baixo volume de notícias
- Alta taxa de erros
- Processamento parado
- Outros problemas na coleta

### Configuração de Alertas

Para configurar alertas por email, defina as seguintes variáveis de ambiente:

```bash
# Configurações SMTP
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=user@example.com
SMTP_PASSWORD=yourpassword

# Destinatários dos alertas (separados por vírgula)
ALERT_RECIPIENTS=admin@example.com,dev@example.com
```

## Próximos Passos

1. Implementar fallback para favicon baseado em domínio
2. Adicionar suporte a mais formatos de data
3. Melhorar a detecção de idioma
4. Adicionar cache para favicons
5. Implementar painel de monitoramento web
6. Adicionar métricas de desempenho
7. Implementar testes automatizados de qualidade
8. Adicionar suporte a notificações em outros canais (Slack, Telegram, etc.)
