# faturapt

Lê e valida o **código QR das faturas portuguesas** (o que a AT exige desde 2022, Portaria n.º 195/2020) e **NIFs**. Python puro, sem dependências, com tipos.

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
>>> faturapt.nif_type("PT 123 456 789")
<NifType.INDIVIDUAL: 'pessoa singular'>

```

## Instalar

```bash
pip install faturapt
```

## O que faz

- **`parse(texto)`**: converte o texto do QR num `InvoiceQR` (datas em `date`, valores em `Decimal`, IVA por espaço fiscal: continente, Açores e Madeira). Lança `QRCodeError`, com a mensagem em português, se faltarem campos obrigatórios, houver campos repetidos, desconhecidos ou acima do tamanho máximo, ou valores mal formados.
- **`check(fatura)`**: devolve os problemas de conteúdo: campos fora de ordem, valores sem duas casas decimais, NIFs inválidos, total de impostos (N) diferente de IVA + selo, ou total (O) diferente de bases + não sujeito + impostos.
- **`is_valid_nif`, `nif_type`, `normalize_nif`**: dígito de controlo, prefixos e tipo de contribuinte (pessoa singular, coletiva, condomínio, …). Aceita espaços, pontos e o prefixo `PT`.
- **Linha de comandos**: `faturapt "A:...*B:..."` (ou pelo stdin) mostra a fatura em JSON. Sai com 0 se estiver tudo certo, com 1 se houver problemas e com 2 se o texto não for um QR válido.

As regras seguem as [especificações técnicas da AT](https://info.portaldasfinancas.gov.pt/pt/apoio_contribuinte/Novas_regras_faturacao/Documents/Especificacoes_Tecnicas_Codigo_QR.pdf) (versão 1.0, agosto de 2020), e os quatro exemplos do documento fazem parte dos testes. O `parse` recusa o que não se consegue ler (campos desconhecidos, repetidos ou acima do tamanho máximo, obrigatórios em falta); o `check` aponta o resto (campos fora de ordem, valores sem duas casas decimais, NIFs e contas).

Ler a imagem do QR não faz parte da biblioteca: para isso, usar por exemplo o `zxing-cpp` ou o `pyzbar` e passar o texto ao `parse`.

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
uv sync                                   # ambiente com as dependências de desenvolvimento
uv run pytest                             # testes, com cobertura mínima de 95 %
uv run ruff check . && uv run ruff format --check . && uv run mypy
```

O CI corre o mesmo em Python 3.10 a 3.14. Para publicar uma versão: atualizar `__version__` e o `CHANGELOG.md`, e criar uma tag `vX.Y.Z`. O workflow `release.yml` publica no PyPI por *trusted publishing* (sem tokens guardados no GitHub).

## Licença

MIT.
