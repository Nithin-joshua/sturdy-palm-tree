from pathlib import Path

from backend.app.main import app


def test_security_headers_middleware_configured():
    # Verify add_security_headers middleware is registered on the FastAPI app
    user_middleware = [m.cls.__name__ for m in app.user_middleware]
    middleware_funcs = [
        getattr(m, "kwargs", {}).get("dispatch", None)
        for m in app.user_middleware
    ]
    func_names = [f.__name__ for f in middleware_funcs if f is not None]
    assert "add_security_headers" in func_names


def test_cloud_manifests_exist():
    render_file = Path("render.yaml")
    assert render_file.exists()
    content_render = render_file.read_text(encoding="utf-8")
    assert "industrial-inspection-agent" in content_render
    assert "healthCheckPath: /health" in content_render

    railway_file = Path("railway.toml")
    assert railway_file.exists()
    content_railway = railway_file.read_text(encoding="utf-8")
    assert "healthcheckPath = \"/health\"" in content_railway

    fly_file = Path("fly.toml")
    assert fly_file.exists()
    content_fly = fly_file.read_text(encoding="utf-8")
    assert "internal_port = 8000" in content_fly


def test_github_actions_ci_workflow():
    ci_file = Path(".github/workflows/ci.yml")
    assert ci_file.exists()
    content_ci = ci_file.read_text(encoding="utf-8")
    assert "name: CI" in content_ci
    assert "pytest -v" in content_ci
    assert "docker/build-push-action" in content_ci


def test_hosting_documentation_exists():
    hosting_doc = Path("docs/hosting.md")
    assert hosting_doc.exists()
    content = hosting_doc.read_text(encoding="utf-8")
    assert "Render" in content
    assert "Railway" in content
    assert "Fly.io" in content
