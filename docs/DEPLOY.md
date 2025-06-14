# Guia de Deploy - BlueMonitor

Este guia fornece instruções para implantar a aplicação BlueMonitor em um ambiente de produção.

## Pré-requisitos

- Docker e Docker Compose instalados
- Acesso a um servidor Linux (recomendado Ubuntu 20.04+)
- Domínio configurado (opcional, para HTTPS)

## 1. Configuração do Ambiente

### 1.1. Clone o repositório

```bash
git clone <seu-repositorio>
cd bluemonitor
```

### 1.2. Configure as variáveis de ambiente

1. Copie o arquivo `.env.example` para `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edite o arquivo `.env` com suas configurações:
   ```bash
   nano .env
   ```

   Certifique-se de configurar pelo menos:
   - `SECRET_KEY`: Uma chave secreta segura
   - `MONGODB_URL`: URL do MongoDB
   - `SERPAPI_KEY`: Sua chave da API do SerpAPI

## 2. Construa e Inicie os Contêineres

```bash
docker-compose up -d --build
```

Isso irá:
- Construir a imagem da API
- Iniciar o MongoDB
- Iniciar o Mongo Express (opcional, para gerenciamento do banco de dados)
- Iniciar a aplicação

## 3. Verifique os Logs

```bash
docker-compose logs -f
```

## 4. Agendamento da Clusterização

Para executar a clusterização periodicamente, configure um cron job:

1. Abra o crontab:
   ```bash
   crontab -e
   ```

2. Adicione a seguinte linha para executar a cada 6 horas:
   ```
   0 */6 * * * cd /caminho/para/bluemonitor && docker-compose exec -T api python scripts/run_clustering.py >> /var/log/bluemonitor-clustering.log 2>&1
   ```

## 5. Configuração de HTTPS (Opcional)

Recomendamos usar o Nginx como proxy reverso com Let's Encrypt para HTTPS.

### 5.1. Instale o Nginx e o Certbot

```bash
sudo apt update
sudo apt install -y nginx certbot python3-certbot-nginx
```

### 5.2. Configure o Nginx

Crie um arquivo de configuração para seu domínio em `/etc/nginx/sites-available/bluemonitor`:

```nginx
server {
    listen 80;
    server_name seudominio.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 5.3. Obtenha o Certificado SSL

```bash
sudo certbot --nginx -d seudominio.com
```

## 6. Monitoramento

### 6.1. Verifique a saúde da aplicação

```bash
curl http://localhost:8000/health
```

### 6.2. Monitore os logs

```bash
docker-compose logs -f
```

## 7. Atualizações

Para atualizar a aplicação:

```bash
git pull
docker-compose up -d --build
```

## Solução de Problemas

### A aplicação não está acessível

1. Verifique se os contêineres estão em execução:
   ```bash
   docker-compose ps
   ```

2. Verifique os logs em busca de erros:
   ```bash
   docker-compose logs
   ```

### A clusterização não está funcionando

1. Verifique se o job agendado está em execução:
   ```bash
   grep CRON /var/log/syslog
   ```

2. Verifique o log de clusterização:
   ```bash
   cat /var/log/bluemonitor-clustering.log
   ```

## Suporte

Em caso de problemas, entre em contato com a equipe de desenvolvimento.
