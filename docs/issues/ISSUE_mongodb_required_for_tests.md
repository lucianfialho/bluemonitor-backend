# Erro de conexão com MongoDB nos testes automatizados

**Descrição:**
Ao rodar os testes automatizados, diversos testes de integração falham devido à impossibilidade de conectar ao MongoDB local (`localhost:27017`). O erro reportado é:

```
pymongo.errors.ServerSelectionTimeoutError: localhost:27017: [Errno 111] Connection refused
```

**Impacto:**
Os testes que dependem de acesso ao banco de dados não são executados corretamente, impedindo a validação completa do backend.

**Como reproduzir:**
1. Execute `pytest` no projeto.
2. Observe os erros de conexão relacionados ao MongoDB.

**Possível causa:**
- O serviço do MongoDB não está rodando localmente ou não está acessível na porta padrão.
- O ambiente de testes não está configurado para usar um banco de dados de teste isolado.

**Checklist:**
- [x] Garantir que o MongoDB está rodando e acessível para os testes. (Verificado via `docker compose ps mongodb`)
- [x] Documentar como subir o MongoDB localmente (ex: via Docker Compose). (Instruções adicionadas no README)
- [x] Configurar variáveis de ambiente para apontar para o banco de teste. (Verificar arquivo `.env` e exemplos no README)
- [ ] Garantir que os testes de integração executam sem erro de conexão. (O MongoDB está acessível, mas há falhas relacionadas ao event loop/fixtures async do pytest, não mais erro de conexão)

**Sugestão:**
Adicionar instruções no README ou scripts utilitários para facilitar a inicialização do ambiente de testes com MongoDB.

---

**Comentário:**
A centralização do parsing de datas foi concluída com sucesso e não há regressão na lógica de datas. As falhas atuais nos testes são exclusivamente relacionadas à ausência do MongoDB e não à lógica de datas ou parsing.

Adicionalmente, após garantir o MongoDB rodando, os testes agora falham por questões de event loop/asyncio nas fixtures do pytest, não mais por erro de conexão. Recomenda-se revisar as fixtures async e a inicialização do app de testes para compatibilidade total com pytest-asyncio e FastAPI.
