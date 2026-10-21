import io
import sys
from pathlib import Path

import pytest

pytest.importorskip("zxingcpp")
import segno
from PIL import Image, ImageFilter

from faturapt import QRCodeError, read_image
from faturapt.__main__ import main

from test_qr import FULL, SIMPLE


def qr_image(text: str, scale: int = 4) -> Image.Image:
    # O segno gera o QR; assim o leitor (zxing) não é testado com o seu próprio escritor.
    buffer = io.BytesIO()
    segno.make(text, error="m", micro=False).save(buffer, kind="png", scale=scale, border=4)
    return Image.open(buffer).convert("RGB")


def photo(*codes: Image.Image) -> Image.Image:
    """Uma "fotografia" de um talão: página grande, QR pequenos, rodada, desfocada e em JPEG."""
    page = Image.new("RGB", (1600, 2200), "white")
    for i, code in enumerate(codes):
        page.paste(code, (200 + i * 700, 1400))
    page = page.rotate(7, expand=True, fillcolor="gray").filter(ImageFilter.GaussianBlur(1))
    buffer = io.BytesIO()
    page.save(buffer, format="JPEG", quality=60)
    return Image.open(io.BytesIO(buffer.getvalue()))


def test_bytes() -> None:
    buffer = io.BytesIO()
    qr_image(SIMPLE).save(buffer, format="PNG")
    assert read_image(buffer.getvalue()).to_text() == SIMPLE


def test_path(tmp_path: Path) -> None:
    path = tmp_path / "fatura.jpg"
    qr_image(FULL).save(path)
    assert read_image(path).to_text() == FULL
    assert read_image(str(path)).total == read_image(path).total


def test_photo_of_a_receipt() -> None:
    assert read_image(photo(qr_image(FULL, scale=3))).to_text() == FULL


def test_exif_orientation() -> None:
    buffer = io.BytesIO()
    exif = Image.Exif()
    exif[0x0112] = 6  # o telemóvel guardou a fotografia deitada
    qr_image(SIMPLE).rotate(90, expand=True).save(buffer, format="JPEG", exif=exif)
    assert read_image(buffer.getvalue()).to_text() == SIMPLE


def test_skips_other_qr_codes() -> None:
    image = photo(qr_image("https://exemplo.pt/promocoes"), qr_image(SIMPLE))
    assert read_image(image).to_text() == SIMPLE


def test_only_other_qr_codes() -> None:
    with pytest.raises(QRCodeError, match=r"Há 1 código\(s\) QR na imagem, mas nenhum"):
        read_image(qr_image("https://exemplo.pt"))


def test_no_qr_code() -> None:
    with pytest.raises(QRCodeError, match="Não encontrei nenhum código QR"):
        read_image(Image.new("L", (400, 400), "white"))


def test_missing_optional_dependencies(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "zxingcpp", None)
    with pytest.raises(ImportError, match=r"faturapt\[image\]"):
        read_image(b"")


def test_cli(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "talão.png"
    qr_image(SIMPLE).save(path)
    assert main(["--imagem", str(path)]) == 0
    assert '"total": "12.30"' in capsys.readouterr().out
    assert main(["-i", str(tmp_path / "nao-existe.png")]) == 2
    assert "erro:" in capsys.readouterr().err
