"""`/api/inspect` endpoint: run the full multimodal inspection workflow."""

from __future__ import annotations

import json
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from backend.app.core.config import get_app_config
from backend.app.rag.document_loader import UnsupportedDocumentError
from backend.app.schemas.inspection import InspectionReport
from backend.app.services.workflow import run_inspection

router = APIRouter(prefix="/api", tags=["inspection"])


def validate_payload_size(data: bytes, label: str, max_bytes: int, max_mb: int) -> None:
    """Ensure uploaded payload byte length does not exceed configured threshold."""
    if len(data) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"{label} exceeds maximum upload limit of {max_mb} MB.",
        )


@router.post("/inspect", response_model=InspectionReport)
async def inspect(
    image: UploadFile = File(..., description="Industrial defect image."),
    standard: UploadFile = File(..., description="Inspection standard (txt/md/pdf)."),
    sensor_csv: Optional[UploadFile] = File(
        default=None, description="Optional sensor CSV."
    ),
    object_name: Optional[str] = Form(default=None),
    vision_hints: Optional[str] = Form(
        default=None, description="Optional JSON object of detector hints."
    ),
    annotate: bool = Form(
        default=False, description="Save an annotated image with the defect box."
    ),
) -> InspectionReport:
    config = get_app_config()
    max_bytes = config.max_upload_size_bytes

    image_bytes = await image.read()
    validate_payload_size(image_bytes, "Image file", max_bytes, config.max_upload_size_mb)

    standard_bytes = await standard.read()
    validate_payload_size(
        standard_bytes, "Standard document", max_bytes, config.max_upload_size_mb
    )

    sensor_data = None
    if sensor_csv is not None:
        sensor_data = await sensor_csv.read()
        validate_payload_size(
            sensor_data, "Sensor CSV", max_bytes, config.max_upload_size_mb
        )

    hints = None
    if vision_hints:
        try:
            hints = json.loads(vision_hints)
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=422, detail=f"vision_hints must be valid JSON: {exc}"
            ) from exc
        if not isinstance(hints, dict):
            raise HTTPException(
                status_code=422, detail="vision_hints must be a JSON object."
            )

    try:
        report = run_inspection(
            image_name=image.filename or "image.png",
            image_bytes=image_bytes,
            standard_bytes=standard_bytes,
            standard_name=standard.filename,
            sensor_csv=sensor_data,
            object_name=object_name,
            vision_hints=hints,
            annotate=annotate,
            output_dir=config.outputs_dir,
        )
    except UnsupportedDocumentError as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc

    return report
