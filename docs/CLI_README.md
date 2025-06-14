# BlueMonitor CLI

Interface de linha de comando para gerenciar os serviços do BlueMonitor.

## Visão Geral

A CLI do BlueMonitor fornece uma maneira fácil de gerenciar todos os componentes do sistema, incluindo a API, coletor de notícias e monitoramento de recursos.

## Instalação

1. Certifique-se de que todas as dependências estejam instaladas:
   ```bash
   pip install -r requirements.txt
   ```

2. Torne o script executável (opcional):
   ```bash
   chmod +x scripts/bluemonitor_cli.py
   ```

3. Crie um alias para facilitar o uso (opcional):
   ```bash
   alias bmon="python -m scripts.bluemonitor_cli"
   ```

## Uso Básico

### Iniciar todos os serviços
```bash
python -m scripts.bluemonitor_cli run
```

### Comandos Disponíveis

#### Iniciar serviços
```bash
# Iniciar todos os serviços
python -m scripts.bluemonitor_cli start

# Iniciar um serviço específico
python -m scripts.bluemonitor_cli start api
python -m scripts.bluemonitor_cli start collector
python -m scripts.bluemonitor_cli start monitor
```

#### Parar serviços
```bash
# Parar todos os serviços
python -m scripts.bluemonitor_cli stop

# Parar um serviço específico
python -m scripts.bluemonitor_cli stop api
```

#### Reiniciar serviços
```bash
# Reiniciar todos os serviços
python -m scripts.bluemonitor_cli restart

# Reiniciar um serviço específico
python -m scripts.bluemonitor_cli restart collector
```

#### Verificar status
```bash
python -m scripts.bluemonitor_cli status
```

## Serviços Gerenciados

1. **API**
   - Inicia o servidor FastAPI
   - Padrão: http://localhost:8000
   - Documentação: http://localhost:8000/docs

2. **Collector**
   - Coleta notícias periodicamente
   - Armazena no banco de dados
   - Processa e categoriza o conteúdo

3. **Monitor**
   - Monitora o uso de recursos do sistema
   - Coleta métricas de CPU, memória, disco e rede
   - Gera relatórios detalhados

## Arquivos de Log

Os logs de cada serviço são armazenados no diretório `logs/`:

- `api.log`: Logs da API
- `collector.log`: Logs do coletor de notícias
- `monitor.log`: Logs do monitor de recursos
- `bluemonitor_cli.log`: Logs da própria CLI

## Monitoramento de Recursos

O monitor de recursos coleta métricas detalhadas sobre o desempenho do sistema:

```bash
# Visualizar métricas coletadas
python -m scripts.visualize_resources monitor/metrics_*.jsonl
```

Isso irá gerar um relatório HTML com gráficos no diretório `monitor/metrics_*_plots/`.

## Dicas e Solução de Problemas

### Verificar se um serviço está em execução
```bash
ps aux | grep "uvicorn\|python.*monitor"
```

### Forçar parada de todos os processos
```bash
pkill -f "uvicorn|python.*monitor"
```

### Verificar logs em tempo real
```bash
tail -f logs/*.log
```

### Configurar monitoramento automático
Adicione ao crontab para iniciar automaticamente na inicialização do sistema:

```bash
@reboot cd /caminho/para/bluemonitor && /usr/bin/python3 -m scripts.bluemonitor_cli run >> /var/log/bluemonitor.log 2>&1
```

## Personalização

### Variáveis de Ambiente
A CLI lê as variáveis de ambiente do arquivo `.env` na raiz do projeto. Você pode personalizar:

- `MONGO_URI`: URI de conexão com o MongoDB
- `SERPAPI_KEY`: Chave da API do SerpAPI
- `OPENAI_API_KEY`: Chave da API da OpenAI
- `SMTP_*`: Configurações de email para alertas

### Configuração dos Processos
Você pode modificar os comandos de inicialização no arquivo `scripts/bluemonitor_cli.py` na constante `PROCESSES`.

## Segurança

- Nunca exponha a API publicamente sem autenticação
- Mantenha as chaves de API em segredo
- Use HTTPS em produção
- Monitore os logs regularmente em busca de atividades suspeitas

## Solução de Problemas Comuns

### Serviço não inicia
1. Verifique os logs em `logs/<servico>.log`
2. Confira se todas as dependências estão instaladas
3. Verifique se as portas necessárias estão disponíveis

### Erros de conexão com o banco de dados
1. Verifique se o MongoDB está em execução
2. Confira a `MONGO_URI` no arquivo `.env`
3. Verifique as permissões do banco de dados

### Problemas de desempenho
1. Monitore o uso de recursos com `python -m scripts.bluemonitor_cli status`
2. Verifique os logs em busca de erros
3. Considere escalar os recursos da máquina se necessário

## Contribuição

1. Faça um fork do repositório
2. Crie uma branch para sua feature (`git checkout -b feature/awesome-feature`)
3. Commit suas mudanças (`git commit -am 'Add some awesome feature'`)
4. Push para a branch (`git push origin feature/awesome-feature`)
5. Abra um Pull Request

## Licença

Este projeto está licenciado sob a licença MIT - veja o arquivo [LICENSE](LICENSE) para mais detalhes.
