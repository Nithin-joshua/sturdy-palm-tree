"""`/api/inspect` endpoint: run the full multimodal inspection workflow."""

from __future__ import annotations

from functools import partial
import json
from pathlib import Path
import re
from typing import Optional

import anyio
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse

from backend.app.core.config import get_app_config
from backend.app.core.security import (
    SecurityValidationError,
    sanitize_csv_security,
    validate_document_security,
    validate_image_security,
)
from backend.app.rag.document_loader import UnsupportedDocumentError
from backend.app.schemas.inspection import InspectionReport
from backend.app.services.workflow import run_inspection

router = APIRouter(prefix="/api", tags=["inspection"])
INSPECTION_ID_REGEX = re.compile(r"^[a-zA-Z0-9_\-]+$")


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
    try:
        validate_image_security(image_bytes, filename=image.filename)
    except SecurityValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    standard_bytes = await standard.read()
    validate_payload_size(
        standard_bytes, "Standard document", max_bytes, config.max_upload_size_mb
    )
    try:
        validate_document_security(standard_bytes, filename=standard.filename or "standard.md")
    except SecurityValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    sensor_data = None
    if sensor_csv is not None:
        sensor_data = await sensor_csv.read()
        validate_payload_size(
            sensor_data, "Sensor CSV", max_bytes, config.max_upload_size_mb
        )
        try:
            sensor_data = sanitize_csv_security(sensor_data)
        except SecurityValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

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
        inspection_func = partial(
            run_inspection,
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
        report = await anyio.to_thread.run_sync(inspection_func)
    except UnsupportedDocumentError as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc

    return report


@router.get("/inspect/{inspection_id}/certificate", response_class=HTMLResponse)
async def get_certificate(inspection_id: str) -> HTMLResponse:
    """Retrieve the printable ISO 9001 Clause 8.7 Quality Certificate."""
    if not INSPECTION_ID_REGEX.match(inspection_id):
        raise HTTPException(status_code=400, detail="Invalid inspection ID format.")

    config = get_app_config()
    out_dir = Path(config.outputs_dir).resolve()
    cert_path = (out_dir / f"{inspection_id}_certificate.html").resolve()

    if not cert_path.is_relative_to(out_dir) or not cert_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Certificate for inspection '{inspection_id}' not found.",
        )
    return HTMLResponse(content=cert_path.read_text(encoding="utf-8"))
