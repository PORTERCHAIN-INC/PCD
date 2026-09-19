"""Wholesale route templates stay on the admin API.

Decided 18 September 2026. The August 2026 ban that treated this path as a
deleted Route Center is not in force.
"""

from __future__ import annotations

from porterchain_api.main import app

_KEPT_ROUTE_TEMPLATES = "/v1/admin/route-templates"


def test_wholesale_route_templates_stay() -> None:
    assert _KEPT_ROUTE_TEMPLATES in set(app.openapi().get("paths", {}))
