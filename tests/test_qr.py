from datetime import date
from decimal import Decimal

import pytest

from faturapt import QRCodeError, check, parse
from faturapt.__main__ import main

# Exemplo das especificações técnicas da AT, com os três espaços fiscais.
FULL = (
    "A:123456789*B:999999990*C:PT*D:FT*E:N*F:20191231*G:FT AB2019/0035*H:CSDF7T5H-0035"
    "*I1:PT*I2:12000.00*I3:15000.00*I4:900.00*I5:50000.00*I6:6500.00*I7:80000.00*I8:18400.00"
    "*J1:PT-AC*J2:10000.00*J3:25000.56*J4:1000.02*J5:75000.00*J6:6750.00*J7:100000.00*J8:18000.00"
    "*K1:PT-MA*K2:5000.00*K3:12500.00*K4:625.00*K5:25000.00*K6:3000.00*K7:40000.00*K8:8800.00"
    "*L:100.00*M:25.00*N:64000.02*O:513600.58*P:100.00*Q:kLp0*R:9999"
    "*S:TB;PT00000000000000000000000;513500.58"
)

# Um talão de supermercado: só taxa normal, consumidor final.
SIMPLE = (
    "A:500000000*B:999999990*C:PT*D:FS*E:N*F:20261015*G:FS 01/1234*H:JJ3XY2KD-1234"
    "*I1:PT*I7:10.00*I8:2.30*N:2.30*O:12.30*Q:Ab1z*R:1234"
)


def test_parse_full() -> None:
    inv = parse(FULL)
    assert inv.issuer_nif == "123456789"
    assert inv.is_final_consumer
    assert inv.document_type_name == "Fatura"
    assert inv.document_date == date(2019, 12, 31)
    assert inv.atcud == "CSDF7T5H-0035"
    assert [t.fiscal_space for t in inv.taxes] == ["PT", "PT-AC", "PT-MA"]
    assert inv.taxes[1].reduced_base == Decimal("25000.56")
    assert inv.total == Decimal("513600.58")
    assert inv.withholding == Decimal("100.00")
    assert inv.other_info == "TB;PT00000000000000000000000;513500.58"
    assert check(inv) == []


def test_parse_simple() -> None:
    inv = parse(SIMPLE)
    assert inv.document_type_name == "Fatura simplificada"
    assert inv.taxes[0].normal_vat == Decimal("2.30")
    assert inv.taxes[0].reduced_base is None
    assert inv.stamp_duty is None
    assert check(inv) == []


def test_document_without_vat() -> None:
    text = SIMPLE.replace("*I1:PT*I7:10.00*I8:2.30*N:2.30*O:12.30", "*I1:0*L:10.00*N:0.00*O:10.00")
    inv = parse(text)
    assert inv.taxes == ()
    assert check(inv) == []


def test_unknown_document_type_is_kept() -> None:
    inv = parse(SIMPLE.replace("D:FS", "D:ZZ"))
    assert inv.document_type == "ZZ"
    assert inv.document_type_name is None


@pytest.mark.parametrize(
    ("text", "message"),
    [
        (SIMPLE.replace("*R:1234", ""), "Faltam campos obrigatórios: R"),
        (SIMPLE + "*A:123456789", "Campo repetido: A"),
        (SIMPLE + "*Z:1", "Campo desconhecido: Z"),
        (SIMPLE.replace("*Q:Ab1z", "*Qx"), "CHAVE:valor"),
        (SIMPLE.replace("F:20261015", "F:20261332"), "Data inválida"),
        (SIMPLE.replace("O:12.30", "O:12,30"), "campo O"),
        (SIMPLE.replace("Q:Ab1z", "Q:Ab1"), "4 caracteres"),
        (SIMPLE.replace("*I1:PT", ""), "Faltam campos obrigatórios: I1"),
        (SIMPLE.replace("I1:PT", "I1:0"), "I1 é 0"),
        (SIMPLE + "*J7:1.00", "sem o espaço fiscal J1"),
        ("", "CHAVE:valor"),
    ],
)
def test_malformed(text: str, message: str) -> None:
    with pytest.raises(QRCodeError, match=message):
        parse(text)


def test_check_finds_problems() -> None:
    text = SIMPLE.replace("A:500000000", "A:500000001").replace("N:2.30", "N:2.31")
    problems = check(parse(text))
    assert len(problems) == 3
    assert "NIF do emitente" in problems[0]
    assert "Total de impostos (N)" in problems[1]
    assert "Total (O)" in problems[2]


def test_check_invalid_buyer_nif() -> None:
    problems = check(parse(SIMPLE.replace("B:999999990", "B:999999991")))
    assert problems == ["NIF do adquirente inválido: 999999991"]


def test_foreign_buyer_nif_not_checked() -> None:
    inv = parse(SIMPLE.replace("B:999999990*C:PT", "B:ES12345678Z*C:ES"))
    assert check(inv) == []


def test_cli_ok(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([SIMPLE]) == 0
    out = capsys.readouterr().out
    assert '"total": "12.30"' in out
    assert '"document_date": "2026-10-15"' in out


def test_cli_problems_and_errors(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([SIMPLE.replace("O:12.30", "O:12.31")]) == 1
    assert main(["lixo"]) == 2
    assert "erro:" in capsys.readouterr().err


def test_cli_stdin(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    import io

    monkeypatch.setattr("sys.stdin", io.StringIO(SIMPLE + "\n"))
    assert main([]) == 0
