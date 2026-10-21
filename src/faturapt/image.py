"""Leitura do código QR a partir de uma imagem (fotografia ou digitalização da fatura).

Precisa das dependências opcionais: ``pip install 'faturapt[image]'``.
"""

from __future__ import annotations

import io
import os
from typing import TYPE_CHECKING

from .qr import InvoiceQR, QRCodeError, parse

if TYPE_CHECKING:
    from PIL.Image import Image

__all__ = ["read_image"]

_MISSING = "Para ler imagens, instalar com: pip install 'faturapt[image]'"


def read_image(image: str | os.PathLike[str] | bytes | Image) -> InvoiceQR:
    """Encontra o código QR da fatura numa imagem e lê-o com :func:`parse`.

    Aceita o caminho de um ficheiro, o conteúdo em ``bytes`` ou uma imagem do Pillow.
    Respeita a orientação EXIF das fotografias do telemóvel. Se houver vários códigos
    (por exemplo, o QR de um site ao lado), devolve o primeiro que seja de uma fatura.

    Lança :class:`QRCodeError` se não houver nenhum QR de fatura na imagem, e
    ``ImportError`` se faltarem as dependências opcionais.
    """
    try:
        import zxingcpp
        from PIL import Image as PILImage
        from PIL import ImageOps
    except ImportError as exc:
        raise ImportError(_MISSING) from exc

    picture: Image
    if isinstance(image, bytes):
        picture = PILImage.open(io.BytesIO(image))
    elif isinstance(image, (str, os.PathLike)):
        picture = PILImage.open(image)
    else:
        picture = image
    picture = ImageOps.exif_transpose(picture).convert("L")

    codes = zxingcpp.read_barcodes(
        picture, formats=zxingcpp.BarcodeFormats(zxingcpp.BarcodeFormat.QRCode)
    )
    if not codes:
        raise QRCodeError("Não encontrei nenhum código QR na imagem")
    errors = []
    for code in codes:
        try:
            return parse(code.text)
        except QRCodeError as exc:
            errors.append(str(exc))
    raise QRCodeError(
        f"Há {len(codes)} código(s) QR na imagem, mas nenhum é de uma fatura ({errors[0]})"
    )
