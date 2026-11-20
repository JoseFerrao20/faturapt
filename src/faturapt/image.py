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
    (por exemplo, o QR de um site ao lado), devolve o primeiro que seja de uma fatura. Se
    não o encontrar, tenta de novo com outro binário do zxing (``GlobalHistogram``), que lê
    fotografias de talões com pouco contraste onde o binário por omissão falha.

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

    formats = zxingcpp.BarcodeFormats(zxingcpp.BarcodeFormat.QRCode)
    errors: dict[str, str] = {}  # texto de cada QR que não é de uma fatura -> o porquê
    # O binário por omissão do zxing (LocalAverage) não encontra o QR em algumas fotografias
    # de talões (papel térmico, pouco contraste) que o GlobalHistogram lê. O segundo só é
    # tentado quando o primeiro não encontra o QR da fatura: o que já se lia não muda.
    for binarizer in (zxingcpp.Binarizer.LocalAverage, zxingcpp.Binarizer.GlobalHistogram):
        for code in zxingcpp.read_barcodes(picture, formats=formats, binarizer=binarizer):
            if code.text in errors:
                continue
            try:
                return parse(code.text)
            except QRCodeError as exc:
                errors[code.text] = str(exc)
    if not errors:
        raise QRCodeError("Não encontrei nenhum código QR na imagem")
    raise QRCodeError(
        f"Há {len(errors)} código(s) QR na imagem, mas nenhum é de uma fatura"
        f" ({next(iter(errors.values()))})"
    )
