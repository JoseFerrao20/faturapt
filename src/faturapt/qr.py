"""Leitura do código QR das faturas portuguesas.

O formato vem da Portaria n.º 195/2020 e das especificações técnicas da AT
("Código de Barras Bidimensional - Código QR", versão 1.0, agosto de 2020):
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
_TAX_KEYS = [f"{letter}{i}" for letter in "IJK" for i in range(1, 9)]
_MONETARY = {k for k in _TAX_KEYS if not k.endswith("1")} | {"L", "M", "N", "O", "P"}
# Tamanho máximo de cada campo, pela ordem em que têm de aparecer (ponto 4 da especificação).
_MAX_LENGTH: dict[str, int] = {
    **{"A": 9, "B": 30, "C": 12, "D": 2, "E": 1, "F": 8, "G": 60, "H": 70},
    **{k: 16 if k in _MONETARY else 5 for k in _TAX_KEYS},
    **{"L": 16, "M": 16, "N": 16, "O": 16, "P": 16, "Q": 4, "R": 4, "S": 65},
}
_ORDER = {key: i for i, key in enumerate(_MAX_LENGTH)}
_AMOUNT = re.compile(r"^-?\d+(\.\d{1,2})?$")
# ATCUD: código de validação da série (8 ou mais caracteres), hífen e número do documento.
_ATCUD = re.compile(r"^[A-Z0-9]{8,}-(\d+)$")
# Identificação do documento no SAF-T(PT): tipo, espaço, série, barra e número.
_DOCUMENT_ID = re.compile(r"^(\S+) \S+/(\d+)$")
_TAX_FIELDS = (
    "exempt_base",
    "reduced_base",
    "reduced_vat",
    "intermediate_base",
    "intermediate_vat",
    "normal_base",
    "normal_vat",
)


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

    def to_text(self) -> str:
        """O texto do código QR, pela ordem e com o formato da especificação.

        Valores ``None`` não entram (os campos opcionais sem informação não se criam), e
        sem espaços fiscais escreve ``I1:0``. Lança :class:`QRCodeError` se algum valor
        passar o tamanho máximo ou tiver um ``*``, ou se o último acabar em espaço.
        ``parse(fatura.to_text())`` devolve uma fatura igual a esta.
        """
        if len(self.taxes) > 3:
            raise QRCodeError("Só há três espaços fiscais (campos I, J e K)")
        fields: dict[str, str | Decimal | None] = {
            "A": self.issuer_nif,
            "B": self.buyer_nif,
            "C": self.buyer_country,
            "D": self.document_type,
            "E": self.document_status,
            "F": self.document_date.strftime("%Y%m%d"),
            "G": self.document_id,
            "H": self.atcud,
        }
        if not self.taxes:
            fields["I1"] = "0"
        for letter, tax in zip("IJK", self.taxes, strict=False):
            fields[f"{letter}1"] = tax.fiscal_space
            for i, name in enumerate(_TAX_FIELDS, start=2):
                fields[f"{letter}{i}"] = getattr(tax, name)
        fields |= {
            "L": self.non_taxable,
            "M": self.stamp_duty,
            "N": self.total_taxes,
            "O": self.total,
            "P": self.withholding,
            "Q": self.hash_chars,
            "R": self.certificate,
            "S": self.other_info,
        }
        text = "*".join(
            f"{key}:{value:.2f}" if isinstance(value, Decimal) else f"{key}:{value}"
            for key, value in fields.items()
            if value is not None
        )
        if text != text.strip():  # a leitura tira os espaços das pontas
            raise QRCodeError("O último campo não pode acabar em espaço")
        _split(text)  # mesmas regras de tamanho e formato que a leitura
        return text


def _split(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for part in text.strip().split("*"):
        key, sep, value = part.partition(":")
        if not sep or not key:
            raise QRCodeError(f"Campo sem o formato CHAVE:valor: {part!r}")
        if key in fields:
            raise QRCodeError(f"Campo repetido: {key}")
        if key not in _MAX_LENGTH:
            raise QRCodeError(f"Campo desconhecido: {key}")
        if len(value) > _MAX_LENGTH[key]:
            raise QRCodeError(
                f"O campo {key} passa o tamanho máximo ({_MAX_LENGTH[key]} caracteres): {value!r}"
            )
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
        values = {
            name: _amount(fields, f"{letter}{i}") for i, name in enumerate(_TAX_FIELDS, start=2)
        }
        result.append(TaxBreakdown(fiscal_space=space, **values))
    return tuple(result)


def parse(text: str) -> InvoiceQR:
    """Lê o texto de um código QR de fatura.

    Lança :class:`QRCodeError` se o texto estiver mal formado (campos desconhecidos,
    repetidos ou acima do tamanho máximo) ou faltarem campos obrigatórios. Aceita
    valores com menos de duas casas decimais e campos fora de ordem, e não confirma
    NIFs nem contas: isso fica para :func:`check`.
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

    Confirma a ordem dos campos, as duas casas decimais dos valores, os NIFs, o ATCUD
    (o número no fim tem de ser o do documento, em G) e as contas: o total de
    impostos (N) é o IVA mais o selo, e o total (O) é a soma das bases, do não
    sujeito (L) e dos impostos (N).
    """
    problems = []
    keys = list(invoice.fields)
    if keys != sorted(keys, key=_ORDER.__getitem__):
        problems.append("Os campos não estão pela ordem da especificação")
    problems += [
        f"O campo {key} devia ter duas casas decimais: {value}"
        for key, value in invoice.fields.items()
        if key in _MONETARY and not re.fullmatch(r"-?\d+\.\d\d", value)
    ]
    if not is_valid_nif(invoice.issuer_nif):
        problems.append(f"NIF do emitente inválido: {invoice.issuer_nif}")
    if invoice.buyer_country == "PT" and not is_valid_nif(invoice.buyer_nif):
        problems.append(f"NIF do adquirente inválido: {invoice.buyer_nif}")

    problems += _check_atcud(invoice)

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


def _check_atcud(invoice: InvoiceQR) -> list[str]:
    document = _DOCUMENT_ID.match(invoice.document_id)
    if document is None:
        return [f"Documento (G) sem o formato 'TIPO SÉRIE/NÚMERO': {invoice.document_id}"]
    problems = []
    if document[1] != invoice.document_type:
        problems.append(
            f"O documento (G) é do tipo {document[1]}, mas o tipo (D) é {invoice.document_type}"
        )
    if invoice.atcud == "0":  # sem ATCUD, como era permitido antes de ser obrigatório
        return problems
    atcud = _ATCUD.match(invoice.atcud)
    if atcud is None:
        problems.append(f"ATCUD (H) sem o formato 'CÓDIGO-NÚMERO': {invoice.atcud}")
    elif int(atcud[1]) != int(document[2]):
        problems.append(
            f"O ATCUD (H) acaba em {atcud[1]}, mas o documento (G) é o n.º {document[2]}"
        )
    return problems
