# Segurança

## Versões com correções

Só a versão mais recente publicada no PyPI recebe correções.

## Como comunicar uma vulnerabilidade

Não abras uma issue pública. Usa o formulário privado do GitHub:
**[comunicar uma vulnerabilidade](https://github.com/JoseFerrao20/faturapt/security/advisories/new)**.

Inclui, se puderes, o texto do QR ou o ficheiro que causa o problema (com os NIFs trocados por outros de exemplo) e a versão do faturapt e do Python.

## O que conta

O faturapt lê dados que vêm de fora (o texto de um QR, uma fotografia, um PDF). Contam, por exemplo:

- um texto, imagem ou PDF que faça o `parse`, o `read_image` ou o `read_pdf` bloquear ou gastar memória sem limite;
- um texto que faça o `parse` lançar outra exceção que não `QRCodeError` (no `read_image`, um ficheiro que não é imagem dá `OSError`, e isso é esperado);
- na página de demonstração, um QR que consiga pôr HTML ou JavaScript na página.

Problemas nas dependências (Pillow, zxing-cpp, pypdfium2) comunicam-se a esses projetos; o Dependabot traz as correções para aqui.
