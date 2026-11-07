"""Unit tests for ISO 9001 Certificate generation and export."""

from datetime import datetime, timezone
from pathlib import Path

from backend.app.schemas.inspection import (
    CAPAPlan,
    InspectionReport,
    RecommendedAction,
    SensorReading,
    SeverityLevel,
    StandardEvidence,
)
from backend.app.services.certificate_generator import (
    render_iso_certificate_html,
    save_iso_certificate,
)


def _sample_report() -> InspectionReport:
    return InspectionReport(
        inspection_id="insp_test_cert_01",
        object_name="pressure_vessel_tank_4",
        inspection_time=datetime(2026, 11, 7, 12, 0, 0, tzinfo=timezone.utc),
        input_data_summary="image 'tank.png', standard 'ASME_SecVIII.md'",
        defect_type="crack",
        defect_description="Longitudinal crack along circumferential weld",
        defect_location="weld seam A-B",
        confidence=0.94,
        severity_level=SeverityLevel.HIGH,
        recommended_action=RecommendedAction.REPAIR,
        risk_explanation="Crack exceeds 5mm tolerance in load-bearing boundary.",
        standard_evidence=[
            StandardEvidence(
                clause_id="3.2",
                title="Serious Crack Criteria",
                text="Cracks longer than 5mm in pressure vessels require immediate repair.",
                score=8.5,
            )
        ],
        sensor_readings=[
            SensorReading(name="temperature", value=88.5, unit="°C"),
            SensorReading(name="vibration", value=3.8, unit="mm/s"),
        ],
        requires_human_review=True,
        human_review_reasons=["Severity is high."],
        audit_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        compliance_standard="ISO 9001:2015 Clause 8.7",
        capa_plan=CAPAPlan(
            immediate_containment="Quarantine pressure vessel immediately.",
            root_cause_analysis="Weld heat-affected zone cyclic stress fatigue.",
            corrective_action="Grind and re-weld under WPS-04 procedure.",
            preventive_action="Inspect preheat monitoring calibration records.",
        ),
    )


def test_render_iso_certificate_html_structure():
    rep = _sample_report()
    html_out = render_iso_certificate_html(rep)

    assert "Certificate of Quality Audit" in html_out
    assert "CERT-insp_test_cert_01" in html_out
    assert "pressure_vessel_tank_4" in html_out
    assert "CRACK" in html_out
    assert "94.0%" in html_out
    assert "NON-CONFORMING — QUARANTINE / REJECT" in html_out
    assert "CLAUSE 3.2" in html_out
    assert "Serious Crack Criteria" in html_out
    assert "temperature" in html_out
    assert "88.50 °C" in html_out
    assert "Quarantine pressure vessel immediately" in html_out
    assert "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855" in html_out
    assert "@media print" in html_out


def test_save_iso_certificate(tmp_path: Path):
    rep = _sample_report()
    out_file = save_iso_certificate(rep, output_dir=str(tmp_path))

    assert out_file.exists()
    assert out_file.name == "insp_test_cert_01_certificate.html"
    content = out_file.read_text(encoding="utf-8")
    assert "insp_test_cert_01" in content


def test_render_iso_certificate_low_severity_human_review_is_hold():
    rep = _sample_report()
    rep.severity_level = SeverityLevel.LOW
    rep.requires_human_review = True
    rep.human_review_reasons = ["Confidence is low (0.64)"]

    html_out = render_iso_certificate_html(rep)

    # Must be on HOLD, never APPROVED FOR RELEASE
    assert "NON-CONFORMING — CONDITIONAL HOLD / PENDING REVIEW" in html_out
    assert "APPROVED FOR RELEASE" not in html_out
    assert "Confidence is low (0.64)" in html_out
