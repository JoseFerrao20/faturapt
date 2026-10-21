from datetime import date
from decimal import Decimal

import pytest

from faturapt import QRCodeError, check, parse
from faturapt.__main__ import main

# Os quatro exemplos das especificações técnicas da AT (versão 1.0, ponto 5).
FULL = (
    "A:123456789*B:999999990*C:PT*D:FT*E:N*F:20191231*G:FT AB2019/0035*H:CSDF7T5H-0035"
    "*I1:PT*I2:12000.00*I3:15000.00*I4:900.00*I5:50000.00*I6:6500.00*I7:80000.00*I8:18400.00"
    "*J1:PT-AC*J2:10000.00*J3:25000.56*J4:1000.02*J5:75000.00*J6:6750.00*J7:100000.00*J8:18000.00"
    "*K1:PT-MA*K2:5000.00*K3:12500.00*K4:625.00*K5:25000.00*K6:3000.00*K7:40000.00*K8:8800.00"
    "*L:100.00*M:25.00*N:64000.02*O:513600.58*P:100.00*Q:kLp0*R:9999"
    "*S:TB;PT00000000000000000000000;513500.58"
)

AT_SIMPLIFIED = (
    "A:123456789*B:999999990*C:PT*D:FS*E:N*F:20190812*G:FS CDVF/12345*H:CDF7T5HD-12345"
    "*I1:PT*I7:0.65*I8:0.15*N:0.15*O:0.80*Q:YhGV*R:9999*S:NU;0.80"
)
AT_PRO_FORMA = (
    "A:500000000*B:123456789*C:PT*D:PF*E:N*F:20190123*G:PF G2019CB/145789*H:HB6FT7RV-145789"
    "*I1:PT*I2:12345.34*I3:12532.65*I4:751.96*I5:52789.00*I6:6862.57*I7:32425.69*I8:7457.91"
    "*N:15072.44*O:125165.12*Q:r/fY*R:9999"
)
AT_TRANSPORT = (
    "A:500000000*B:123456789*C:PT*D:GT*E:N*F:20190720*G:GT G234CB/50987*H:GTVX4Y8B-50987"
    "*I1:0*N:0.00*O:0.00*Q:5uIg*R:9999"
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


@pytest.mark.parametrize("text", [FULL, AT_SIMPLIFIED, AT_PRO_FORMA, AT_TRANSPORT])
def test_at_examples_are_valid(text: str) -> None:
    assert check(parse(text)) == []


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
        (SIMPLE.replace("Q:Ab1z", "Q:Ab1z9"), "tamanho máximo \\(4"),
        (SIMPLE.replace("A:500000000", "A:PT500000000"), "campo A passa"),
        (SIMPLE + "*S:" + "x" * 66, "campo S passa"),
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


def test_check_order_and_decimals() -> None:
    text = SIMPLE.replace("*Q:Ab1z*R:1234", "*R:1234*Q:Ab1z").replace("O:12.30", "O:12.3")
    assert check(parse(text)) == [
        "Os campos não estão pela ordem da especificação",
        "O campo O devia ter duas casas decimais: 12.3",
    ]


@pytest.mark.parametrize(
    ("old", "new", "problem"),
    [
        (
            "H:JJ3XY2KD-1234",
            "H:JJ3XY2KD-1235",
            "O ATCUD (H) acaba em 1235, mas o documento (G) é o n.º 1234",
        ),
        ("H:JJ3XY2KD-1234", "H:JJ3-1234", "ATCUD (H) sem o formato 'CÓDIGO-NÚMERO': JJ3-1234"),
        ("G:FS 01/1234", "G:FT 01/1234", "O documento (G) é do tipo FT, mas o tipo (D) é FS"),
        ("G:FS 01/1234", "G:FS-1234", "Documento (G) sem o formato 'TIPO SÉRIE/NÚMERO': FS-1234"),
    ],
)
def test_check_atcud(old: str, new: str, problem: str) -> None:
    assert check(parse(SIMPLE.replace(old, new))) == [problem]


def test_atcud_zero_is_accepted() -> None:
    assert check(parse(SIMPLE.replace("H:JJ3XY2KD-1234", "H:0"))) == []


def test_atcud_leading_zeros_match() -> None:
    assert check(parse(SIMPLE.replace("H:JJ3XY2KD-1234", "H:JJ3XY2KD-01234"))) == []


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
