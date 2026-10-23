"""Confirmação do IVA de cada taxa (só avisos: as taxas mudam com o tempo e por região)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from .qr import InvoiceQR

__all__ = ["check_vat"]

# Taxas reduzida, intermédia e normal (em %) por espaço fiscal, a partir da data indicada.
# O QR só existe desde 2020 (Portaria n.º 195/2020), por isso a tabela começa em 2019: os
# exemplos da especificação da AT, desse ano, confirmam as taxas de então nas três regiões.
# - PT (continente): 6 / 13 / 23.
# - PT-AC (Açores): 4 / 9 / 18; a normal passou a 16 a 1 de julho de 2021 (Orçamento regional
#   para 2021).
# - PT-MA (Madeira): 5 / 12 / 22; a reduzida passou a 4 a 1 de outubro de 2024 (Decreto
#   Legislativo Regional n.º 6/2024/M).
# Antes de 2019 ou noutro espaço fiscal, não se confirma nada.
_RATES: dict[str, list[tuple[date, tuple[int, int, int]]]] = {
    "PT": [(date(2019, 1, 1), (6, 13, 23))],
    "PT-AC": [(date(2019, 1, 1), (4, 9, 18)), (date(2021, 7, 1), (4, 9, 16))],
    "PT-MA": [(date(2019, 1, 1), (5, 12, 22)), (date(2024, 10, 1), (4, 12, 22))],
}
_CATEGORIES = (
    ("reduced", "reduzida"),
    ("intermediate", "intermédia"),
    ("normal", "normal"),
)
# O IVA costuma ser arredondado linha a linha, por isso a soma pode afastar-se uns cêntimos
# da base vezes a taxa: tolera-se 10 cêntimos ou 1 % do IVA esperado, o que for maior.
_MIN_TOLERANCE = Decimal("0.10")
_RELATIVE_TOLERANCE = Decimal("0.01")


def _rates(fiscal_space: str, day: date) -> tuple[int, int, int] | None:
    current = None
    for start, rates in _RATES.get(fiscal_space, []):
        if day >= start:
            current = rates
    return current


def check_vat(invoice: InvoiceQR) -> list[str]:
    """Avisos sobre o IVA de cada taxa; lista vazia se bater certo ou não se puder confirmar.

    Para cada espaço fiscal e taxa com base e IVA, confirma que o IVA é a base vezes a
    taxa em vigor na data da fatura, com uma folga para os arredondamentos. Ao contrário
    do :func:`check`, são avisos: as taxas mudam com os orçamentos (sobretudo nos Açores e
    na Madeira), e o faturapt só conhece as que estão na tabela. Fora dela (espaço fiscal
    desconhecido ou data anterior), não diz nada.
    """
    warnings = []
    for tax in invoice.taxes:
        rates = _rates(tax.fiscal_space, invoice.document_date)
        if rates is None:
            continue
        for (prefix, name), rate in zip(_CATEGORIES, rates, strict=True):
            base = getattr(tax, f"{prefix}_base")
            vat = getattr(tax, f"{prefix}_vat")
            if base is None or vat is None:
                continue
            expected = (base * rate / 100).quantize(Decimal("0.01"))
            tolerance = max(_MIN_TOLERANCE, expected * _RELATIVE_TOLERANCE)
            if abs(vat - expected) > tolerance:
                warnings.append(
                    f"IVA à taxa {name} ({tax.fiscal_space}, {rate} %): a base {base:.2f} "
                    f"dá {expected:.2f} de IVA, mas o QR tem {vat:.2f}"
                )
    return warnings
