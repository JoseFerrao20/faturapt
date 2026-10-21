import pytest

from faturapt import InvalidNIF, NifType, is_valid_nif, nif_type, normalize_nif


@pytest.mark.parametrize(
    ("nif", "kind"),
    [
        ("123456789", NifType.INDIVIDUAL),
        ("500000000", NifType.COMPANY),
        ("999999990", NifType.CIVIL_PARTNERSHIP),
        ("PT 123 456 789", NifType.INDIVIDUAL),
        (123456789, NifType.INDIVIDUAL),
    ],
)
def test_valid(nif: str | int, kind: NifType) -> None:
    assert is_valid_nif(nif)
    assert nif_type(nif) is kind


def test_two_digit_prefix_wins() -> None:
    # 45 é não residente; o 4 sozinho não é um prefixo.
    assert nif_type("450000001") is NifType.NON_RESIDENT_INDIVIDUAL


@pytest.mark.parametrize(
    ("nif", "message"),
    [
        ("123456780", "dígito de controlo"),
        ("12345678", "9 dígitos"),
        ("12345678A", "9 dígitos"),
        ("400000000", "prefixo"),
        ("", "9 dígitos"),
    ],
)
def test_invalid(nif: str, message: str) -> None:
    assert not is_valid_nif(nif)
    with pytest.raises(InvalidNIF, match=message):
        nif_type(nif)


def test_check_digit_zero_when_remainder_is_one() -> None:
    # 1*9 + 7*2 = 23, e 23 % 11 = 1: o dígito é 0, não 10.
    assert is_valid_nif("100000070")


def test_normalize() -> None:
    assert normalize_nif(" pt 123.456-789 ") == "123456789"
