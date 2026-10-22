import json
from datetime import date
from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from faturapt import InvoiceQR, QRCodeError, TaxBreakdown, check, parse

from test_qr import AT_PRO_FORMA, AT_SIMPLIFIED, AT_TRANSPORT, FULL, SIMPLE


@pytest.mark.parametrize("text", [FULL, AT_SIMPLIFIED, AT_PRO_FORMA, AT_TRANSPORT, SIMPLE])
def test_to_text_gives_back_the_original(text: str) -> None:
    assert parse(text).to_text() == text


def test_to_text_from_scratch() -> None:
    invoice = InvoiceQR(
        issuer_nif="500000000",
        buyer_nif="999999990",
        buyer_country="PT",
        document_type="FS",
        document_status="N",
        document_date=date(2026, 10, 15),
        document_id="FS 01/1234",
        atcud="JJ3XY2KD-1234",
        taxes=(TaxBreakdown("PT", normal_base=Decimal(10), normal_vat=Decimal("2.3")),),
        total_taxes=Decimal("2.3"),
        total=Decimal("12.3"),
        hash_chars="Ab1z",
        certificate="1234",
    )
    assert invoice.to_text() == SIMPLE
    assert check(parse(invoice.to_text())) == []


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"other_info": "a*b"}, "CHAVE:valor"),
        ({"document_id": "x" * 61}, "campo G passa"),
        ({"taxes": (TaxBreakdown("PT"),) * 4}, "três espaços fiscais"),
        ({"other_info": "pago "}, "acabar em espaço"),
    ],
)
def test_to_text_rejects(changes: dict[str, object], message: str) -> None:
    from dataclasses import replace

    with pytest.raises(QRCodeError, match=message):
        replace(parse(SIMPLE), **changes).to_text()  # type: ignore[arg-type]


amounts = st.decimals(min_value=0, max_value=10**9, places=2, allow_nan=False)
optional = st.none() | amounts
tax = st.builds(
    TaxBreakdown,
    fiscal_space=st.sampled_from(["PT", "PT-AC", "PT-MA"]),
    exempt_base=optional,
    reduced_base=optional,
    reduced_vat=optional,
    intermediate_base=optional,
    intermediate_vat=optional,
    normal_base=optional,
    normal_vat=optional,
)
text = st.text(st.characters(codec="ascii", exclude_characters="*", min_codepoint=32), min_size=1)
invoices = st.builds(
    InvoiceQR,
    issuer_nif=st.from_regex(r"[0-9]{9}", fullmatch=True),
    buyer_nif=st.from_regex(r"[0-9A-Z]{1,30}", fullmatch=True),
    buyer_country=st.sampled_from(["PT", "ES", "Desconhecido"]),
    document_type=st.sampled_from(["FT", "FS", "FR", "NC", "GT"]),
    document_status=st.sampled_from(["N", "A"]),
    document_date=st.dates(min_value=date(2000, 1, 1), max_value=date(2099, 12, 31)),
    document_id=text.filter(lambda s: len(s) <= 60),
    atcud=text.filter(lambda s: len(s) <= 70),
    taxes=st.lists(tax, max_size=3).map(tuple),
    total_taxes=amounts,
    total=amounts,
    hash_chars=st.from_regex(r"[A-Za-z0-9/+]{4}", fullmatch=True),
    certificate=st.from_regex(r"[0-9]{1,4}", fullmatch=True),
    non_taxable=optional,
    stamp_duty=optional,
    withholding=optional,
    other_info=st.none() | text.filter(lambda s: len(s) <= 65 and s == s.rstrip()),
)


@given(invoices)
def test_round_trip(invoice: InvoiceQR) -> None:
    assert parse(invoice.to_text()) == invoice


@given(invoices)
def test_dict_round_trip(invoice: InvoiceQR) -> None:
    # Também através do JSON, como faz quem usa o dicionário noutra linguagem.
    data = json.loads(json.dumps(invoice.to_dict()))
    assert InvoiceQR.from_dict(data) == invoice


def test_to_dict() -> None:
    assert parse(SIMPLE).to_dict() == {
        "issuer_nif": "500000000",
        "buyer_nif": "999999990",
        "buyer_country": "PT",
        "document_type": "FS",
        "document_status": "N",
        "document_date": "2026-10-15",
        "document_id": "FS 01/1234",
        "atcud": "JJ3XY2KD-1234",
        "taxes": [
            {
                "fiscal_space": "PT",
                "exempt_base": None,
                "reduced_base": None,
                "reduced_vat": None,
                "intermediate_base": None,
                "intermediate_vat": None,
                "normal_base": "10.00",
                "normal_vat": "2.30",
            }
        ],
        "total_taxes": "2.30",
        "total": "12.30",
        "hash_chars": "Ab1z",
        "certificate": "1234",
        "non_taxable": None,
        "stamp_duty": None,
        "withholding": None,
        "other_info": None,
        "document_type_name": "Fatura simplificada",
        "is_final_consumer": True,
    }


def test_from_dict_fills_the_raw_fields() -> None:
    # Passa pelo texto do QR: fica como se tivesse sido lido, e o check funciona.
    invoice = InvoiceQR.from_dict(parse(FULL).to_dict())
    assert invoice.fields == parse(FULL).fields
    assert check(invoice) == []


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"document_date": None}, "Valor inválido"),
        ({"document_date": "31-12-2019"}, "Valor inválido"),
        ({"total": 12.3}, 'os valores vêm em texto, como "12.30"'),
        ({"total": "doze"}, "'doze' não é um valor"),
        ({"taxes": [{"normal_base": "10.00"}]}, "Falta o campo 'fiscal_space'"),
        ({"issuer_nif": None}, "Faltam campos obrigatórios: A"),
        ({"hash_chars": "Ab1"}, "4 caracteres do hash"),
        ({"total": None}, "não podem ser null"),
    ],
)
def test_from_dict_rejects(changes: dict[str, object], message: str) -> None:
    with pytest.raises(QRCodeError, match=message):
        InvoiceQR.from_dict(parse(SIMPLE).to_dict() | changes)


@pytest.mark.parametrize("key", ["issuer_nif", "document_date", "taxes", "total"])
def test_from_dict_requires_the_fields(key: str) -> None:
    data = parse(SIMPLE).to_dict()
    del data[key]
    with pytest.raises(QRCodeError, match=f"Falta o campo '{key}'"):
        InvoiceQR.from_dict(data)
