# Contribuir

Obrigado pelo interesse! Issues e pull requests são bem-vindos, em português ou em inglês.

## Antes de começar

- **Um erro na leitura de uma fatura real** é a contribuição mais útil: abre uma issue com o texto do QR (troca os NIFs de pessoas por outros de exemplo, como `999999990`) e o que esperavas.
- Para uma mudança maior, abre primeiro uma issue para combinarmos a ideia.
- As regras do QR vêm das [especificações técnicas da AT](https://info.portaldasfinancas.gov.pt/pt/apoio_contribuinte/Novas_regras_faturacao/Documents/Especificacoes_Tecnicas_Codigo_QR.pdf). Uma regra nova deve citar o ponto do documento.

## Ambiente

Com o [uv](https://docs.astral.sh/uv/):

```bash
uv sync --all-extras
uv run pytest                                      # testes, exemplos do README e cobertura ≥ 95 %
uv run ruff check . && uv run ruff format --check . && uv run mypy
```

## Regras do código

- O `parse` só recusa o que está mal formado; problemas de conteúdo (NIFs, contas, ATCUD) vão para o `check`, que devolve uma lista e nunca lança.
- Valores em `Decimal`, nunca `float`.
- `parse(fatura.to_text()) == fatura`: um campo novo entra nos dois (o teste com o Hypothesis está em `tests/test_build.py`).
- As dependências de imagem e PDF são opcionais e importam-se só dentro das funções: `import faturapt` tem de funcionar sem elas.
- Nos testes de imagem, os QR são gerados com o `segno`, não com o zxing.
- Mensagens de erro, README e CHANGELOG em português de Portugal; nomes no código e mensagens de commit em inglês.

## Pull requests

- Um PR por mudança, a partir de um ramo, com o CI verde (Python 3.10 a 3.14).
- Uma mudança visível para quem usa a biblioteca entra no `CHANGELOG.md`, em "Por publicar".
- A página de demonstração (`site/`) testa-se com `tests/test_site.py`; uma mudança no `app.js` deve ser vista no browser, nos temas claro e escuro.
