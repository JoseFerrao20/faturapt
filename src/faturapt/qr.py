"""Leitura do código QR das faturas portuguesas.

O formato vem da Portaria n.º 195/2020 e das especificações técnicas da AT:
campos ``CHAVE:valor`` separados por ``*``, por exemplo
``A:123456789*B:999999990*C:PT*D:FT*...``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from .nif import is_valid_nif

__all__ = [
    "DOCUMENT_TYPES",
    "InvoiceQR",
    "QRCodeError",
    "TaxBreakdown",
    "check",
    "parse",
]


class QRCodeError(ValueError):
    """O texto não é um código QR de fatura bem formado."""


DOCUMENT_TYPES: dict[str, str] = {
    "FT": "Fatura",
    "FS": "Fatura simplificada",
    "FR": "Fatura-recibo",
    "ND": "Nota de débito",
    "NC": "Nota de crédito",
    "GR": "Guia de remessa",
    "GT": "Guia de transporte",
    "GA": "Guia de movimentação de ativos próprios",
    "GC": "Guia de consignação",
    "GD": "Guia ou nota de devolução",
    "CM": "Consulta de mesa",
    "CC": "Crédito de consignação",
    "FC": "Fatura de consignação",
    "FO": "Folha de obra",
    "NE": "Nota de encomenda",
    "OU": "Outros",
    "OR": "Orçamento",
    "PF": "Fatura pró-forma",
    "RC": "Recibo",
    "RG": "Outro recibo",
}

_REQUIRED = ("A", "B", "C", "D", "E", "F", "G", "H", "I1", "N", "O", "Q", "R")
_SINGLE = {"A", "B", "C", "D", "E", "F", "G", "H", "L", "M", "N", "O", "P", "Q", "R", "S"}
_TAX_KEY = re.compile(r"^([IJK])([1-8])$")
_AMOUNT = re.compile(r"^-?\d+(\.\d{1,2})?$")


@dataclass(frozen=True, slots=True)
class TaxBreakdown:
    """IVA de um espaço fiscal (campos I, J ou K)."""

    fiscal_space: str
    """``PT``, ``PT-AC`` (Açores) ou ``PT-MA`` (Madeira)."""
    exempt_base: Decimal | None = None
    reduced_base: Decimal | None = None
    reduced_vat: Decimal | None = None
    intermediate_base: Decimal | None = None
    intermediate_vat: Decimal | None = None
    normal_base: Decimal | None = None
    normal_vat: Decimal | None = None

    @property
    def total_base(self) -> Decimal:
        parts = (self.exempt_base, self.reduced_base, self.intermediate_base, self.normal_base)
        return sum((p for p in parts if p is not None), Decimal(0))

    @property
    def total_vat(self) -> Decimal:
        parts = (self.reduced_vat, self.intermediate_vat, self.normal_vat)
        return sum((p for p in parts if p is not None), Decimal(0))


@dataclass(frozen=True, slots=True)
class InvoiceQR:
    """Os campos de um código QR de fatura, já convertidos."""

    issuer_nif: str
    buyer_nif: str
    buyer_country: str
    document_type: str
    document_status: str
    document_date: date
    document_id: str
    atcud: str
    taxes: tuple[TaxBreakdown, ...]
    total_taxes: Decimal
    total: Decimal
    hash_chars: str
    certificate: str
    non_taxable: Decimal | None = None
    stamp_duty: Decimal | None = None
    withholding: Decimal | None = None
    other_info: str | None = None
    fields: dict[str, str] = field(default_factory=dict, compare=False, repr=False)
    """Os campos tal como vieram, por chave."""

    @property
    def document_type_name(self) -> str | None:
        """Nome do tipo de documento (``"Fatura"``), ou ``None`` se for desconhecido."""
        return DOCUMENT_TYPES.get(self.document_type)

    @property
    def is_final_consumer(self) -> bool:
        """``True`` se a fatura não tem NIF do adquirente (consumidor final)."""
        return self.buyer_nif == "999999990"


def _split(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for part in text.strip().split("*"):
        key, sep, value = part.partition(":")
        if not sep or not key:
            raise QRCodeError(f"Campo sem o formato CHAVE:valor: {part!r}")
        if key in fields:
            raise QRCodeError(f"Campo repetido: {key}")
        if key not in _SINGLE and not _TAX_KEY.match(key):
            raise QRCodeError(f"Campo desconhecido: {key}")
        fields[key] = value
    return fields


def _amount(fields: dict[str, str], key: str) -> Decimal | None:
    raw = fields.get(key)
    if raw is None:
        return None
    if not _AMOUNT.match(raw):
        raise QRCodeError(f"Valor inválido no campo {key} (usar ponto e até 2 casas): {raw!r}")
    try:
        return Decimal(raw)
    except InvalidOperation as exc:  # pragma: no cover - o regex já o impede
        raise QRCodeError(f"Valor inválido no campo {key}: {raw!r}") from exc


def _taxes(fields: dict[str, str]) -> tuple[TaxBreakdown, ...]:
    result = []
    for letter in "IJK":
        space = fields.get(f"{letter}1")
        others = [k for k in fields if k.startswith(letter) and k != f"{letter}1"]
        if space is None:
            if others:
                raise QRCodeError(f"Campos {letter}2 a {letter}8 sem o espaço fiscal {letter}1")
            continue
        if space == "0":  # documento sem IVA
            if others:
                raise QRCodeError(f"{letter}1 é 0 (sem IVA), mas há outros campos {letter}")
            continue
        names = (
            "exempt_base",
            "reduced_base",
            "reduced_vat",
            "intermediate_base",
            "intermediate_vat",
            "normal_base",
            "normal_vat",
        )
        values = {name: _amount(fields, f"{letter}{i}") for i, name in enumerate(names, start=2)}
        result.append(TaxBreakdown(fiscal_space=space, **values))
    return tuple(result)


def parse(text: str) -> InvoiceQR:
    """Lê o texto de um código QR de fatura.

    Lança :class:`QRCodeError` se o texto estiver mal formado ou faltarem campos
    obrigatórios. Não confirma NIFs nem contas: para isso, usar :func:`check`.
    """
    fields = _split(text)
    missing = [k for k in _REQUIRED if k not in fields]
    if missing:
        raise QRCodeError(f"Faltam campos obrigatórios: {', '.join(missing)}")

    try:
        document_date = datetime.strptime(fields["F"], "%Y%m%d").date()
    except ValueError as exc:
        raise QRCodeError(f"Data inválida no campo F (AAAAMMDD): {fields['F']!r}") from exc

    if len(fields["Q"]) != 4:
        raise QRCodeError(f"O campo Q tem de ter 4 caracteres do hash: {fields['Q']!r}")

    total_taxes = _amount(fields, "N") or Decimal(0)  # N e O são obrigatórios (vistos acima)
    total = _amount(fields, "O") or Decimal(0)

    return InvoiceQR(
        issuer_nif=fields["A"],
        buyer_nif=fields["B"],
        buyer_country=fields["C"],
        document_type=fields["D"],
        document_status=fields["E"],
        document_date=document_date,
        document_id=fields["G"],
        atcud=fields["H"],
        taxes=_taxes(fields),
        non_taxable=_amount(fields, "L"),
        stamp_duty=_amount(fields, "M"),
        total_taxes=total_taxes,
        total=total,
        withholding=_amount(fields, "P"),
        hash_chars=fields["Q"],
        certificate=fields["R"],
        other_info=fields.get("S"),
        fields=fields,
    )


def check(invoice: InvoiceQR) -> list[str]:
    """Problemas de conteúdo numa fatura já lida; lista vazia se estiver tudo certo.

    Confirma os NIFs e as contas: o total de impostos (N) é o IVA mais o selo, e o
    total (O) é a soma das bases, do não sujeito (L) e dos impostos (N).
    """
    problems = []
    if not is_valid_nif(invoice.issuer_nif):
        problems.append(f"NIF do emitente inválido: {invoice.issuer_nif}")
    if invoice.buyer_country == "PT" and not is_valid_nif(invoice.buyer_nif):
        problems.append(f"NIF do adquirente inválido: {invoice.buyer_nif}")

    vat = sum((t.total_vat for t in invoice.taxes), Decimal(0))
    expected_taxes = vat + (invoice.stamp_duty or 0)
    if expected_taxes != invoice.total_taxes:
        problems.append(
            f"Total de impostos (N) é {invoice.total_taxes}, mas IVA + selo dá {expected_taxes}"
        )

    bases = sum((t.total_base for t in invoice.taxes), Decimal(0))
    expected_total = bases + (invoice.non_taxable or 0) + invoice.total_taxes
    if expected_total != invoice.total:
        problems.append(
            f"Total (O) é {invoice.total}, mas bases + não sujeito + impostos dá {expected_total}"
        )
    return problems
