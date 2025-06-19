# MongoDB obrigatório para execução dos testes de integração

**Descrição:**
Os testes automatizados de integração do backend dependem de uma instância do MongoDB acessível em `localhost:27017`. Atualmente, ao rodar os testes sem o MongoDB, ocorrem erros de conexão (`Connection refused`) e falhas relacionadas à ausência do atributo `mongodb_manager` no app de teste.

**Impacto:**
- Testes de integração que dependem do banco de dados não são executados corretamente.
- Não é possível validar o comportamento completo da aplicação sem o ambiente de banco configurado.

**Como reproduzir:**
1. Execute `pytest` no projeto sem um MongoDB rodando.
2. Observe erros como:
   - `pymongo.errors.ServerSelectionTimeoutError: localhost:27017: [Errno 111] Connection refused`
   - `AttributeError: 'State' object has no attribute 'mongodb_manager'`

**Checklist:**
- [ ] Documentar no README como subir o MongoDB localmente (ex: via Docker Compose).
- [ ] Adicionar instrução clara sobre a obrigatoriedade do MongoDB para rodar os testes.
- [ ] (Opcional) Adicionar um script utilitário para facilitar o setup do ambiente de testes.
- [ ] Garantir que todos os testes de integração executam sem erro de conexão.

---

**Comentário:**
A centralização do parsing de datas foi concluída com sucesso e não há regressão na lógica de datas. As falhas atuais nos testes são exclusivamente relacionadas à ausência do MongoDB e não à lógica de datas ou parsing.
