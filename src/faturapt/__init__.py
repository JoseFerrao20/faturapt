"""Leitura e validação do código QR das faturas portuguesas e de NIFs."""

from .image import read_image
from .nif import InvalidNIF, NifType, is_valid_nif, nif_type, normalize_nif
from .pdf import read_pdf
from .qr import DOCUMENT_TYPES, InvoiceQR, QRCodeError, TaxBreakdown, check, parse
from .vat import check_vat

__all__ = [
    "DOCUMENT_TYPES",
    "InvalidNIF",
    "InvoiceQR",
    "NifType",
    "QRCodeError",
    "TaxBreakdown",
    "check",
    "check_vat",
    "is_valid_nif",
    "nif_type",
    "normalize_nif",
    "parse",
    "read_image",
    "read_pdf",
]

__version__ = "0.3.0"
