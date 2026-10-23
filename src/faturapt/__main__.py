"""``faturapt "A:...*B:..."``, ``faturapt -i talao.jpg`` ou ``faturapt -i fatura.pdf``: mostra
a fatura em JSON e os problemas encontrados."""

from __future__ import annotations

import argparse
import json
import sys

from .image import read_image
from .pdf import read_pdf
from .qr import QRCodeError, check, parse
from .vat import check_vat


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="faturapt", description=__doc__)
    source = parser.add_mutually_exclusive_group()
    source.add_argument("qr", nargs="?", help="texto do código QR (por omissão, lido do stdin)")
    source.add_argument(
        "-i",
        "--imagem",
        help="fotografia, digitalização ou PDF da fatura (precisa de faturapt[image] ou [pdf])",
    )
    args = parser.parse_args(argv)

    try:
        if args.imagem is not None:
            with open(args.imagem, "rb") as file:
                is_pdf = file.read(5) == b"%PDF-"
            invoice = read_pdf(args.imagem) if is_pdf else read_image(args.imagem)
        else:
            invoice = parse(args.qr if args.qr is not None else sys.stdin.read())
    except (QRCodeError, ImportError, OSError) as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 2

    data = invoice.to_dict()
    data["problems"] = check(invoice)
    data["warnings"] = check_vat(invoice)  # só avisos: não mudam o código de saída
    print(json.dumps(data, ensure_ascii=False, indent=2))
    return 1 if data["problems"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
