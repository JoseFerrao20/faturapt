"""A ponte da página de demonstração (``site/demo.py``), corrida no Python normal."""

import importlib.util
import json
from pathlib import Path
from types import ModuleType

from test_qr import AT_TRANSPORT, FULL, SIMPLE


def load_demo() -> ModuleType:
    path = Path(__file__).parent.parent / "site" / "demo.py"
    spec = importlib.util.spec_from_file_location("demo", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


demo = load_demo()


def analyse(text: str) -> dict[str, object]:
    result: dict[str, object] = json.loads(demo.analyse(text))
    return result


def test_valid_invoice() -> None:
    data = analyse(FULL)
    assert data["problems"] == []
    assert data["total"] == "513600.58"
    assert data["document_date"] == "2019-12-31"
    assert data["document_type_name"] == "Fatura"
    assert data["issuer_type"] == "pessoa singular"
    assert data["is_final_consumer"] is True
    assert len(data["taxes"]) == 3  # type: ignore[arg-type]


def test_amounts_keep_two_decimals() -> None:
    data = analyse(AT_TRANSPORT)
    assert data["total"] == "0.00"
    assert data["taxes"] == []


def test_problems_are_listed() -> None:
    data = analyse(SIMPLE.replace("O:12.30", "O:12.31"))
    assert data["problems"] == ["Total (O) é 12.31, mas bases + não sujeito + impostos dá 12.30"]


def test_invalid_issuer_nif_has_no_type() -> None:
    data = analyse(SIMPLE.replace("A:500000000", "A:500000001"))
    assert data["issuer_type"] is None


def test_not_an_invoice() -> None:
    assert analyse("https://exemplo.pt") == {"error": "Campo desconhecido: https"}
