"""VLM defect detector backed by an OpenAI-compatible API (Phase 2).

Sends the image plus a structured-output prompt to an OpenAI-compatible Chat
Completions endpoint and parses the JSON response into a ``DefectObservation``.
Works with any compatible server via ``INSPECTION_VLM_BASE_URL`` -- including
local Qwen-VL deployments served by Ollama or vLLM. For fully in-process local
Qwen inference (no server), use ``QwenVLDefectDetector`` instead.

The ``openai`` SDK is imported lazily and the client can be injected for tests.
"""

from __future__ import annotations

import base64
import logging
from pathlib import Path
from typing import Any, Optional

from backend.app.schemas.inspection import DefectObservation
from backend.app.vision.config import VisionConfig
from backend.app.vision.defect_detector import DefectDetector
from backend.app.vision.vlm_common import (
    SYSTEM_PROMPT,
    USER_PROMPT,
    observation_from_payload,
)

logger = logging.getLogger(__name__)

_MIME_BY_SUFFIX = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
}


def _mime_for(filename: str) -> str:
    return _MIME_BY_SUFFIX.get(Path(filename).suffix.lower(), "image/png")


class VLMDefectDetector(DefectDetector):
    """Defect detector backed by an OpenAI-compatible vision model."""

    def __init__(
        self,
        config: Optional[VisionConfig] = None,
        client: Any = None,
    ) -> None:
        self.config = config or VisionConfig()
        self._client = client

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                from openai import OpenAI  # type: ignore
            except ImportError as exc:  # pragma: no cover - without dep only
                raise RuntimeError(
                    "openai is required for the VLM detector. Install it with: "
                    "pip install -r backend/requirements-vision.txt"
                ) from exc
            if not self.config.vlm_api_key:
                raise RuntimeError(
                    "No VLM API key configured. Set INSPECTION_VLM_API_KEY "
                    "(or OPENAI_API_KEY)."
                )
            kwargs: dict[str, Any] = {"api_key": self.config.vlm_api_key}
            if self.config.vlm_base_url:
                kwargs["base_url"] = self.config.vlm_base_url
            self._client = OpenAI(**kwargs)
        return self._client

    def detect(
        self,
        *,
        filename: str,
        image_bytes: Optional[bytes] = None,
        hints: Optional[dict] = None,
    ) -> DefectObservation:
        hints = hints or {}
        if not image_bytes:
            return DefectObservation(
                defect_type="unknown",
                description="No image data provided to the VLM detector.",
                confidence=0.0,
                location=hints.get("location"),
            )

        client = self._get_client()
        data_uri = (
            f"data:{_mime_for(filename)};base64,"
            + base64.b64encode(image_bytes).decode("ascii")
        )
        logger.info(
            "Calling VLM API: model=%s base_url=%s for image '%s' (%d bytes)...",
            self.config.vlm_model,
            self.config.vlm_base_url or "api.openai.com",
            filename,
            len(image_bytes),
        )
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": USER_PROMPT},
                    {"type": "image_url", "image_url": {"url": data_uri}},
                ],
            },
        ]
        try:
            response = client.chat.completions.create(
                model=self.config.vlm_model,
                messages=messages,
                temperature=0,
            )
            content = response.choices[0].message.content or ""
            logger.info("VLM API response received (%d chars): %s", len(content), content[:160])
            return observation_from_payload(content, hints)
        except Exception as exc:
            # Automatic fallback if the requested model is 404/unserved on OpenRouter
            err_str = str(exc).lower()
            if (
                ("404" in err_str or "not found" in err_str or "no provider" in err_str)
                and self.config.vlm_model != "nvidia/nemotron-3.5-super-vl:free"
            ):
                logger.warning(
                    "Model '%s' is unavailable (404/unserved); automatically retrying with nvidia/nemotron-3.5-super-vl:free...",
                    self.config.vlm_model,
                )
                try:
                    retry_response = client.chat.completions.create(
                        model="nvidia/nemotron-3.5-super-vl:free",
                        messages=messages,
                        temperature=0,
                    )
                    retry_content = retry_response.choices[0].message.content or ""
                    logger.info("Fallback Nemotron VLM response received (%d chars): %s", len(retry_content), retry_content[:160])
                    obs = observation_from_payload(retry_content, hints)
                    obs.description = f"[Via Nemotron fallback]: {obs.description}"
                    return obs
                except Exception as retry_exc:
                    logger.error("Nemotron fallback also failed: %s", retry_exc)
                    exc = retry_exc

            logger.error("VLM inference failed via model %s: %s", self.config.vlm_model, exc)
            return DefectObservation(
                defect_type="unknown",
                description=f"VLM call failed ({exc.__class__.__name__}: {exc}).",
                confidence=0.0,
                location=hints.get("location"),
            )
