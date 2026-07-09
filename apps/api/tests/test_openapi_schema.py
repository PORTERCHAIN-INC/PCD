"""OpenAPI schema generation guard.

Regression test for the class of bug where a route annotation references an
undefined/forward-ref request model (e.g. an unregistered `*Body` schema).
Such a route imports fine but makes `app.openapi()` — and therefore
`/openapi.json` + `/docs` — raise at runtime. This guards §0.6.7 / §7.1.x
(OpenAPI is the partner/route truth) and keeps the exported snapshot buildable.
"""

from __future__ import annotations

from porterchain_api.main import app


def test_openapi_schema_builds() -> None:
    spec = app.openapi()
    assert spec["openapi"].startswith("3.")
    assert len(spec.get("paths", {})) > 100


def test_assign_batch_route_documented() -> None:
    spec = app.openapi()
    assert "/v1/admin/operations/queue/assign-batch" in spec["paths"]
