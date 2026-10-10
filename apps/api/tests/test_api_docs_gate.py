"""/docs, /redoc and /openapi.json are hidden outside local/dev/test (readiness audit #11)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from porterchain_api.main import api_docs_exposed


@pytest.mark.parametrize(
    ("app_env", "flag", "expected"),
    [
        ("local", False, True),
        ("development", False, True),
        ("test", False, True),
        ("production", False, False),
        ("staging", False, False),
        ("production", True, True),
    ],
)
def test_api_docs_gate(app_env: str, flag: bool, expected: bool) -> None:
    assert api_docs_exposed(SimpleNamespace(app_env=app_env, api_docs_enabled=flag)) is expected


def test_production_app_has_no_docs_routes(monkeypatch) -> None:
    from porterchain_api import main

    real = main.get_settings()
    fake = real.model_copy(update={"app_env": "production", "api_docs_enabled": False})
    monkeypatch.setattr(main, "get_settings", lambda: fake)
    app = main.create_app()
    paths = {getattr(r, "path", None) for r in app.routes}
    assert "/docs" not in paths and "/openapi.json" not in paths and "/redoc" not in paths
    # Schema generation still works in-process (contract tests rely on it).
    assert app.openapi()["info"]["title"] == "Porterchain API"
