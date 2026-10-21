"""Validação do NIF (Número de Identificação Fiscal) português."""

from __future__ import annotations

from enum import Enum

__all__ = ["InvalidNIF", "NifType", "is_valid_nif", "nif_type", "normalize_nif"]


class InvalidNIF(ValueError):
    """O valor não é um NIF português válido."""


class NifType(str, Enum):
    """Tipo de contribuinte, pelo prefixo do NIF."""

    INDIVIDUAL = "pessoa singular"
    NON_RESIDENT_INDIVIDUAL = "pessoa singular não residente"
    COMPANY = "pessoa coletiva"
    PUBLIC_ADMINISTRATION = "administração pública"
    UNDIVIDED_INHERITANCE = "herança indivisa"
    NON_RESIDENT_COMPANY = "pessoa coletiva não residente"
    INVESTMENT_FUND = "fundo de investimento"
    OFFICIAL_ASSIGNMENT = "atribuição oficiosa"
    EXCEPTIONAL_REGIME = "regime excecional"
    SOLE_TRADER = "empresário em nome individual"
    CONDOMINIUM_OR_IRREGULAR = "condomínio ou sociedade irregular"
    NON_RESIDENT_NO_ESTABLISHMENT = "não residente sem estabelecimento estável"
    CIVIL_PARTNERSHIP = "sociedade civil sem personalidade jurídica"


# Prefixos de dois dígitos primeiro: "45" tem de ganhar a "4" (que não existe sozinho).
_PREFIXES: tuple[tuple[str, NifType], ...] = (
    ("45", NifType.NON_RESIDENT_INDIVIDUAL),
    ("70", NifType.UNDIVIDED_INHERITANCE),
    ("71", NifType.NON_RESIDENT_COMPANY),
    ("72", NifType.INVESTMENT_FUND),
    ("74", NifType.UNDIVIDED_INHERITANCE),
    ("75", NifType.UNDIVIDED_INHERITANCE),
    ("77", NifType.OFFICIAL_ASSIGNMENT),
    ("79", NifType.EXCEPTIONAL_REGIME),
    ("90", NifType.CONDOMINIUM_OR_IRREGULAR),
    ("91", NifType.CONDOMINIUM_OR_IRREGULAR),
    ("98", NifType.NON_RESIDENT_NO_ESTABLISHMENT),
    ("99", NifType.CIVIL_PARTNERSHIP),
    ("1", NifType.INDIVIDUAL),
    ("2", NifType.INDIVIDUAL),
    ("3", NifType.INDIVIDUAL),
    ("5", NifType.COMPANY),
    ("6", NifType.PUBLIC_ADMINISTRATION),
    ("8", NifType.SOLE_TRADER),
)


def normalize_nif(value: str | int) -> str:
    """Tira espaços, pontos, hífenes e o prefixo ``PT``.

    Não valida: ``normalize_nif(" PT 123 456 789 ")`` dá ``"123456789"``.
    """
    text = str(value).strip().upper()
    if text.startswith("PT"):
        text = text[2:]
    return "".join(ch for ch in text if ch not in " .-")


def _check_digit(first_eight: str) -> int:
    total = sum(int(d) * w for d, w in zip(first_eight, range(9, 1, -1), strict=True))
    remainder = total % 11
    return 0 if remainder < 2 else 11 - remainder


def nif_type(value: str | int) -> NifType:
    """Devolve o tipo de contribuinte, ou lança :class:`InvalidNIF`."""
    nif = normalize_nif(value)
    if len(nif) != 9 or not nif.isdigit():
        raise InvalidNIF(f"O NIF tem de ter 9 dígitos: {value!r}")
    kind = next((t for prefix, t in _PREFIXES if nif.startswith(prefix)), None)
    if kind is None:
        raise InvalidNIF(f"O NIF começa por um prefixo que não existe: {value!r}")
    if int(nif[8]) != _check_digit(nif[:8]):
        raise InvalidNIF(f"O dígito de controlo do NIF não confere: {value!r}")
    return kind


def is_valid_nif(value: str | int) -> bool:
    """``True`` se o valor (depois de :func:`normalize_nif`) for um NIF válido."""
    try:
        nif_type(value)
    except InvalidNIF:
        return False
    return True
