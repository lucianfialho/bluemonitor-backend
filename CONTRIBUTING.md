# Contribuindo para o BlueMonitor

Obrigado pelo seu interesse em contribuir para o BlueMonitor! Aqui estão algumas diretrizes para ajudar você a começar.

## 🚀 Começando

1. **Faça um Fork** do repositório
2. **Clone** o repositório para sua máquina local:
   ```bash
   git clone https://github.com/seu-usuario/bluemonitor.git
   cd bluemonitor
   ```
3. **Crie um branch** para sua feature/correção:
   ```bash
   git checkout -b feature/nova-feature
   ```
4. **Instale as dependências**:
   ```bash
   pip install -r requirements.txt
   ```
5. **Faça suas alterações**
6. **Teste suas alterações**
   ```bash
   pytest
   ```
7. **Faça commit** das suas alterações:
   ```bash
   git add .
   git commit -m "feat: adiciona nova funcionalidade"
   ```
8. **Envie** suas alterações:
   ```bash
   git push origin feature/nova-feature
   ```
9. **Abra um Pull Request**

## 📝 Padrões de Código

- Siga o [PEP 8](https://www.python.org/dev/peps/pep-0008/) para código Python
- Use [type hints](https://docs.python.org/3/library/typing.html) em todo o código
- Documente funções e classes com docstrings
- Mantenha os testes atualizados

## 🧪 Testes

- Escreva testes para novas funcionalidades
- Execute todos os testes antes de enviar um PR:
  ```bash
  pytest
  ```
- Mantenha a cobertura de testes acima de 80%

## 📦 Dependências

- Adicione novas dependências apenas quando necessário
- Documente a razão da dependência no PR
- Mantenha as versões das dependências atualizadas

## 📝 Pull Requests

- Descreva claramente as mudanças propostas
- Inclua exemplos de uso, se aplicável
- Referencie issues relacionadas
- Mantenha o PR focado em uma única funcionalidade/correção

## 🐛 Reportando Bugs

Use as [issues do GitHub](https://github.com/seu-usuario/bluemonitor/issues) para reportar bugs. Inclua:

1. Um resumo do problema
2. Passos para reproduzir
3. Comportamento esperado vs. real
4. Capturas de tela, se aplicável
5. Ambiente (SO, versão do Python, etc.)

## 📄 Licença

Ao contribuir, você concorda que suas contribuições serão licenciadas sob a [Licença MIT](LICENSE).

## 🙏 Agradecimentos

Obrigado por ajudar a melhorar o BlueMonitor! Sua contribuição é muito valiosa para a comunidade.
