"""Ponte entre a página de demonstração e o faturapt.

Corre no browser, com o Pyodide: a página chama ``analyse`` com o texto de um QR e recebe
JSON. Os testes (``tests/test_site.py``) correm o mesmo ficheiro no Python normal.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date
from decimal import Decimal

import faturapt


def _plain(value: object) -> str:
    if isinstance(value, Decimal):
        return f"{value:.2f}"
    if isinstance(value, date):
        return value.isoformat()
    raise TypeError(type(value).__name__)


def analyse(text: str) -> str:
    """A fatura em JSON, com os problemas do ``check``, ou ``{"error": ...}``."""
    try:
        invoice = faturapt.parse(text)
    except faturapt.QRCodeError as exc:
        return json.dumps({"error": str(exc)}, ensure_ascii=False)

    data = asdict(invoice)
    data.pop("fields")
    data["document_type_name"] = invoice.document_type_name
    data["is_final_consumer"] = invoice.is_final_consumer
    try:
        data["issuer_type"] = faturapt.nif_type(invoice.issuer_nif).value
    except faturapt.InvalidNIF:
        data["issuer_type"] = None
    data["problems"] = faturapt.check(invoice)
    data["version"] = faturapt.__version__
    return json.dumps(data, default=_plain, ensure_ascii=False)
