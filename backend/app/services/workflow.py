"""End-to-end inspection workflow orchestration.

Ties together the vision adapter, document loader, retriever, decision engine,
and report generator. This is the single entry point used by the API layer and
is easy to unit test without HTTP.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

from backend.app.agents.inspection_agent import decide
from backend.app.core.security import compute_audit_hash
from backend.app.rag.document_loader import load_document_bytes
from backend.app.rag.retriever import StandardRetriever
from backend.app.schemas.inspection import InspectionReport
from backend.app.services.certificate_generator import save_iso_certificate
from backend.app.services.report_generator import build_report
from backend.app.services.sensor_loader import parse_sensor_csv
from backend.app.vision.defect_detector import DefectDetector, get_default_detector


def _build_query(observation) -> str:
    """Construct a retrieval query from the observation."""
    parts = [observation.defect_type, observation.description]
    if observation.length_mm:
        parts.append(f"length {observation.length_mm} mm")
    if observation.load_bearing_area:
        parts.append("load bearing pressure boundary weld")
    if observation.location:
        parts.append(observation.location)
    return " ".join(p for p in parts if p)


def run_inspection(
    *,
    image_name: str,
    image_bytes: Optional[bytes] = None,
    standard_text: Optional[str] = None,
    standard_bytes: Optional[bytes] = None,
    standard_name: Optional[str] = None,
    sensor_csv: Optional[bytes | str] = None,
    object_name: Optional[str] = None,
    vision_hints: Optional[dict] = None,
    detector: Optional[DefectDetector] = None,
    top_k: int = 3,
    annotate: bool = False,
    output_dir: str = "outputs",
) -> InspectionReport:
    """Run the full inspection pipeline and return a structured report."""
    detector = detector or get_default_detector()

    # 1. Vision analysis.
    observation = detector.detect(
        filename=image_name, image_bytes=image_bytes, hints=vision_hints
    )

    # 2. Standard RAG.
    if standard_text is None and standard_bytes is not None:
        standard_text = load_document_bytes(
            standard_bytes, standard_name or "standard.md"
        )
    elif standard_bytes is None and standard_text is not None:
        standard_bytes = standard_text.encode("utf-8")

    standard_evidence = []
    if standard_text:
        retriever = StandardRetriever.from_text(standard_text)
        standard_evidence = retriever.retrieve(_build_query(observation), top_k=top_k)

    # 3. Sensor check.
    sensor_readings = parse_sensor_csv(sensor_csv) if sensor_csv else []

    # 4. Decision engine.
    decision = decide(observation, standard_evidence, sensor_readings)

    # 5. Cryptographic audit hash (ISO 9001:2015 Clause 8.7 chain of custody).
    resolved_object = object_name or Path(image_name).stem
    audit_hash = None
    if image_bytes:
        decision_summary = {
            "object_name": resolved_object,
            "severity": decision.severity_level.value,
            "action": decision.recommended_action.value,
            "requires_human_review": decision.requires_human_review,
            "defect_type": observation.defect_type,
            "confidence": round(observation.confidence, 4),
            "location": observation.location or "",
            "clause_ids": [ev.clause_id for ev in standard_evidence if ev.clause_id],
        }
        audit_hash = compute_audit_hash(
            image_bytes=image_bytes,
            standard_bytes=standard_bytes,
            sensor_data=sensor_csv,
            decision_summary=decision_summary,
        )

    # 6. Report generation.
    detector_name = detector.__class__.__name__
    detector_cfg = getattr(detector, "config", None)
    detector_model = getattr(detector_cfg, "vlm_model", None) if detector_cfg else None

    report = build_report(
        object_name=resolved_object,
        image_name=image_name,
        observation=observation,
        decision=decision,
        standard_evidence=standard_evidence,
        sensor_readings=sensor_readings,
        standard_name=standard_name,
        detector=detector_name,
        detector_model=detector_model,
        audit_hash=audit_hash,
    )

    # 7. Generate official ISO 9001 compliance certificate artifact.
    try:
        save_iso_certificate(report, output_dir=output_dir)
    except Exception as exc:
        logger.warning(
            "Failed to save ISO 9001 certificate for '%s': %s",
            report.inspection_id,
            exc,
            exc_info=True,
        )

    # 8. Optional annotated defect image (Phase 2).
    if annotate and image_bytes and observation.bounding_box is not None:
        from backend.app.vision.annotator import annotate_defect

        report.annotated_image_path = annotate_defect(
            image_bytes=image_bytes,
            observation=observation,
            output_dir=output_dir,
            inspection_id=report.inspection_id,
        )

    return report
