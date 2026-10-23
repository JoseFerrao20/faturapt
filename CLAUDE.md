# faturapt

Biblioteca Python (≥ 3.10, sem dependências) que lê e valida o código QR das faturas portuguesas (`src/faturapt/qr.py`) e NIFs (`src/faturapt/nif.py`), com a linha de comandos em `__main__.py`. A leitura de imagens (`image.py`) usa as dependências opcionais `faturapt[image]` (Pillow e zxing-cpp), importadas só dentro do `read_image`: `import faturapt` tem de funcionar sem elas. O mesmo para os PDFs (`pdf.py`, `faturapt[pdf]`, com o pypdfium2): o PDFium não aguenta duas threads ao mesmo tempo, por isso o `read_pdf` usa um lock enquanto desenha as páginas. Projeto de portfólio de José Ferrão.

A página de demonstração (`site/`, publicada pelo `pages.yml` no GitHub Pages) corre o faturapt no browser com o Pyodide e lê fotografias com o zxing-wasm; as versões de ambos estão fixadas em `site/app.js`. O texto que vem do QR entra na página só com `textContent`, nunca como HTML.

## Comandos

```bash
uv sync --all-extras
uv run pytest                                  # inclui os exemplos do README (doctest) e cobertura ≥ 95 %
uv run ruff check . && uv run ruff format --check . && uv run mypy
uv build
```

## Convenções

- README, CHANGELOG, mensagens de erro e descrições de PR em **português de Portugal**; nomes no código e mensagens de commit em inglês.
- API pública só pelo que está em `faturapt.__all__`; mudar algo que já lá está é uma versão nova *major* (ou *minor* antes da 1.0) e entra no `CHANGELOG.md`.
- `parse` só recusa o que está mal formado; problemas de conteúdo (NIFs, contas) vão para `check`, que devolve uma lista e nunca lança.
- Valores em `Decimal`, nunca `float`.
- `check_vat` (`vat.py`) só dá avisos, nunca entra no `check`: as taxas de IVA mudam com os orçamentos. Uma taxa nova entra na tabela `_RATES` com a data e a fonte (diploma) no comentário, e com um teste na data da mudança.
- Nos testes de imagem, os QR são gerados com o `segno` e não com o escritor do zxing, para o leitor não ser testado contra si próprio.
- `to_text` e `parse` são inversos: `parse(fatura.to_text()) == fatura`, e o mesmo para `to_dict` e `from_dict`, através do JSON (testes com o Hypothesis em `tests/test_build.py`). Um campo novo entra nos quatro. O `to_dict` é o formato do JSON da linha de comandos e da página de demonstração.
- Cada alteração num PR a partir de um ramo, com o CI verde.
