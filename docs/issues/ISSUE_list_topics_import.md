# Erro de importação: list_topics em test_topics.py

**Descrição:**
Ao rodar os testes automatizados, ocorre o seguinte erro de importação no arquivo `test_topics.py`:

```
ImportError: cannot import name 'list_topics' from 'app.api.v1.endpoints.topics'
```

**Impacto:**
Esse erro impede a execução dos testes relacionados a tópicos, podendo mascarar outros problemas e dificultando a validação de novas funcionalidades.

**Como reproduzir:**
1. Execute `pytest` no projeto.
2. Observe o erro de importação referente ao `list_topics`.

**Possível causa:**
A função `list_topics` não está definida ou não está sendo exportada corretamente no módulo `topics.py`.

**Checklist:**
- [x] Garantir que a função `list_topics` existe e está exportada no arquivo correto. (Não existe, correto é usar `get_topics`)
- [x] Corrigir o import nos testes, se necessário.
- [x] Garantir que todos os testes de tópicos executam sem erro de importação.

---

**Status:**
✔️ Issue resolvida. O erro de importação foi corrigido e os testes de tópicos executam sem erro de importação. 

**Observação:**
Persistem erros de conexão com o MongoDB nos testes de integração. Recomenda-se abrir uma nova issue para configuração do ambiente MongoDB para testes automatizados.
