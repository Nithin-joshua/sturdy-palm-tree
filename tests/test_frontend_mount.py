from pathlib import Path

from backend.app.main import app


def test_frontend_directory_mounted_at_root():
    # Verify that the frontend static mount exists
    assert any(getattr(r, "name", None) == "frontend" for r in app.routes)

    # Verify that frontend directory and core files exist
    frontend_dir = Path("frontend")
    assert frontend_dir.exists()
    assert (frontend_dir / "index.html").exists()
    assert (frontend_dir / "config.js").exists()
    assert (frontend_dir / "app.js").exists()


def test_api_routes_precede_frontend_mount():
    # API and health routes must appear before the catch-all frontend mount
    route_names = [getattr(r, "name", None) for r in app.routes]
    assert "health" in route_names
    assert "frontend" in route_names

    health_idx = route_names.index("health")
    frontend_idx = route_names.index("frontend")
    # Frontend must be at the end so it doesn't shadow health or API routes
    assert health_idx < frontend_idx
    assert frontend_idx == len(app.routes) - 1


def test_frontend_config_uses_relative_api_base():
    config_path = Path("frontend/config.js")
    content = config_path.read_text(encoding="utf-8")
    assert 'apiBase: ""' in content
