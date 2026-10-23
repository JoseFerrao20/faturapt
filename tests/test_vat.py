from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from faturapt import TaxBreakdown, check, check_vat, parse

from test_qr import AT_PRO_FORMA, AT_SIMPLIFIED, AT_TRANSPORT, FULL, SIMPLE


def invoice(space: str, day: date, **values: str):  # type: ignore[no-untyped-def]
    tax = TaxBreakdown(space, **{k: Decimal(v) for k, v in values.items()})
    return replace(parse(SIMPLE), document_date=day, taxes=(tax,))


@pytest.mark.parametrize("text", [FULL, AT_SIMPLIFIED, AT_PRO_FORMA, AT_TRANSPORT, SIMPLE])
def test_at_examples_have_the_right_vat(text: str) -> None:
    # Os exemplos da especificação da AT (2019) confirmam as taxas das três regiões.
    assert check_vat(parse(text)) == []


def test_wrong_rate() -> None:
    wrong = parse(
        SIMPLE.replace("I8:2.30", "I8:1.30")
        .replace("N:2.30", "N:1.30")
        .replace("O:12.30", "O:11.30")
    )
    assert check_vat(wrong) == [
        "IVA à taxa normal (PT, 23 %): a base 10.00 dá 2.30 de IVA, mas o QR tem 1.30"
    ]
    assert check(wrong) == []  # as contas batem certo: o aviso só vem do check_vat


@pytest.mark.parametrize(
    ("vat", "warns"),
    [
        ("23.00", False),
        ("23.23", False),  # arredondamentos linha a linha: até 1 % do IVA
        ("22.77", False),
        ("23.30", True),
        ("13.00", True),  # taxa intermédia no campo da normal
    ],
)
def test_tolerance_for_rounding(vat: str, warns: bool) -> None:
    day = date(2026, 1, 1)
    assert bool(check_vat(invoice("PT", day, normal_base="100.00", normal_vat=vat))) is warns


def test_small_amounts_tolerate_ten_cents() -> None:
    day = date(2026, 1, 1)
    assert check_vat(invoice("PT", day, reduced_base="1.00", reduced_vat="0.15")) == []
    assert check_vat(invoice("PT", day, reduced_base="1.00", reduced_vat="0.17")) != []


@pytest.mark.parametrize(
    ("day", "rate"),
    [(date(2021, 6, 30), "18.00"), (date(2021, 7, 1), "16.00"), (date(2026, 10, 1), "16.00")],
)
def test_azores_normal_rate_by_date(day: date, rate: str) -> None:
    assert check_vat(invoice("PT-AC", day, normal_base="100.00", normal_vat=rate)) == []
    other = "16.00" if rate == "18.00" else "18.00"
    assert check_vat(invoice("PT-AC", day, normal_base="100.00", normal_vat=other)) != []


@pytest.mark.parametrize(
    ("day", "rate"),
    [(date(2024, 9, 30), "5.00"), (date(2024, 10, 1), "4.00")],
)
def test_madeira_reduced_rate_by_date(day: date, rate: str) -> None:
    assert check_vat(invoice("PT-MA", day, reduced_base="100.00", reduced_vat=rate)) == []
    other = "4.00" if rate == "5.00" else "5.00"
    [warning] = check_vat(invoice("PT-MA", day, reduced_base="100.00", reduced_vat=other))
    assert warning.startswith(f"IVA à taxa reduzida (PT-MA, {rate[0]} %)")


@pytest.mark.parametrize(
    ("space", "day"),
    [("PT", date(2018, 12, 31)), ("ES", date(2026, 1, 1))],
)
def test_no_warnings_outside_the_table(space: str, day: date) -> None:
    assert check_vat(invoice(space, day, normal_base="100.00", normal_vat="1.00")) == []


def test_base_without_vat_is_not_checked() -> None:
    assert check_vat(invoice("PT", date(2026, 1, 1), normal_base="100.00")) == []
