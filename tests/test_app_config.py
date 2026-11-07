from pathlib import Path

import pytest
from fastapi import HTTPException

from backend.app.api.inspect import validate_payload_size
from backend.app.core.config import AppConfig, get_app_config, load_dotenv


def test_default_app_config():
    cfg = AppConfig()
    assert cfg.host == "0.0.0.0"
    assert cfg.port == 8000
    assert cfg.cors_origins == ["*"]
    assert cfg.max_upload_size_mb == 25
    assert cfg.max_upload_size_bytes == 25 * 1024 * 1024
    assert cfg.outputs_dir == "outputs"


def test_from_env_parses_cors_origins(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000, https://cloud.inspection.ai")
    monkeypatch.setenv("PORT", "9090")
    monkeypatch.setenv("MAX_UPLOAD_SIZE_MB", "10")
    monkeypatch.setenv("OUTPUTS_DIR", "custom_outputs")

    cfg = AppConfig.from_env()
    assert cfg.port == 9090
    assert cfg.cors_origins == ["http://localhost:3000", "https://cloud.inspection.ai"]
    assert cfg.max_upload_size_mb == 10
    assert cfg.max_upload_size_bytes == 10 * 1024 * 1024
    assert cfg.outputs_dir == "custom_outputs"


def test_load_dotenv_parses_file(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("CUSTOM_TEST_VAR=hello_agent\n# Comment\nINVALID_LINE\n", encoding="utf-8")

    monkeypatch.delenv("CUSTOM_TEST_VAR", raising=False)
    load_dotenv(env_file)
    import os
    assert os.getenv("CUSTOM_TEST_VAR") == "hello_agent"


def test_validate_payload_size_accepts_valid_length():
    # Should not raise
    validate_payload_size(b"valid payload", "Test file", max_bytes=1024, max_mb=1)


def test_validate_payload_size_rejects_oversized_payload():
    with pytest.raises(HTTPException) as exc_info:
        validate_payload_size(b"X" * 200, "Image file", max_bytes=100, max_mb=1)

    assert exc_info.value.status_code == 413
    assert "Image file exceeds maximum upload limit" in exc_info.value.detail
