"""Cryptographic audit hashing and input security validation.

Provides tamper-evident SHA-256 hashing for ISO 9001 auditability, magic-byte
file type verification, dimension limits against decompression bombs, and CSV
formula injection neutralization.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
from typing import Optional

from PIL import Image

MAX_IMAGE_DIMENSION = 4096

_IMAGE_MAGIC_SIGNATURES: list[tuple[bytes, str]] = [
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\x89PNG", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
    (b"BM", "image/bmp"),
    (b"II*\x00", "image/tiff"),
    (b"MM\x00*", "image/tiff"),
]

_PDF_MAGIC = b"%PDF-"


class SecurityValidationError(ValueError):
    """Raised when an uploaded file violates security or format policies."""


def validate_image_security(
    image_bytes: bytes,
    filename: Optional[str] = None,
    max_dimension: int = MAX_IMAGE_DIMENSION,
) -> str:
    """Validate image magic bytes and ensure dimensions are within safe bounds.

    Returns the detected MIME type if valid, otherwise raises SecurityValidationError.
    """
    if not image_bytes:
        raise SecurityValidationError("Image file is empty (0 bytes).")

    # 1. Magic bytes check
    is_valid_magic = False
    detected_mime = "image/octet-stream"

    for sig, mime in _IMAGE_MAGIC_SIGNATURES:
        if image_bytes.startswith(sig):
            is_valid_magic = True
            detected_mime = mime
            break

    # Also handle WebP (RIFF .... WEBP)
    if not is_valid_magic and len(image_bytes) >= 12:
        if image_bytes[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP":
            is_valid_magic = True
            detected_mime = "image/webp"

    if not is_valid_magic:
        raise SecurityValidationError(
            "Uploaded file does not match any recognized image magic bytes "
            "(supported: PNG, JPEG, WEBP, BMP, GIF, TIFF)."
        )

    # 2. Decompression bomb & dimension check
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            w, h = img.size
            if w > max_dimension or h > max_dimension:
                raise SecurityValidationError(
                    f"Image dimensions ({w}x{h}) exceed maximum allowed "
                    f"limit of {max_dimension}x{max_dimension} pixels."
                )
    except SecurityValidationError:
        raise
    except Image.DecompressionBombError as exc:
        raise SecurityValidationError(
            f"Image exceeds decompression safety limits (possible decompression bomb): {exc}"
        ) from exc
    except Exception as exc:
        raise SecurityValidationError(
            f"Invalid or corrupted image content: {exc}"
        ) from exc

    return detected_mime


def validate_document_security(doc_bytes: bytes, filename: str) -> str:
    """Verify document magic bytes or text encoding.

    Returns the detected format: 'pdf', 'markdown', or 'text'.
    """
    if not doc_bytes:
        raise SecurityValidationError("Standard document is empty (0 bytes).")

    lower = filename.lower()
    is_pdf_ext = lower.endswith(".pdf")

    if doc_bytes.startswith(_PDF_MAGIC):
        if not is_pdf_ext and filename:
            raise SecurityValidationError(
                "PDF magic signature detected, but file lacks .pdf extension."
            )
        return "pdf"

    if is_pdf_ext:
        raise SecurityValidationError(
            "Document has .pdf extension but lacks valid %PDF- header signature."
        )

    # Disallow null bytes in text standards
    if b"\x00" in doc_bytes:
        raise SecurityValidationError(
            "Standard document contains binary/null bytes but lacks valid PDF signature."
        )

    try:
        doc_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SecurityValidationError(
            f"Standard document must be valid UTF-8 text: {exc}"
        ) from exc

    return "markdown" if lower.endswith((".md", ".markdown")) else "text"


def sanitize_csv_security(csv_data: bytes | str) -> str:
    """Sanitize CSV content to neutralize CSV formula injection attacks.

    Disallows executable formula prefixes (=, +, -, @, tab, carriage return)
    in cell values by prepending a single quote.
    """
    if isinstance(csv_data, bytes):
        try:
            text = csv_data.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise SecurityValidationError(
                f"Sensor CSV must be valid UTF-8: {exc}"
            ) from exc
    else:
        text = csv_data

    if not text.strip():
        return ""

    if "\x00" in text:
        raise SecurityValidationError("Sensor CSV contains invalid NULL bytes.")

    reader = csv.reader(io.StringIO(text))
    output = io.StringIO()
    writer = csv.writer(output)

    dangerous_prefixes = ("=", "+", "-", "@", "\t", "\r")

    try:
        for row in reader:
            sanitized_row = []
            for cell in row:
                val = cell.strip()
                # If cell starts with dangerous prefix, escape it unless numeric
                if val.startswith(dangerous_prefixes) and not _is_numeric(val):
                    sanitized_row.append(f"'{val}")
                else:
                    sanitized_row.append(cell)
            writer.writerow(sanitized_row)
    except csv.Error as exc:
        raise SecurityValidationError(f"Malformed CSV content: {exc}") from exc

    return output.getvalue()


def _is_numeric(val: str) -> bool:
    """Check if string is a standard float/integer (e.g. -12.4 is a valid number)."""
    try:
        float(val)
        return True
    except ValueError:
        return False


def compute_audit_hash(
    *,
    image_bytes: bytes,
    standard_bytes: Optional[bytes] = None,
    sensor_data: Optional[bytes | str] = None,
    decision_summary: Optional[dict] = None,
) -> str:
    """Calculate a collision-resistant hierarchical SHA-256 audit digest.

    Hashes each component individually into 32-byte digests before computing
    the root audit seal, preventing delimiter collision attacks.
    """
    h_img = hashlib.sha256(image_bytes).digest()

    std_raw = standard_bytes or b""
    h_std = hashlib.sha256(std_raw).digest()

    if sensor_data is None:
        sns_raw = b""
    elif isinstance(sensor_data, str):
        sns_raw = sensor_data.encode("utf-8")
    else:
        sns_raw = sensor_data
    h_sns = hashlib.sha256(sns_raw).digest()

    if decision_summary:
        dec_raw = json.dumps(
            decision_summary, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    else:
        dec_raw = b"{}"
    h_dec = hashlib.sha256(dec_raw).digest()

    root_hasher = hashlib.sha256()
    root_hasher.update(b"ISO9001-AUDIT-ROOT-V1:")
    root_hasher.update(h_img)
    root_hasher.update(h_std)
    root_hasher.update(h_sns)
    root_hasher.update(h_dec)

    return root_hasher.hexdigest()
