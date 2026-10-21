# Alterações

O formato segue o [Keep a Changelog](https://keepachangelog.com/pt-PT/1.1.0/) e as versões o [Semantic Versioning](https://semver.org/lang/pt-PT/).

## [0.1.0] - por publicar

- `parse` e `check` para o código QR das faturas (Portaria n.º 195/2020).
- `is_valid_nif`, `nif_type` e `normalize_nif`.
- Linha de comandos `faturapt`.
- Regras conferidas com as especificações técnicas da AT (versão 1.0): tamanho máximo de cada campo no `parse`; ordem dos campos e duas casas decimais no `check`; os quatro exemplos do documento nos testes.
