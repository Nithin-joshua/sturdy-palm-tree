from pathlib import Path


def test_dockerfile_exists_and_configured():
    dockerfile = Path("Dockerfile")
    assert dockerfile.exists()
    content = dockerfile.read_text(encoding="utf-8")

    assert "FROM python:3.12-slim" in content
    assert "EXPOSE 8000" in content
    assert "appuser" in content
    assert "HEALTHCHECK" in content
    assert "uvicorn backend.app.main:app" in content


def test_dockerignore_excludes_development_artifacts():
    dockerignore = Path(".dockerignore")
    assert dockerignore.exists()
    content = dockerignore.read_text(encoding="utf-8")

    assert ".git" in content
    assert ".venv" in content
    assert "__pycache__" in content
    assert "tests" in content


def test_docker_compose_config():
    compose_file = Path("docker-compose.yml")
    assert compose_file.exists()
    content = compose_file.read_text(encoding="utf-8")

    assert "inspection-agent:" in content
    assert "${PORT:-8000}:8000" in content
    assert "/app/outputs" in content
