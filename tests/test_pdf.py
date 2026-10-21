import io
import sys
import threading
from pathlib import Path

import pytest

pytest.importorskip("pypdfium2")
from reportlab.graphics import renderPDF
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from faturapt import QRCodeError, read_pdf
from faturapt.__main__ import main

from test_qr import FULL, SIMPLE


def make_pdf(*pages: str | None) -> bytes:
    """Um PDF como os dos programas de faturação: texto e o QR desenhado (vetorial), 30 mm."""
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    for qr in pages:
        pdf.drawString(60, 780, "Fatura")
        if qr is not None:
            widget = QrCodeWidget(qr, barLevel="M")
            x0, y0, x1, y1 = widget.getBounds()
            size = 85  # pontos: 30 mm, o mínimo da especificação
            drawing = Drawing(
                size, size, transform=[size / (x1 - x0), 0, 0, size / (y1 - y0), 0, 0]
            )
            drawing.add(widget)
            renderPDF.draw(drawing, pdf, 60, 60)
        pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def test_vector_qr() -> None:
    assert read_pdf(make_pdf(FULL)).to_text() == FULL


def test_qr_on_the_last_page(tmp_path: Path) -> None:
    path = tmp_path / "fatura.pdf"
    path.write_bytes(make_pdf(None, None, SIMPLE))
    assert read_pdf(path).to_text() == SIMPLE
    assert read_pdf(str(path)).to_text() == SIMPLE


def test_qr_only_in_the_middle_is_not_searched() -> None:
    # A especificação diz primeira ou última página; as outras não são desenhadas.
    with pytest.raises(QRCodeError, match="primeira nem na última"):
        read_pdf(make_pdf(None, SIMPLE, None))


def test_other_qr_is_skipped() -> None:
    with pytest.raises(QRCodeError, match="Não encontrei o código QR da fatura"):
        read_pdf(make_pdf("https://exemplo.pt"))


def test_not_a_pdf() -> None:
    with pytest.raises(QRCodeError, match="não é um PDF legível"):
        read_pdf(b"isto nao e um pdf")


def test_concurrent_reads() -> None:
    pdf = make_pdf(SIMPLE)
    results: list[str] = []
    threads = [
        threading.Thread(target=lambda: results.append(read_pdf(pdf).to_text())) for _ in range(4)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert results == [SIMPLE] * 4


def test_missing_optional_dependencies(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "pypdfium2", None)
    with pytest.raises(ImportError, match=r"faturapt\[pdf\]"):
        read_pdf(b"%PDF-")


def test_cli_detects_pdf(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "fatura"  # sem extensão: conta o conteúdo, não o nome
    path.write_bytes(make_pdf(SIMPLE))
    assert main(["-i", str(path)]) == 0
    assert '"total": "12.30"' in capsys.readouterr().out
