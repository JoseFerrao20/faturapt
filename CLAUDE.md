# faturapt

Biblioteca Python (≥ 3.10, sem dependências) que lê e valida o código QR das faturas portuguesas (`src/faturapt/qr.py`) e NIFs (`src/faturapt/nif.py`), com a linha de comandos em `__main__.py`. Projeto de portfólio de José Ferrão.

## Comandos

```bash
uv sync
uv run pytest                                  # inclui os exemplos do README (doctest) e cobertura ≥ 95 %
uv run ruff check . && uv run ruff format --check . && uv run mypy
uv build
```

## Convenções

- README, CHANGELOG, mensagens de erro e descrições de PR em **português de Portugal**; nomes no código e mensagens de commit em inglês.
- API pública só pelo que está em `faturapt.__all__`; mudar algo que já lá está é uma versão nova *major* (ou *minor* antes da 1.0) e entra no `CHANGELOG.md`.
- `parse` só recusa o que está mal formado; problemas de conteúdo (NIFs, contas) vão para `check`, que devolve uma lista e nunca lança.
- Valores em `Decimal`, nunca `float`.
- Cada alteração num PR a partir de um ramo, com o CI verde.
