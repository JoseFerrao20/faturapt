"""Leitura do código QR a partir de um PDF (a fatura que chega por email).

Os programas de faturação desenham o QR no PDF (vetorial), por isso não basta procurar
imagens dentro do ficheiro: a página é desenhada como imagem e o QR é lido com
:func:`~faturapt.read_image`. Precisa das dependências opcionais:
``pip install 'faturapt[pdf]'``.
"""

from __future__ import annotations

import os
import threading

from .image import read_image
from .qr import InvoiceQR, QRCodeError

__all__ = ["read_pdf"]

_MISSING = "Para ler PDFs, instalar com: pip install 'faturapt[pdf]'"
_DPI = 300  # o QR tem de ter pelo menos 30 mm: a 300 dpi são mais de 350 píxeis
_MAX_SIDE = 4000  # píxeis: uma página fora do normal não ocupa memória sem limite

# O PDFium não pode ser usado por duas threads ao mesmo tempo (num servidor web, por exemplo).
_pdfium_lock = threading.Lock()


def read_pdf(pdf: str | os.PathLike[str] | bytes) -> InvoiceQR:
    """Encontra o código QR da fatura num PDF e lê-o com :func:`~faturapt.parse`.

    Aceita o caminho do ficheiro ou o conteúdo em ``bytes``. Procura na primeira e na
    última página, que é onde a especificação da AT deixa pôr o QR.

    Lança :class:`QRCodeError` se o ficheiro não for um PDF legível ou não tiver o QR de
    uma fatura, e ``ImportError`` se faltarem as dependências opcionais.
    """
    try:
        import pypdfium2 as pdfium
    except ImportError as exc:
        raise ImportError(_MISSING) from exc

    source = pdf if isinstance(pdf, bytes) else os.fspath(pdf)
    with _pdfium_lock:
        try:
            document = pdfium.PdfDocument(source)
        except pdfium.PdfiumError as exc:
            raise QRCodeError(f"O ficheiro não é um PDF legível ({exc})") from exc
        try:
            pages = sorted({0, len(document) - 1}) if len(document) else []
            images = []
            for index in pages:
                page = document[index]
                scale = min(_DPI / 72, _MAX_SIDE / max(page.get_size()))
                images.append(page.render(scale=scale).to_pil())
        finally:
            document.close()

    for image in images:
        try:
            return read_image(image)
        except QRCodeError:
            pass
    raise QRCodeError("Não encontrei o código QR da fatura na primeira nem na última página")
