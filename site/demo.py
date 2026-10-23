"""Ponte entre a página de demonstração e o faturapt.

Corre no browser, com o Pyodide: a página chama ``analyse`` com o texto de um QR e recebe
JSON. Os testes (``tests/test_site.py``) correm o mesmo ficheiro no Python normal.
"""

from __future__ import annotations

import json

import faturapt


def analyse(text: str) -> str:
    """A fatura em JSON, com os problemas do ``check``, ou ``{"error": ...}``."""
    try:
        invoice = faturapt.parse(text)
    except faturapt.QRCodeError as exc:
        return json.dumps({"error": str(exc)}, ensure_ascii=False)

    data = invoice.to_dict()
    try:
        data["issuer_type"] = faturapt.nif_type(invoice.issuer_nif).value
    except faturapt.InvalidNIF:
        data["issuer_type"] = None
    data["problems"] = faturapt.check(invoice)
    data["warnings"] = faturapt.check_vat(invoice)
    data["version"] = faturapt.__version__
    return json.dumps(data, ensure_ascii=False)
