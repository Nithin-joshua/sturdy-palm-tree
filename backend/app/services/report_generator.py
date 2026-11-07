"""Assemble the final structured InspectionReport from workflow outputs."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from backend.app.schemas.inspection import (
    CAPAPlan,
    DefectObservation,
    InspectionReport,
    RecommendedAction,
    SensorReading,
    SeverityLevel,
    StandardEvidence,
)

if TYPE_CHECKING:
    from backend.app.agents.inspection_agent import InspectionDecision


def generate_default_capa(
    *,
    severity: SeverityLevel,
    recommended_action: RecommendedAction,
    defect_type: str,
    object_name: str,
    requires_human_review: bool = False,
    human_review_reasons: Optional[list[str]] = None,
) -> CAPAPlan:
    """Generate a structured ISO 9001:2015 Clause 8.7 CAPA remediation plan."""
    if requires_human_review and severity.rank < SeverityLevel.HIGH.rank:
        reason_str = "; ".join(human_review_reasons or ["Flagged for supervisor audit"])
        return CAPAPlan(
            immediate_containment=(
                f"Hold component '{object_name}' in quarantine pending secondary supervisor review "
                f"({reason_str}). Do not release to downstream production."
            ),
            root_cause_analysis=(
                "Inconclusive visual evidence, missing regulatory standard clause, "
                "or conflicting sensor telemetry requiring human engineering audit."
            ),
            corrective_action=(
                "Perform physical reinspection by a certified QA inspector and record findings in audit log."
            ),
            preventive_action=(
                "Review inspection standard library coverage and calibrate model confidence thresholds."
            ),
        )

    if severity == SeverityLevel.LOW:
        return CAPAPlan(
            immediate_containment="Component cleared for release; normal production processing continues.",
            root_cause_analysis="Surface variation or superficial defect is within standard allowable tolerance limits.",
            corrective_action="No corrective rework required. Maintain standard operational cadence.",
            preventive_action="Continue routine shift-based visual quality checks according to the audit plan.",
        )

    dtype = defect_type.lower()
    return CAPAPlan(
        immediate_containment=(
            f"Immediately quarantine component '{object_name}' (severity: {severity.value.upper()}). "
            f"Apply physical/digital lock-out tag and notify line supervisor."
        ),
        root_cause_analysis=(
            f"Detected surface flaw ({dtype}) exceeding standard tolerance thresholds, "
            f"potentially caused by tool wear, thermal cycling, or material fatigue."
        ),
        corrective_action=(
            f"Execute prescribed disposition: {recommended_action.value.replace('_', ' ').upper()}. "
            f"Conduct non-destructive testing (NDT) to verify compliance prior to release."
        ),
        preventive_action=(
            "Initiate a 5-Why root cause investigation, review machine calibration logs, "
            "and verify supplier raw material conformance certificates."
        ),
    )


def _summarize_inputs(
    *,
    image_name: str,
    standard_name: Optional[str],
    sensor_readings: list[SensorReading],
) -> str:
    parts = [f"image '{image_name}'"]
    if standard_name:
        parts.append(f"standard '{standard_name}'")
    if sensor_readings:
        parts.append(f"{len(sensor_readings)} sensor reading(s)")
    return ", ".join(parts)


def build_report(
    *,
    object_name: str,
    image_name: str,
    observation: DefectObservation,
    decision: "InspectionDecision",
    standard_evidence: list[StandardEvidence],
    sensor_readings: Optional[list[SensorReading]] = None,
    standard_name: Optional[str] = None,
    annotated_image_path: Optional[str] = None,
    detector: Optional[str] = None,
    detector_model: Optional[str] = None,
    audit_hash: Optional[str] = None,
    compliance_standard: str = "ISO 9001:2015 Clause 8.7",
    capa_plan: Optional[CAPAPlan] = None,
) -> InspectionReport:
    """Combine all pieces into the final report object."""
    sensor_readings = sensor_readings or []
    if capa_plan is None:
        capa_plan = generate_default_capa(
            severity=decision.severity_level,
            recommended_action=decision.recommended_action,
            defect_type=observation.defect_type,
            object_name=object_name,
            requires_human_review=decision.requires_human_review,
            human_review_reasons=decision.human_review_reasons,
        )

    return InspectionReport(
        object_name=object_name,
        input_data_summary=_summarize_inputs(
            image_name=image_name,
            standard_name=standard_name,
            sensor_readings=sensor_readings,
        ),
        defect_type=observation.defect_type,
        defect_description=observation.description,
        defect_location=observation.location,
        defect_bbox=observation.bounding_box,
        confidence=observation.confidence,
        detector=detector,
        detector_model=detector_model,
        severity_level=decision.severity_level,
        recommended_action=decision.recommended_action,
        risk_explanation=decision.risk_explanation,
        standard_evidence=standard_evidence,
        sensor_readings=sensor_readings,
        requires_human_review=decision.requires_human_review,
        human_review_reasons=decision.human_review_reasons,
        annotated_image_path=annotated_image_path,
        audit_hash=audit_hash,
        compliance_standard=compliance_standard,
        capa_plan=capa_plan,
    )
