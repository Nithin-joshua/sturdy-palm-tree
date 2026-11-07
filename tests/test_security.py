"""Unit tests for cryptographic audit hashing and security input validation."""

import pytest
from PIL import Image
import io

from backend.app.core.security import (
    SecurityValidationError,
    compute_audit_hash,
    sanitize_csv_security,
    validate_document_security,
    validate_image_security,
)


def _create_test_image(width: int = 100, height: int = 100) -> bytes:
    img = Image.new("RGB", (width, height), color="red")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_validate_image_security_valid_png():
    png_bytes = _create_test_image(50, 50)
    mime = validate_image_security(png_bytes, filename="part.png")
    assert mime == "image/png"


def test_validate_image_security_empty():
    with pytest.raises(SecurityValidationError, match="empty"):
        validate_image_security(b"")


def test_validate_image_security_invalid_magic():
    with pytest.raises(SecurityValidationError, match="magic bytes"):
        validate_image_security(b"MALICIOUS_NON_IMAGE_BINARY_PAYLOAD", filename="exploit.exe")


def test_validate_image_security_exceeds_dimension():
    oversized_bytes = _create_test_image(5000, 100)
    with pytest.raises(SecurityValidationError, match="exceed maximum allowed limit"):
        validate_image_security(oversized_bytes, max_dimension=4096)


def test_validate_document_security_valid_markdown():
    doc = b"# Standard 101\nDefects must not exceed 2mm."
    fmt = validate_document_security(doc, "standard.md")
    assert fmt == "markdown"


def test_validate_document_security_pdf():
    doc = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj"
    fmt = validate_document_security(doc, "standard.pdf")
    assert fmt == "pdf"


def test_validate_document_security_pdf_mismatch():
    doc = b"not a pdf"
    with pytest.raises(SecurityValidationError, match="header signature"):
        validate_document_security(doc, "fake.pdf")


def test_validate_document_security_binary_garbage():
    doc = b"Some text with null byte \x00 in header"
    with pytest.raises(SecurityValidationError, match="null bytes"):
        validate_document_security(doc, "bogus.md")


def test_sanitize_csv_security_null_byte_rejected():
    with pytest.raises(SecurityValidationError, match="NULL bytes"):
        sanitize_csv_security("col1,col2\nval1,\x00val2")


def test_sanitize_csv_security_formula_injection():
    csv_input = "col1,col2,col3\n=1+1,-15.4,@SUM(A1:A2)\n"
    sanitized = sanitize_csv_security(csv_input)
    # Dangerous formulas must be escaped with single quote, negative number preserved
    assert "'=1+1" in sanitized
    assert "-15.4" in sanitized
    assert "'@SUM(A1:A2)" in sanitized


def test_compute_audit_hash_deterministic():
    img = b"fake_png_data"
    std = b"fake_standard_data"
    sns = "temp,vib\n80,4.2"
    dec = {"severity": "critical", "action": "stop_machine"}

    hash1 = compute_audit_hash(image_bytes=img, standard_bytes=std, sensor_data=sns, decision_summary=dec)
    hash2 = compute_audit_hash(image_bytes=img, standard_bytes=std, sensor_data=sns, decision_summary=dec)

    assert hash1 == hash2
    assert len(hash1) == 64  # SHA-256 hex string


def test_compute_audit_hash_tamper_evident():
    img = b"fake_png_data"
    std = b"fake_standard_data"
    sns = "temp,vib\n80,4.2"
    dec = {"severity": "critical", "action": "stop_machine"}

    original_hash = compute_audit_hash(image_bytes=img, standard_bytes=std, sensor_data=sns, decision_summary=dec)

    # Tampering with image bytes alters hash
    tampered_img_hash = compute_audit_hash(image_bytes=b"tampered_png_data", standard_bytes=std, sensor_data=sns, decision_summary=dec)
    assert original_hash != tampered_img_hash

    # Tampering with decision alters hash
    tampered_dec_hash = compute_audit_hash(image_bytes=img, standard_bytes=std, sensor_data=sns, decision_summary={"severity": "low"})
    assert original_hash != tampered_dec_hash
