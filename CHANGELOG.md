# Alterações

O formato segue o [Keep a Changelog](https://keepachangelog.com/pt-PT/1.1.0/) e as versões o [Semantic Versioning](https://semver.org/lang/pt-PT/).

## [Por publicar]

### Adicionado

- `check_vat`, com avisos sobre o IVA de cada taxa: confirma que o IVA é a base vezes a taxa em vigor na data da fatura (continente, Açores e Madeira, com as mudanças de 2021 nos Açores e de 2024 na Madeira), com folga para os arredondamentos. São avisos, separados do `check`, porque as taxas mudam com os orçamentos.
- A linha de comandos e a página de demonstração mostram esses avisos (`warnings`), sem mudar o código de saída.

## [0.3.0] - 2026-10-22

### Adicionado

- `InvoiceQR.to_dict()` e `InvoiceQR.from_dict()`: a fatura num dicionário pronto para JSON (valores em texto com duas casas, datas em ISO, IVA numa lista) e o caminho inverso, que passa pelas mesmas regras do `parse`. Testes de ida e volta com o Hypothesis, através do JSON.

### Alterado

- A linha de comandos escreve o `to_dict()` mais a lista `problems`: os valores passam a ter sempre duas casas (`"10.00"` em vez de `"10"`), e entra o `is_final_consumer`.

## [0.2.0] - 2026-10-22

### Adicionado

- `read_pdf`, para ler o QR da fatura num PDF, mesmo quando está desenhado (vetorial), como fazem os programas de faturação. Procura na primeira e na última página. Dependências opcionais `faturapt[pdf]` (pypdfium2, Pillow e zxing-cpp).
- A linha de comandos lê PDFs com `-i`, reconhecidos pelo conteúdo.

## [0.1.0] - 2026-10-21

Primeira versão.

### Adicionado

- `parse`, para ler o texto do código QR das faturas (Portaria n.º 195/2020), e `check`, para confirmar o conteúdo: ordem dos campos, duas casas decimais, NIFs, ATCUD (o número no fim tem de ser o do documento, e o documento em G tem de ser do tipo D) e contas.
- `InvoiceQR.to_text()`, para gerar o texto do QR, com testes de ida e volta (Hypothesis).
- `read_image`, para encontrar e ler o QR numa fotografia ou digitalização, com as dependências opcionais `faturapt[image]` (Pillow e zxing-cpp).
- `is_valid_nif`, `nif_type` e `normalize_nif`.
- Linha de comandos `faturapt`, a partir do texto ou de uma imagem (`-i`/`--imagem`).
- Regras conferidas com as especificações técnicas da AT (versão 1.0, agosto de 2020), com os quatro exemplos do documento nos testes.

[Por publicar]: https://github.com/JoseFerrao20/faturapt/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/JoseFerrao20/faturapt/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/JoseFerrao20/faturapt/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/JoseFerrao20/faturapt/releases/tag/v0.1.0
