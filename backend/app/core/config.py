"""Centralized application configuration.

Reads settings from environment variables or a local `.env` file with lightweight
CPU-friendly defaults for any laptop.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def load_dotenv(path: str | Path = ".env") -> None:
    """Lightweight .env loader using standard library only."""
    env_file = Path(path)
    if not env_file.is_file():
        return
    try:
        lines = env_file.read_text(encoding="utf-8").splitlines()
    except Exception:
        return

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip().strip("\"'")
        if key and key not in os.environ:
            os.environ[key] = val


# Load .env if present on import
load_dotenv()


def _env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value is None:
        return default
    value = value.strip()
    return value or default


def _env_int(name: str, default: int) -> int:
    raw = _env(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass
class AppConfig:
    """Server and runtime application settings."""

    app_title: str = "Multimodal Industrial Inspection Agent"
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list[str] = field(default_factory=lambda: ["*"])
    max_upload_size_mb: int = 25
    outputs_dir: str = "outputs"

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @classmethod
    def from_env(cls) -> "AppConfig":
        raw_cors = _env("CORS_ORIGINS", "*") or "*"
        if raw_cors == "*":
            origins = ["*"]
        else:
            origins = [o.strip() for o in raw_cors.split(",") if o.strip()]

        return cls(
            app_title=_env("APP_TITLE", "Multimodal Industrial Inspection Agent")
            or "Multimodal Industrial Inspection Agent",
            host=_env("HOST", "0.0.0.0") or "0.0.0.0",
            port=_env_int("PORT", 8000),
            cors_origins=origins,
            max_upload_size_mb=_env_int("MAX_UPLOAD_SIZE_MB", 25),
            outputs_dir=_env("OUTPUTS_DIR", "outputs") or "outputs",
        )


_config_instance: AppConfig | None = None


def get_app_config() -> AppConfig:
    """Return singleton or freshly loaded AppConfig."""
    global _config_instance
    if _config_instance is None:
        _config_instance = AppConfig.from_env()
    return _config_instance
