"""Leitura e validação do código QR das faturas portuguesas e de NIFs."""

from .nif import InvalidNIF, NifType, is_valid_nif, nif_type, normalize_nif
from .qr import DOCUMENT_TYPES, InvoiceQR, QRCodeError, TaxBreakdown, check, parse

__all__ = [
    "DOCUMENT_TYPES",
    "InvalidNIF",
    "InvoiceQR",
    "NifType",
    "QRCodeError",
    "TaxBreakdown",
    "check",
    "is_valid_nif",
    "nif_type",
    "normalize_nif",
    "parse",
]

__version__ = "0.1.0"
