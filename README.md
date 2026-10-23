# faturapt

[![CI](https://github.com/JoseFerrao20/faturapt/actions/workflows/ci.yml/badge.svg)](https://github.com/JoseFerrao20/faturapt/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/faturapt)](https://pypi.org/project/faturapt/)
[![Versões de Python](https://img.shields.io/pypi/pyversions/faturapt)](https://pypi.org/project/faturapt/)
[![Licença: MIT](https://img.shields.io/badge/licen%C3%A7a-MIT-blue)](LICENSE)

Lê e valida o **código QR das faturas portuguesas** (o que a AT exige desde 2022, Portaria n.º 195/2020) e **NIFs**. Python puro, sem dependências obrigatórias, com tipos.

**[Experimentar no browser](https://joseferrao20.github.io/faturapt/)**: cola o texto de um QR, aponta a câmara do telemóvel à fatura ou escolhe uma fotografia. A página corre o próprio faturapt com o [Pyodide](https://pyodide.org) e nada sai do teu computador.

```python
>>> import faturapt
>>> inv = faturapt.parse("A:500000000*B:999999990*C:PT*D:FS*E:N*F:20261015*G:FS 01/1234"
...                      "*H:JJ3XY2KD-1234*I1:PT*I7:10.00*I8:2.30*N:2.30*O:12.30*Q:Ab1z*R:1234")
>>> inv.document_type_name, inv.document_date, inv.total
('Fatura simplificada', datetime.date(2026, 10, 15), Decimal('12.30'))
>>> inv.is_final_consumer
True
>>> faturapt.check(inv)      # NIFs e contas; lista vazia = tudo certo
[]
>>> faturapt.check_vat(inv)  # avisos: o IVA de cada taxa bate certo com a base?
[]
>>> faturapt.nif_type("PT 123 456 789")
<NifType.INDIVIDUAL: 'pessoa singular'>
>>> dados = inv.to_dict()    # pronto para JSON: valores em texto, datas em ISO
>>> dados["total"], dados["document_date"], dados["taxes"][0]["normal_vat"]
('12.30', '2026-10-15', '2.30')
>>> faturapt.InvoiceQR.from_dict(dados) == inv
True

```

## Instalar

```bash
pip install faturapt             # só texto: sem dependências
pip install 'faturapt[image]'    # também lê fotografias (Pillow e zxing-cpp)
pip install 'faturapt[pdf]'      # fotografias e PDFs (também o pypdfium2)
```

```python
>>> fatura = faturapt.read_image("talao.jpg")    # doctest: +SKIP
>>> fatura.total, faturapt.check(fatura)          # doctest: +SKIP
(Decimal('12.30'), [])
>>> faturapt.read_pdf("fatura.pdf").document_id   # doctest: +SKIP
'FS 01/1234'
```

## O que faz

- **`parse(texto)`**: converte o texto do QR num `InvoiceQR` (datas em `date`, valores em `Decimal`, IVA por espaço fiscal: continente, Açores e Madeira). Lança `QRCodeError`, com a mensagem em português, se faltarem campos obrigatórios, houver campos repetidos, desconhecidos ou acima do tamanho máximo, ou valores mal formados.
- **`check(fatura)`**: devolve os problemas de conteúdo: campos fora de ordem, valores sem duas casas decimais, NIFs inválidos, ATCUD que não acaba no número do documento (G) ou documento (G) de outro tipo que não o D, total de impostos (N) diferente de IVA + selo, ou total (O) diferente de bases + não sujeito + impostos.
- **`check_vat(fatura)`**: avisos (e não problemas) sobre o IVA de cada taxa. Confirma que o IVA é a base vezes a taxa em vigor na data da fatura, no continente, nos Açores e na Madeira, com uma folga para os arredondamentos linha a linha (10 cêntimos ou 1 %). Apanha, por exemplo, uma base à taxa intermédia no campo da normal. São só avisos porque as taxas mudam com os orçamentos, sobretudo nas regiões autónomas: a tabela está em `vat.py`, confirmada com os exemplos da especificação da AT, e fora dela (antes de 2019 ou noutro espaço fiscal) não se avisa nada.
- **`fatura.to_text()`**: o caminho inverso, para quem gera faturas: escreve o texto do QR pela ordem da especificação, com duas casas decimais, e recusa valores acima do tamanho máximo. `parse(fatura.to_text())` devolve sempre a mesma fatura (os testes confirmam-no com o Hypothesis, em faturas geradas ao acaso).
- **`fatura.to_dict()` e `InvoiceQR.from_dict(dados)`**: a fatura num dicionário pronto para JSON, para a guardar numa base de dados ou a passar a um programa noutra linguagem. Os valores vêm em texto com duas casas (`"12.30"`, nunca `float`, para não perderem cêntimos), as datas em ISO e o IVA numa lista, um dicionário por espaço fiscal. O `from_dict` faz o caminho inverso e passa pelas mesmas regras do `parse`. As duas também se confirmam com o Hypothesis, através do JSON.
- **`is_valid_nif`, `nif_type`, `normalize_nif`**: dígito de controlo, prefixos e tipo de contribuinte (pessoa singular, coletiva, condomínio, …). Aceita espaços, pontos e o prefixo `PT`.
- **`read_image(imagem)`**: encontra o QR da fatura numa fotografia ou digitalização (caminho, `bytes` ou imagem do Pillow) e lê-o com o `parse`. Respeita a orientação EXIF do telemóvel e, se houver outros QR na imagem (um site, uma promoção), escolhe o da fatura. Precisa de `faturapt[image]`.
- **`read_pdf(pdf)`**: o mesmo para a fatura em PDF que chega por email (caminho ou `bytes`). Os programas de faturação desenham o QR no PDF em vez de o pôr como imagem, por isso a página é desenhada a 300 dpi antes de se procurar o QR, na primeira e na última página (onde a especificação o deixa pôr). Pode ser chamada por várias threads ao mesmo tempo. Precisa de `faturapt[pdf]`.
- **Linha de comandos**: `faturapt "A:...*B:..."` (ou pelo stdin) ou `faturapt -i talao.jpg` (ou `-i fatura.pdf`: o PDF é reconhecido pelo conteúdo) mostra a fatura em JSON (o `to_dict()`, mais as listas `problems` do `check` e `warnings` do `check_vat`), para usar noutros programas. Sai com 0 se estiver tudo certo (os avisos do IVA não contam), com 1 se houver problemas e com 2 se o texto, a imagem ou o PDF não tiverem um QR válido.

As regras seguem as [especificações técnicas da AT](https://info.portaldasfinancas.gov.pt/pt/apoio_contribuinte/Novas_regras_faturacao/Documents/Especificacoes_Tecnicas_Codigo_QR.pdf) (versão 1.0, agosto de 2020), e os quatro exemplos do documento fazem parte dos testes. O `parse` recusa o que não se consegue ler (campos desconhecidos, repetidos ou acima do tamanho máximo, obrigatórios em falta); o `check` aponta o resto (campos fora de ordem, valores sem duas casas decimais, NIFs e contas).


## Campos do QR

| Chave | Campo | `InvoiceQR` |
|---|---|---|
| A, B, C | NIF do emitente, NIF e país do adquirente | `issuer_nif`, `buyer_nif`, `buyer_country` |
| D, E, F, G | Tipo, estado, data e identificação do documento | `document_type`, `document_status`, `document_date`, `document_id` |
| H | ATCUD | `atcud` |
| I1–I8, J1–J8, K1–K8 | IVA por espaço fiscal (isento, reduzida, intermédia, normal) | `taxes` (`TaxBreakdown`) |
| L, M, N, O, P | Não sujeito, selo, total de impostos, total, retenção na fonte | `non_taxable`, `stamp_duty`, `total_taxes`, `total`, `withholding` |
| Q, R, S | 4 caracteres do hash, n.º do certificado, outras informações | `hash_chars`, `certificate`, `other_info` |

## Desenvolvimento

```bash
uv sync --all-extras                      # ambiente com as dependências de desenvolvimento e de imagem
uv run pytest                             # testes, com cobertura mínima de 95 %
uv run ruff check . && uv run ruff format --check . && uv run mypy
```

A página de demonstração está em `site/`: o `demo.py` é a ponte para o faturapt (testada em `tests/test_site.py`) e o workflow `pages.yml` publica-a no GitHub Pages a cada push na `main`, com o wheel acabado de construir.

O CI corre o mesmo em Python 3.10 a 3.14. Para publicar uma versão: atualizar `__version__`, passar as entradas de "Por publicar" do `CHANGELOG.md` para a versão nova, com a data, e criar uma tag `vX.Y.Z`. O workflow `release.yml` publica no PyPI por *trusted publishing* (sem tokens guardados no GitHub).

## Contribuir

Issues e pull requests são bem-vindos: ver o [CONTRIBUTING.md](CONTRIBUTING.md). O que mais ajuda é um QR de uma fatura real que o faturapt leia mal. Vulnerabilidades comunicam-se em privado ([SECURITY.md](SECURITY.md)).

## Licença

MIT.
