from pathlib import Path
from typing import Any
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app.api.inspect import router as inspect_router
from backend.app.core.config import get_app_config
from starlette.requests import Request
from starlette.responses import Response

config = get_app_config()

app = FastAPI(
    title=config.app_title,
    description="MVP API for industrial defect inspection workflows.",
    version="0.1.0",
)

# Standard security headers middleware for production hardening
@app.middleware("http")
async def add_security_headers(request: Request, call_next) -> Response:
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


# Configurable CORS support (defaults to * for local development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

outputs_dir = Path(config.outputs_dir)
outputs_dir.mkdir(parents=True, exist_ok=True)
app.mount("/outputs", StaticFiles(directory=str(outputs_dir)), name="outputs")

app.include_router(inspect_router)


@app.get("/health")
def health() -> dict[str, Any]:
    from backend.app.vision.config import VisionConfig
    v_cfg = VisionConfig.from_env()
    has_key = bool(v_cfg.vlm_api_key and v_cfg.vlm_api_key != "your_openrouter_api_key_here")
    return {
        "status": "ok",
        "name": "Multimodal Industrial Inspection Agent API",
        "detector": v_cfg.backend,
        "vlm_model": v_cfg.vlm_model,
        "vlm_configured": has_key,
    }


# Mount static frontend at root (after API routes so API endpoints take precedence)
frontend_dir = Path("frontend")
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")

