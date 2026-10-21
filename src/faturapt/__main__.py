"""``faturapt "A:...*B:..."``: mostra a fatura em JSON e os problemas encontrados."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import date
from decimal import Decimal
from typing import Any

from .qr import QRCodeError, check, parse


def _json(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, date):
        return value.isoformat()
    raise TypeError(type(value).__name__)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="faturapt", description=__doc__)
    parser.add_argument("qr", nargs="?", help="texto do código QR (por omissão, lido do stdin)")
    args = parser.parse_args(argv)
    text = args.qr if args.qr is not None else sys.stdin.read()

    try:
        invoice = parse(text)
    except QRCodeError as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 2

    data = asdict(invoice)
    data.pop("fields")
    data["document_type_name"] = invoice.document_type_name
    data["problems"] = check(invoice)
    print(json.dumps(data, default=_json, ensure_ascii=False, indent=2))
    return 1 if data["problems"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
