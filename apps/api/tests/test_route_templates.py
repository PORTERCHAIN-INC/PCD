"""Wholesale route templates (§8.1.10)."""

from __future__ import annotations

from porterchain_api.admin_engine.route_template_service import (
    WHOLESALE_TYPE,
    AdminRouteTemplateService,
)


def test_wholesale_type_constant():
    assert WHOLESALE_TYPE == "wholesale"


def test_serialize_shape():
    class _Fake:
        id = "tpl-1"
        name = "Downtown loop"
        template_type = "wholesale"
        merchant_id = "m-1"
        zone = "gta_core"
        schedule = {"days": ["mon", "wed"]}
        stops = [{"address": "1 King St"}]
        config = {"vehicle_class": "box16"}
        is_active = True
        created_by = "admin-1"
        created_at = None

    row = AdminRouteTemplateService().serialize(_Fake())
    assert row["template_type"] == "wholesale"
    assert row["stops"][0]["address"] == "1 King St"
