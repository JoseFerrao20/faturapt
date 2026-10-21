# Alterações

O formato segue o [Keep a Changelog](https://keepachangelog.com/pt-PT/1.1.0/) e as versões o [Semantic Versioning](https://semver.org/lang/pt-PT/).

## [0.1.0] - por publicar

- `parse` e `check` para o código QR das faturas (Portaria n.º 195/2020).
- `is_valid_nif`, `nif_type` e `normalize_nif`.
- Linha de comandos `faturapt`, com `-i`/`--imagem` para ler uma fotografia.
- `read_image`, para encontrar e ler o QR numa imagem, com as dependências opcionais `faturapt[image]` (Pillow e zxing-cpp).
- `InvoiceQR.to_text()`, para gerar o texto do QR, com testes de ida e volta (Hypothesis).
- `check` confirma o ATCUD (o número no fim tem de ser o do documento) e que o documento (G) é do tipo D.
- Regras conferidas com as especificações técnicas da AT (versão 1.0): tamanho máximo de cada campo no `parse`; ordem dos campos e duas casas decimais no `check`; os quatro exemplos do documento nos testes.
