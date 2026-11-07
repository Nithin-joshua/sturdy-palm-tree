import io
import json

from PIL import Image
from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)

STANDARD_PATH = "data/sample_standards/pipeline_surface_defect_standard.md"


def _valid_png() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (10, 10), color="blue").save(buf, format="PNG")
    return buf.getvalue()


def _standard_bytes() -> bytes:
    with open(STANDARD_PATH, "rb") as f:
        return f.read()


def test_inspect_basic_crack():
    files = {
        "image": ("pipe_crack_001.png", _valid_png(), "image/png"),
        "standard": (
            "standard.md",
            _standard_bytes(),
            "text/markdown",
        ),
    }
    resp = client.post("/api/inspect", files=files)
    assert resp.status_code == 200
    body = resp.json()
    assert body["defect_type"] == "crack"
    assert "severity_level" in body
    assert "recommended_action" in body
    assert body["standard_evidence"]


def test_inspect_with_hints_and_sensor():
    files = {
        "image": ("pipe.png", _valid_png(), "image/png"),
        "standard": ("standard.md", _standard_bytes(), "text/markdown"),
        "sensor_csv": ("sensors.csv", b"temperature,vibration\n90,3\n", "text/csv"),
    }
    data = {
        "object_name": "pipe_42",
        "vision_hints": json.dumps(
            {"defect_type": "crack", "confidence": 0.9, "length_mm": 9, "load_bearing_area": True}
        ),
    }
    resp = client.post("/api/inspect", files=files, data=data)
    assert resp.status_code == 200
    body = resp.json()
    assert body["object_name"] == "pipe_42"
    assert body["severity_level"] == "critical"
    assert body["recommended_action"] == "stop_machine"
    assert body["requires_human_review"] is True


def test_inspect_unsupported_standard_returns_415():
    files = {
        "image": ("pipe.png", _valid_png(), "image/png"),
        "standard": ("standard.docx", b"binary", "application/octet-stream"),
    }
    resp = client.post("/api/inspect", files=files)
    assert resp.status_code == 415


def test_inspect_invalid_hints_returns_422():
    files = {
        "image": ("pipe.png", _valid_png(), "image/png"),
        "standard": ("standard.md", _standard_bytes(), "text/markdown"),
    }
    resp = client.post("/api/inspect", files=files, data={"vision_hints": "{not json"})
    assert resp.status_code == 422


def test_inspect_generates_audit_hash_and_certificate():
    files = {
        "image": ("pipe_crack_001.png", _valid_png(), "image/png"),
        "standard": ("standard.md", _standard_bytes(), "text/markdown"),
    }
    resp = client.post("/api/inspect", files=files)
    assert resp.status_code == 200
    body = resp.json()

    assert "audit_hash" in body and body["audit_hash"] is not None
    assert len(body["audit_hash"]) == 64
    assert body["compliance_standard"] == "ISO 9001:2015 Clause 8.7"
    assert "capa_plan" in body and body["capa_plan"] is not None
    assert "immediate_containment" in body["capa_plan"]

    # Verify certificate endpoint
    insp_id = body["inspection_id"]
    cert_resp = client.get(f"/api/inspect/{insp_id}/certificate")
    assert cert_resp.status_code == 200
    assert "text/html" in cert_resp.headers["content-type"]
    assert f"CERT-{insp_id}" in cert_resp.text
    assert "Certificate of Quality Audit" in cert_resp.text
    assert body["audit_hash"] in cert_resp.text


def test_certificate_invalid_id_rejected():
    resp = client.get("/api/inspect/../../malicious/certificate")
    assert resp.status_code in {400, 404}


def test_inspect_rejects_empty_image():
    files = {
        "image": ("pipe.png", b"", "image/png"),
        "standard": ("standard.md", _standard_bytes(), "text/markdown"),
    }
    resp = client.post("/api/inspect", files=files)
    assert resp.status_code == 422
    assert "empty" in resp.json()["detail"].lower()
